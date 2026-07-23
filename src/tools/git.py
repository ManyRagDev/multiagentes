"""Git tool with auto-detection of installation and repository."""
import asyncio
import shutil
from pathlib import Path
from typing import Any

from .base import BaseTool, PermissionLevel, ToolResult


class GitTool(BaseTool):
    """Operações Git com detecção automática de instalação e repositório."""

    # Subcomandos seguros (leitura ou operações locais não-destrutivas)
    SAFE_SUBCOMMANDS = {
        "status", "log", "diff", "show", "branch", "tag",
        "remote", "stash list", "reflog", "shortlog",
    }

    # Subcomandos que modificam estado (requerem permissão WRITE/GIT)
    MUTATING_SUBCOMMANDS = {
        "add", "commit", "checkout", "switch", "merge", "rebase",
        "reset", "stash push", "stash pop", "cherry-pick",
        "pull", "fetch", "push", "tag -a", "branch -d",
    }

    def __init__(self):
        self._git_available: bool | None = None
        self._repo_root: str | None = None

    @property
    def name(self) -> str:
        return "git"

    @property
    def description(self) -> str:
        return (
            "Executa comandos Git. Auto-detecta instalação e repositório. "
            "Args: subcommand (str), args (str, opcional), cwd (str, opcional). "
            "Ex: subcommand='status', subcommand='diff --cached'."
        )

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.GIT

    async def _check_git_installed(self) -> tuple[bool, str]:
        """Verifica se git está instalado."""
        if self._git_available is not None:
            return self._git_available, ""

        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            version = stdout.decode().strip()
            self._git_available = proc.returncode == 0
            if self._git_available:
                return True, version
            return False, "git retornou erro"
        except FileNotFoundError:
            self._git_available = False
            return False, "git não encontrado no PATH"
        except Exception as e:
            self._git_available = False
            return False, str(e)

    async def _detect_repo(self, cwd: str | None = None) -> tuple[bool, str]:
        """Detecta se cwd está dentro de um repositório Git."""
        work_dir = cwd or "."
        try:
            proc = await asyncio.create_subprocess_exec(
                "git", "rev-parse", "--show-toplevel",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=work_dir,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5)
            if proc.returncode == 0:
                self._repo_root = stdout.decode().strip()
                return True, self._repo_root
            return False, stderr.decode().strip() or "Não é um repositório Git"
        except Exception as e:
            return False, str(e)

    def _classify_subcommand(self, subcommand: str) -> str:
        """Classifica subcomando como 'safe', 'mutating' ou 'unknown'."""
        base = subcommand.strip().split()[0] if subcommand else ""
        full = subcommand.strip()

        if full in self.SAFE_SUBCOMMANDS or base in self.SAFE_SUBCOMMANDS:
            return "safe"
        if full in self.MUTATING_SUBCOMMANDS or base in self.MUTATING_SUBCOMMANDS:
            return "mutating"
        return "unknown"

    async def execute(self, **kwargs) -> ToolResult:
        subcommand = kwargs.get("subcommand", "").strip()
        extra_args = kwargs.get("args", "")
        cwd = kwargs.get("cwd", None)

        if not subcommand:
            return ToolResult(success=False, error="Argumento 'subcommand' é obrigatório")

        # 1. Verificar instalação
        installed, info = await self._check_git_installed()
        if not installed:
            return ToolResult(
                success=False,
                error=f"Git não disponível: {info}. Instale git ou adicione ao PATH.",
                metadata={"git_installed": False},
            )

        # 2. Detectar repositório
        in_repo, repo_info = await self._detect_repo(cwd)
        if not in_repo:
            return ToolResult(
                success=False,
                error=f"Repositório Git não detectado: {repo_info}",
                metadata={"git_installed": True, "in_repo": False},
            )

        # 3. Classificar risco do subcomando
        risk = self._classify_subcommand(subcommand)
        command = f"git {subcommand}"
        if extra_args:
            command += f" {extra_args}"

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd or repo_info,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30)

            out = stdout.decode("utf-8", errors="replace").strip()
            err = stderr.decode("utf-8", errors="replace").strip()
            code = proc.returncode

            meta = {
                "git_installed": True,
                "in_repo": True,
                "repo_root": repo_info,
                "subcommand_risk": risk,
                "exit_code": code,
            }

            if code == 0:
                return ToolResult(success=True, output=out or "(sem saída)", metadata=meta)
            else:
                combined = err or out
                return ToolResult(success=False, output=combined, error=f"Exit code {code}", metadata=meta)

        except asyncio.TimeoutError:
            return ToolResult(success=False, error="Timeout após 30s", metadata={"command": command})
        except Exception as e:
            return ToolResult(success=False, error=str(e))
