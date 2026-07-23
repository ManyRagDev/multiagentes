"""Agente BugHunter - identifica bugs de software."""

from src.agents.base import BaseAgent
from src.schemas.findings import Finding, FindingList
from src.schemas.agent import AgentConfig


class BugHunterAgent(BaseAgent[FindingList]):
    """Agente que identifica bugs de software."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                nome="BugHunter",
                role="Caçador de bugs de software",
                model="glm-5.2",
                temperature=0.3,
                prompt_file="src/prompts/audit/bug_hunter.prompty",
                dominio="audit",
                output_schema="FindingList"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[FindingList]:
        """Retorna o schema Pydantic do output."""
        return FindingList
