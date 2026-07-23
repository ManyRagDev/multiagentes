"""Agente PerfDoubter - cético de problemas de performance."""

from src.agents.base import BaseAgent
from src.schemas.findings import Verdict, VerdictList
from src.schemas.agent import AgentConfig


class PerfDoubterAgent(BaseAgent[VerdictList]):
    """Agente cético que questiona gargalos de performance."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                nome="PerfDoubter",
                role="Cético de problemas de performance",
                model="deepseek-v4-pro",
                temperature=0.3,
                prompt_file="src/prompts/verify/performance_doubter.prompty",
                dominio="verify",
                output_schema="VerdictList"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[VerdictList]:
        """Retorna o schema Pydantic do output."""
        return VerdictList
