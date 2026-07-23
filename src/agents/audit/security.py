"""Agente SecAudit - identifica vulnerabilidades de segurança."""

from src.agents.base import BaseAgent
from src.schemas.findings import Finding, FindingList
from src.schemas.agent import AgentConfig


class SecAuditAgent(BaseAgent[FindingList]):
    """Agente que identifica vulnerabilidades de segurança."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                nome="SecAudit",
                role="Auditor de segurança",
                model="glm-5.2",
                temperature=0.2,
                prompt_file="src/prompts/audit/security.prompty",
                dominio="audit",
                output_schema="FindingList"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[FindingList]:
        """Retorna o schema Pydantic do output."""
        return FindingList
