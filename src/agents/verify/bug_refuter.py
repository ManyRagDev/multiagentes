"""Agente BugRefuter - advogado do diabo para bugs."""

from src.agents.base import BaseAgent
from src.schemas.findings import Verdict, VerdictList
from src.schemas.agent import AgentConfig


class BugRefuterAgent(BaseAgent[VerdictList]):
    """Agente cético que tenta refutar bugs reportados."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                nome="BugRefuter",
                role="Advogado do diabo para bugs",
                model="deepseek-v4-pro",
                temperature=0.4,
                prompt_file="src/prompts/verify/bug_refuter.prompty",
                dominio="verify",
                output_schema="VerdictList"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[VerdictList]:
        """Retorna o schema Pydantic do output."""
        return VerdictList
