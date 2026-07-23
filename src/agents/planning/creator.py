"""Agente PlanCreator - cria planos de implementação."""

from src.agents.base import BaseAgent
from src.schemas.plano import Plan
from src.schemas.agent import AgentConfig


class PlanCreatorAgent(BaseAgent[Plan]):
    """Agente que cria planos de implementação detalhados."""

    def __init__(self, config: AgentConfig | None = None):
        """
        Inicializa o PlanCreator.

        Args:
            config: Configuração (opcional, usa padrão se não fornecido)
        """
        if config is None:
            config = AgentConfig(
                nome="PlanCreator",
                role="Criador de planos de implementação",
                model="claude-sonnet-4-6",
                temperature=0.4,
                prompt_file="src/prompts/planning/creator.prompty",
                dominio="planning",
                output_schema="Plan"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[Plan]:
        """Retorna o schema Pydantic do output."""
        return Plan
