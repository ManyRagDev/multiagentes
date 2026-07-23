"""Agente CompletenessCheck - meta-auditor de completude."""

from src.agents.base import BaseAgent
from src.schemas.findings import CompletenessReport
from src.schemas.agent import AgentConfig


class CompletenessCheckAgent(BaseAgent[CompletenessReport]):
    """Meta-agente que verifica se nada foi deixado de fora."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                nome="CompletenessCheck",
                role="Meta-auditor (verifica completude)",
                model="glm-5.2",
                temperature=0.4,
                prompt_file="src/prompts/verify/completeness_check.prompty",
                dominio="verify",
                output_schema="CompletenessReport"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[CompletenessReport]:
        """Retorna o schema Pydantic do output."""
        return CompletenessReport
