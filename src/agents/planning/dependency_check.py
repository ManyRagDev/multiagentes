"""Agente DependencyChecker - verifica dependências em planos."""

from src.agents.base import BaseAgent
from src.schemas.plano import PlanValidation
from src.schemas.agent import AgentConfig


class DependencyCheckerAgent(BaseAgent[PlanValidation]):
    """Agente que verifica dependências em planos."""

    def __init__(self, config: AgentConfig | None = None):
        """
        Inicializa o DependencyChecker.

        Args:
            config: Configuração (opcional, usa padrão se não fornecido)
        """
        if config is None:
            config = AgentConfig(
                nome="DependencyChecker",
                role="Verificador de dependências em planos",
                model="claude-haiku-4-5",
                temperature=0.1,
                prompt_file="src/prompts/planning/dependency_check.prompty",
                dominio="planning",
                output_schema="PlanValidation"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[PlanValidation]:
        """Retorna o schema Pydantic do output."""
        return PlanValidation
