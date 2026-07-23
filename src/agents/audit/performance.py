"""Agente PerfAnalyst - identifica problemas de performance."""

from src.agents.base import BaseAgent
from src.schemas.findings import Finding, FindingList
from src.schemas.agent import AgentConfig


class PerfAnalystAgent(BaseAgent[FindingList]):
    """Agente que identifica problemas de performance."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                nome="PerfAnalyst",
                role="Analista de performance",
                model="glm-5.2",
                temperature=0.3,
                prompt_file="src/prompts/audit/performance.prompty",
                dominio="audit",
                output_schema="FindingList"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[FindingList]:
        """Retorna o schema Pydantic do output."""
        return FindingList
