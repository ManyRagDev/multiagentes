"""Base classes for tool system with permission model."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class PermissionLevel(Enum):
    """Níveis de permissão para ferramentas."""
    READ = "read"           # Leitura: geralmente seguro
    WRITE = "write"         # Escrita: requer confirmação ou auto-approve
    EXECUTE = "execute"     # Shell/comandos: risco alto
    GIT = "git"             # Operações Git: modificam histórico/estado


class PermissionDecision(Enum):
    """Decisão de permissão."""
    APPROVED = "approved"
    DENIED = "denied"
    AUTO_APPROVE = "auto_approve"  # Modo automático ativo


@dataclass
class ToolRequest:
    """Requisição de execução de ferramenta."""
    tool_name: str
    action: str
    args: dict[str, Any]
    level: PermissionLevel
    description: str = ""
    risk_note: str = ""


@dataclass
class ToolResult:
    """Resultado da execução de ferramenta."""
    success: bool
    output: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class BaseTool(ABC):
    """Interface base para todas as ferramentas."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome único da ferramenta."""
        ...

    @property
    @abstractmethod
    def description(self) -> str:
        """Descrição para o LLM entender quando usar."""
        ...

    @property
    @abstractmethod
    def permission_level(self) -> PermissionLevel:
        """Nível de permissão padrão desta ferramenta."""
        ...

    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Executa a ferramenta com os argumentos fornecidos."""
        ...

    def validate_args(self, **kwargs) -> tuple[bool, str]:
        """Valida argumentos antes da execução. Retorna (ok, msg)."""
        return True, ""


class PermissionManager:
    """Gerencia decisões de permissão: prompt, auto-approve e memória."""

    def __init__(self, auto_mode: bool = False):
        self._auto_mode = auto_mode
        # Regras persistentes: {(tool_name, action_pattern): approved/denied}
        self._rules: dict[tuple[str, str], bool] = {}
        # Callback para solicitar permissão ao usuário
        self._prompt_callback: Optional[Any] = None

    @property
    def auto_mode(self) -> bool:
        return self._auto_mode

    @auto_mode.setter
    def auto_mode(self, value: bool):
        self._auto_mode = value

    def set_prompt_callback(self, callback):
        """Define callback async fn(request: ToolRequest) -> PermissionDecision."""
        self._prompt_callback = callback

    def add_rule(self, tool_name: str, action_pattern: str, approved: bool):
        """Adiciona regra persistente (ex: 'filesystem', 'read:*' -> True)."""
        self._rules[(tool_name, action_pattern)] = approved

    async def request_permission(self, request: ToolRequest) -> PermissionDecision:
        """Solicita permissão seguindo hierarquia: regra > auto > prompt."""
        # 1. Verificar regras persistentes
        for (tool, pattern), approved in self._rules.items():
            if tool == request.tool_name and self._match(pattern, request.action):
                return PermissionDecision.APPROVED if approved else PermissionDecision.DENIED

        # 2. Auto-mode aprova tudo exceto EXECUTE (que ainda pode ser arriscado)
        if self._auto_mode:
            return PermissionDecision.AUTO_APPROVE

        # 3. Prompt ao usuário
        if self._prompt_callback:
            return await self._prompt_callback(request)

        # Sem callback e sem auto-mode: nega por segurança
        return PermissionDecision.DENIED

    @staticmethod
    def _match(pattern: str, action: str) -> bool:
        """Match simples com wildcard: 'read:*' casa com 'read_file'."""
        if pattern == "*":
            return True
        if pattern.endswith(":*"):
            prefix = pattern[:-2]
            return action.startswith(prefix)
        return pattern == action
