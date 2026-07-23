"""Shell tool with allowlist, timeout and safety checks."""
import asyncio
import re
from typing import Any

from .base import BaseTool, PermissionLevel, ToolResult


# Comandos/padrões perigosos bloqueados por padrão
BLOCKED_PATTERNS = [
    r"rm\s+-rf\s+/",
    r"rm\s+-rf\s+\*",
    r"mkfs\.",
    r"dd\s+if=",
    r":(){ :\|:& };:",  # fork bomb
    r"chmod\s+-R\s+777",
    r"curl.*\|\s*(ba)?sh",
    r"wget.*\|\s*(ba)?sh",
    r"eval\s*\(",
    r"exec\s*\(",
    r">/dev/sd[a-z]",
    r"shutdown",
    r"reboot",
    r"format\s+[a-zA-Z]:",
    r"del\s+/[sS]\s+[a-zA-Z]:\\",
]

# Comandos permitidos por padrão (prefixos)
DEFAULT_ALLOWED_PREFIXES = [
    "npm ", "npx ", "yarn ", "pnpm ",
    "uv ", "pip ", "python ", "pytest ", "ruff ", "mypy ",
    "node ", "tsc ", "eslint ", "vitest ", "vite ",
    "git ", "cargo ", "go ",
    "ls", "dir", "cat", "head", "tail", "grep", "find",
    "echo ", "pwd", "whoami",
]


class ShellTool(BaseTool):
    """Execução de comandos shell com allowlist e bloqueio de padrões perigosos."""

    def __init__(self, allowed_prefixes: list[str] | None = None, timeout: int = 60):
        self._allowed_prefixes = allowed_prefixes or DEFAULT_ALLOWED_PREFIXES
        self._timeout = timeout

    @property
    def name(self) -> str:
        return "shell"

    @property
    def description(self) -> str:
        return (
            "Executa comando no terminal. "
            "Args: command (str), cwd (str, opcional), timeout (int, opcional). "
            "Comandos são validados contra allowlist e padrões bloqueados."
        )

    @property
    def permission_level(self) -> PermissionLevel:
        return PermissionLevel.EXECUTE

    def validate_args(self, **kwargs) -> tuple[bool, str]:
        command = kwargs.get("command", "").strip()
        if not command:
            return False, "Argumento 'command' é obrigatório"

        # Verificar padrões bloqueados
        for pattern in BLOCKED_PATTERNS:
            if re.search(pattern, command, re.IGNORECASE):
                return False, f"Comando bloqueado por segurança (padrão: {pattern})"

        # Verificar allowlist
        if not any(command.startswith(prefix) for prefix in self._allowed_prefixes):
            allowed = ", ".join(p.strip() for p in self._allowed_prefixes[:10])
            return False, (
                f"Comando não está na allowlist. Prefixos permitidos: {allowed}... "
                f"Adicione ao config ou use modo automático com cautela."
            )

        return True, ""

    async def execute(self, **kwargs) -> ToolResult:
        ok, msg = self.validate_args(**kwargs)
        if not ok:
            return ToolResult(success=False, error=msg)

        command = kwargs["command"]
        cwd = kwargs.get("cwd", None)
        timeout = kwargs.get("timeout", self._timeout)

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=cwd,
            )
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )

            out = stdout.decode("utf-8", errors="replace").strip()
            err = stderr.decode("utf-8", errors="replace").strip()
            code = proc.returncode

            if code == 0:
                return ToolResult(
                    success=True,
                    output=out or "(sem saída)",
                    metadata={"exit_code": code, "command": command},
                )
            else:
                combined = f"STDOUT:\n{out}\n\nSTDERR:\n{err}" if out and err else (err or out)
                return ToolResult(
                    success=False,
                    output=combined,
                    error=f"Exit code {code}",
                    metadata={"exit_code": code, "command": command},
                )

        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"Timeout após {timeout}s",
                metadata={"command": command, "timeout": timeout},
            )
        except Exception as e:
            return ToolResult(success=False, error=str(e))
