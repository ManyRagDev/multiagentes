"""Filesystem tool with permission-gated read/write operations."""
import os
from pathlib import Path
from typing import Any

from .base import BaseTool, PermissionLevel, ToolResult


class FilesystemReadTool(BaseTool):
    """Leitura de arquivos e listagem de diretórios."""

    @property
    def name(self) -> str:
        return "fs_read"

    @property
    def description(self) -> str:
        return (
            "Lê conteúdo de arquivo ou lista diretório. "
            "Args: path (str), mode ('file'|'dir'), max_lines (int, opcional)."
        )

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.READ

    async def execute(self, **kwargs) -> ToolResult:
        path = kwargs.get("path", "")
        mode = kwargs.get("mode", "file")
        max_lines = kwargs.get("max_lines", 0)

        if not path:
            return ToolResult(success=False, error="Argumento 'path' é obrigatório")

        p = Path(path).resolve()

        try:
            if mode == "dir":
                if not p.is_dir():
                    return ToolResult(success=False, error=f"Não é diretório: {p}")
                entries = sorted(p.iterdir())
                lines = []
                for e in entries:
                    prefix = "[DIR]" if e.is_dir() else "[FILE]"
                    size = e.stat().st_size if e.is_file() else "-"
                    lines.append(f"{prefix} {e.name} ({size})")
                return ToolResult(success=True, output="\n".join(lines))

            # mode == "file"
            if not p.is_file():
                return ToolResult(success=False, error=f"Arquivo não encontrado: {p}")

            text = p.read_text(encoding="utf-8", errors="replace")
            if max_lines and max_lines > 0:
                lines = text.splitlines()[:max_lines]
                text = "\n".join(lines)
                truncated = len(lines) < len(p.read_text(encoding="utf-8", errors="replace").splitlines())
                meta = {"truncated": truncated, "total_lines": len(p.read_text(encoding="utf-8", errors="replace").splitlines())}
            else:
                meta = {"total_lines": len(text.splitlines()), "size_bytes": p.stat().st_size}

            return ToolResult(success=True, output=text, metadata=meta)

        except Exception as e:
            return ToolResult(success=False, error=str(e))


class FilesystemWriteTool(BaseTool):
    """Escrita/edição de arquivos com validação de path."""

    ALLOWED_EXTENSIONS = {
        ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml",
        ".md", ".txt", ".css", ".html", ".toml", ".cfg", ".ini", ".env",
        ".sh", ".bash", ".sql", ".graphql", ".proto",
    }

    @property
    def name(self) -> str:
        return "fs_write"

    @property
    def description(self) -> str:
        return (
            "Escreve ou sobrescreve arquivo. "
            "Args: path (str), content (str), create_dirs (bool, default True)."
        )

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.WRITE

    def validate_args(self, **kwargs) -> tuple[bool, str]:
        path = kwargs.get("path", "")
        if not path:
            return False, "Argumento 'path' é obrigatório"
        ext = Path(path).suffix.lower()
        if ext and ext not in self.ALLOWED_EXTENSIONS:
            return False, f"Extensão '{ext}' não permitida. Permitidas: {sorted(self.ALLOWED_EXTENSIONS)}"
        return True, ""

    async def execute(self, **kwargs) -> ToolResult:
        ok, msg = self.validate_args(**kwargs)
        if not ok:
            return ToolResult(success=False, error=msg)

        path = kwargs["path"]
        content = kwargs.get("content", "")
        create_dirs = kwargs.get("create_dirs", True)

        p = Path(path).resolve()

        try:
            if create_dirs:
                p.parent.mkdir(parents=True, exist_ok=True)

            existed = p.exists()
            p.write_text(content, encoding="utf-8")

            action = "Atualizado" if existed else "Criado"
            return ToolResult(
                success=True,
                output=f"{action}: {p} ({len(content)} bytes)",
                metadata={"path": str(p), "existed": existed, "size": len(content)},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
