"""Worktree: execucao isolada em diretorio temporario.

Cria uma copia do projeto em temp dir, executa alteracoes la,
e so faz merge no repositorio real se todos os gates passarem.
"""
from __future__ import annotations

import logging
import shutil
import tempfile
from contextlib import contextmanager
from pathlib import Path

logger = logging.getLogger(__name__)

IGNORE_PATTERNS = {
    ".git", "__pycache__", ".venv", "venv", "node_modules",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tox",
    "dist", "build", ".eggs", "*.egg-info",
    ".env", "logs", "uv.lock",
}


class WorktreeManager:
    """Gerencia execucao isolada em worktree temporario."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self._worktree: Path | None = None
        self._original_files: dict[str, str] = {}
        self._session_active = False

    @property
    def active(self) -> bool:
        return self._session_active

    @property
    def worktree_path(self) -> Path | None:
        return self._worktree

    @contextmanager
    def session(self, allowed_files: list[str] | None = None):
        """Context manager que cria e gerencia o ciclo de vida do worktree.

        Uso:
            with worktree.session(allowed_files=["src/math.py"]) as wt_path:
                # executa codigo, aplica diffs, roda validacao
                worktree.apply_output(code, ["src/math.py"])
        """
        self._create(allowed_files)
        try:
            yield self._worktree
        finally:
            self.discard()

    def _create(self, allowed_files: list[str] | None = None) -> None:
        """Cria worktree copiando arquivos relevantes do projeto."""
        if self._session_active:
            raise RuntimeError("Worktree session ja esta ativa")

        self._worktree = Path(tempfile.mkdtemp(prefix="multiagent_"))
        self._original_files = {}
        self._session_active = True

        if allowed_files:
            validated = self._validate_files(allowed_files, "_create")
            self._copy_with_deps(validated)
        else:
            self._copy_full_project()

        logger.info(
            "Worktree criado: %s (%d arquivos copiados)",
            self._worktree, len(self._original_files),
        )

    def _copy_with_deps(self, allowed_files: list[str]) -> None:
        """Copia apenas os arquivos permitidos e suas dependencias diretas."""
        for rel_path in allowed_files:
            src = self.project_root / rel_path
            dst = self._worktree / rel_path
            if src.is_file():
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
                self._original_files[rel_path] = src.read_text(encoding="utf-8", errors="replace")
            elif src.is_dir():
                shutil.copytree(
                    src, dst,
                    dirs_exist_ok=True,
                    ignore=shutil.ignore_patterns(*IGNORE_PATTERNS),
                )
                for f in dst.rglob("*"):
                    if f.is_file():
                        rel = str(f.relative_to(self._worktree))
                        self._original_files[rel] = (
                            (self.project_root / rel)
                            .read_text(encoding="utf-8", errors="replace")
                        )

    def _copy_full_project(self) -> None:
        """Copia o projeto inteiro para o worktree, ignorando artefatos."""
        def _ignore_patterns(directory: str, names: list[str]) -> set[str]:
            ignored = set()
            for name in names:
                if name in IGNORE_PATTERNS:
                    ignored.add(name)
                elif name.startswith(".") and name not in (".env.example",):
                    ignored.add(name)
                elif any(name.endswith(pat.replace("*", "")) for pat in IGNORE_PATTERNS):
                    ignored.add(name)
            return ignored

        shutil.copytree(
            self.project_root, self._worktree,
            dirs_exist_ok=True,
            ignore=_ignore_patterns,
        )

        for f in self._worktree.rglob("*"):
            if f.is_file() and not self._should_ignore_for_snapshot(f):
                rel = str(f.relative_to(self._worktree))
                src = self.project_root / rel
                if src.is_file():
                    try:
                        self._original_files[rel] = src.read_text(encoding="utf-8", errors="replace")
                    except Exception:
                        pass

    @staticmethod
    def _should_ignore_for_snapshot(filepath: Path) -> bool:
        parts = filepath.parts
        return any(p in IGNORE_PATTERNS for p in parts)

    def _validate_path_security(self, rel_path: str, caller: str = "") -> str:
        """Valida que um caminho relativo nao escapa do projeto (P0.3).

        Rejeita:
        - path traversal (../, ..\\)
        - caminhos absolutos
        - caracteres nulos
        - resolucao que escapa de project_root

        Retorna o caminho normalizado se for seguro.
        """
        raw = rel_path.strip()

        if not raw:
            raise ValueError(f"[{caller}] Caminho vazio nao permitido")

        if '\x00' in raw:
            raise ValueError(f"[{caller}] Caractere nulo detectado em: {raw!r}")

        normalized = raw.replace('\\', '/')

        if normalized.startswith('/') or (
            len(raw) >= 2 and raw[1] == ':' and raw[2] in ('\\', '/')
        ):
            raise ValueError(
                f"[{caller}] Caminho absoluto rejeitado: {raw!r}"
            )

        parts = normalized.split('/')
        if '..' in parts:
            raise ValueError(
                f"[{caller}] Path traversal detectado (..): {raw!r}"
            )

        resolved = (self.project_root / raw).resolve()

        try:
            resolved.relative_to(self.project_root)
        except ValueError:
            raise ValueError(
                f"[{caller}] Caminho escapa do projeto: {raw!r} "
                f"→ {resolved}"
            )

        return raw

    def _validate_files(self, files: list[str], caller: str = "") -> list[str]:
        """Valida lista de caminhos contra path traversal."""
        return [
            self._validate_path_security(f, caller)
            for f in files
        ]

    def apply_output(self, output: str, changed_files: list[str]) -> None:
        """Aplica o output do executor aos arquivos do worktree.

        Suporta dois formatos:
        - unified_diff: output contem patch que sera aplicado
        - full_file: output e o conteudo completo do arquivo
        """
        if not self._session_active or self._worktree is None:
            raise RuntimeError("Nenhuma sessao de worktree ativa")

        if not output or not output.strip():
            return

        cleaned = self._extract_code(output)

        if "--- a/" in cleaned and "+++ b/" in cleaned:
            self._apply_diff(cleaned, changed_files)
        else:
            self._apply_full_file(cleaned, changed_files)

    @staticmethod
    def _extract_code(output: str) -> str:
        """Extrai codigo puro, removendo fences markdown."""
        text = output.strip()

        if text.startswith("```"):
            lines = text.split("\n")
            end = None
            for i in range(1, len(lines)):
                if lines[i].strip() == "```":
                    end = i
                    break
            if end and end > 1:
                return "\n".join(lines[1:end]).strip()

        fences = text.count("```")
        if fences >= 2:
            first = text.find("```")
            last = text.rfind("```")
            inner = text[first + 3:last].strip()
            if inner.startswith(("python", "typescript", "javascript", "diff")):
                inner = inner[inner.find("\n"):].strip()
            return inner

        return text

    def _apply_diff(self, diff_text: str, changed_files: list[str]) -> None:
        """Aplica patch unificado aos arquivos do worktree.

        Sem usar subprocess 'patch', faz parse manual simples.
        """
        patches: dict[str, list[str]] = {}
        current_file = None

        for line in diff_text.split("\n"):
            if line.startswith("--- a/") or line.startswith("+++ b/"):
                filepath = line[6:] if line.startswith("+++ b/") else line[4:]
                current_file = filepath
                if current_file not in patches:
                    patches[current_file] = []
            elif current_file:
                patches[current_file].append(line)

        for filepath, lines in patches.items():
            safe_path = self._validate_path_security(filepath, "_apply_diff")
            target = self._worktree / safe_path
            if not target.parent.exists():
                target.parent.mkdir(parents=True, exist_ok=True)

            if target.exists():
                original = target.read_text(encoding="utf-8", errors="replace")
                result = self._patch_lines(original, lines)
                target.write_text(result, encoding="utf-8")
            else:
                content = "\n".join(
                    l[1:] for l in lines if l.startswith("+") and not l.startswith("+++")
                )
                target.write_text(content, encoding="utf-8")

    @staticmethod
    def _patch_lines(original: str, diff_lines: list[str]) -> str:
        """Aplica linhas de diff a um texto original (simplificado)."""
        result: list[str] = []
        orig_lines = original.split("\n")
        orig_idx = 0

        for line in diff_lines:
            if line.startswith("@@"):
                from_part = line.split("@@")[1].strip() if "@@" in line else ""
                if from_part:
                    try:
                        start = int(from_part.split(",")[0].replace("-", ""))
                        orig_idx = max(0, start - 1)
                    except (ValueError, IndexError):
                        pass
                continue
            elif line.startswith(" "):
                result.append(line[1:])
                orig_idx += 1
            elif line.startswith("-"):
                orig_idx += 1
            elif line.startswith("+"):
                result.append(line[1:])
            elif line.startswith("\\"):
                pass

        if orig_idx < len(orig_lines):
            result.extend(orig_lines[orig_idx:])

        return "\n".join(result)

    def _apply_full_file(self, code: str, changed_files: list[str]) -> None:
        """Escreve codigo como arquivo completo no worktree."""
        if not changed_files:
            return

        safe_files = self._validate_files(changed_files, "_apply_full_file")
        target_file = safe_files[0]
        target = self._worktree / target_file
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(code, encoding="utf-8")

    def collect_diff(self, changed_files: list[str] | None = None) -> str:
        """Coleta diff entre worktree e repositorio original.

        Retorna diff unificado para merge ou inspecao.
        """
        if not self._session_active or self._worktree is None:
            return ""

        files = changed_files or list(self._original_files.keys())
        validated = self._validate_files(files, "collect_diff")
        diffs: list[str] = []

        for rel_path in sorted(validated):
            wt_file = self._worktree / rel_path
            orig_file = self.project_root / rel_path

            if not wt_file.exists():
                continue

            wt_content = wt_file.read_text(encoding="utf-8", errors="replace")
            orig_content = self._original_files.get(rel_path, "")

            if wt_content == orig_content:
                continue

            from difflib import unified_diff
            diff_lines = list(unified_diff(
                orig_content.splitlines(keepends=True),
                wt_content.splitlines(keepends=True),
                fromfile=f"a/{rel_path}",
                tofile=f"b/{rel_path}",
            ))
            if diff_lines:
                diffs.append("".join(diff_lines))

        return "\n".join(diffs)

    def merge(self, changed_files: list[str] | None = None) -> list[str]:
        """Faz merge das alteracoes do worktree para o repositorio original.

        Retorna lista de arquivos que foram modificados.
        """
        if not self._session_active or self._worktree is None:
            return []

        files = changed_files or list(self._original_files.keys())
        validated = self._validate_files(files, "merge")
        modified = []

        for rel_path in sorted(validated):
            wt_file = self._worktree / rel_path
            if not wt_file.exists():
                continue

            wt_content = wt_file.read_text(encoding="utf-8", errors="replace")
            orig_content = self._original_files.get(rel_path, "")
            if wt_content == orig_content:
                continue

            target = self.project_root / rel_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(wt_content, encoding="utf-8")
            modified.append(rel_path)
            logger.info("Merge: %s", rel_path)

        return modified

    def discard(self) -> None:
        """Descarta o worktree sem aplicar alteracoes."""
        if self._worktree and self._worktree.exists():
            try:
                shutil.rmtree(self._worktree, ignore_errors=True)
                logger.info("Worktree descartado: %s", self._worktree)
            except Exception as e:
                logger.warning("Erro ao descartar worktree: %s", e)
        self._worktree = None
        self._original_files = {}
        self._session_active = False

    def _reset_files(self, files: list[str]) -> None:
        """Restaura arquivos do worktree ao estado original (para retry)."""
        validated = self._validate_files(files, "_reset_files")
        for rel_path in validated:
            wt_file = self._worktree / rel_path
            orig_content = self._original_files.get(rel_path)
            if orig_content is not None and wt_file.parent.exists():
                wt_file.parent.mkdir(parents=True, exist_ok=True)
                wt_file.write_text(orig_content, encoding="utf-8")

    def status(self) -> dict:
        """Retorna status do worktree atual."""
        return {
            "active": self._session_active,
            "worktree_path": str(self._worktree) if self._worktree else None,
            "tracked_files": len(self._original_files),
        }
