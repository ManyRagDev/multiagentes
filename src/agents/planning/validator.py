"""Agente PlanValidator - valida planos buscando inconsistências."""

from src.agents.base import BaseAgent
from src.schemas.plano import PlanValidation
from src.schemas.agent import AgentConfig


class PlanValidatorAgent(BaseAgent[PlanValidation]):
    """Agente que valida planos buscando inconsistências."""

    def __init__(self, config: AgentConfig | None = None):
        """
        Inicializa o PlanValidator.

        Args:
            config: Configuração (opcional, usa padrão se não fornecido)
        """
        if config is None:
            config = AgentConfig(
                nome="PlanValidator",
                role="Validador de planos (busca inconsistências)",
                model="claude-sonnet-4-6",
                temperature=0.2,
                prompt_file="src/prompts/planning/validator.prompty",
                dominio="planning",
                output_schema="PlanValidation"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[PlanValidation]:
        """Retorna o schema Pydantic do output."""
        return PlanValidation
