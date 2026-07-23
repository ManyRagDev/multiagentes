"""Tool registry: central registration, discovery and execution with permission gates."""
from typing import Any

from .base import (
    BaseTool,
    PermissionDecision,
    PermissionLevel,
    PermissionManager,
    ToolRequest,
    ToolResult,
)
from .filesystem import FilesystemReadTool, FilesystemWriteTool
from .git import GitTool
from .shell import ShellTool


class ToolRegistry:
    """Registro central de ferramentas com execução protegida por permissões."""

    def __init__(self, permission_manager: PermissionManager | None = None):
        self._tools: dict[str, BaseTool] = {}
        self.permission_manager = permission_manager or PermissionManager()
        # Registra ferramentas padrão
        self._register_defaults()

    def _register_defaults(self):
        """Registra o conjunto padrão de ferramentas."""
        for tool in [
            FilesystemReadTool(),
            FilesystemWriteTool(),
            ShellTool(),
            GitTool(),
        ]:
            self.register(tool)

    def register(self, tool: BaseTool):
        """Registra uma ferramenta."""
        self._tools[tool.name] = tool

    def get(self, name: str) -> BaseTool | None:
        return self._tools.get(name)

    def list_tools(self) -> list[dict[str, str]]:
        """Lista ferramentas disponíveis para o LLM."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "permission_level": t.permission_level.value,
            }
            for t in self._tools.values()
        ]

    async def execute_tool(
        self, tool_name: str, action: str = "", args: dict[str, Any] | None = None
    ) -> ToolResult:
        """Executa ferramenta com gate de permissão."""
        tool = self._tools.get(tool_name)
        if not tool:
            available = ", ".join(self._tools.keys())
            return ToolResult(
                success=False,
                error=f"Ferramenta '{tool_name}' não encontrada. Disponíveis: {available}",
            )

        args = args or {}

        # Validação prévia
        ok, msg = tool.validate_args(**args)
        if not ok:
            return ToolResult(success=False, error=f"Validação falhou: {msg}")

        # Solicitar permissão
        request = ToolRequest(
            tool_name=tool_name,
            action=action or tool.name,
            args=args,
            level=tool.permission_level,
            description=tool.description,
        )

        decision = await self.permission_manager.request_permission(request)

        if decision == PermissionDecision.DENIED:
            return ToolResult(
                success=False,
                error=f"Permissão negada para {tool_name} (nível: {tool.permission_level.value})",
                metadata={"decision": "denied"},
            )

        # Executar
        try:
            result = await tool.execute(**args)
            result.metadata["decision"] = decision.value
            result.metadata["tool"] = tool_name
            return result
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Erro na execução de {tool_name}: {e}",
                metadata={"decision": decision.value},
            )
