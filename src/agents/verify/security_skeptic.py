"""Agente SecSkeptic - cético de vulnerabilidades."""

from src.agents.base import BaseAgent
from src.schemas.findings import Verdict, VerdictList
from src.schemas.agent import AgentConfig


class SecSkepticAgent(BaseAgent[VerdictList]):
    """Agente cético que questiona exploits de segurança."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                nome="SecSkeptic",
                role="Cético de vulnerabilidades",
                model="deepseek-v4-pro",
                temperature=0.3,
                prompt_file="src/prompts/verify/security_skeptic.prompty",
                dominio="verify",
                output_schema="VerdictList"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[VerdictList]:
        """Retorna o schema Pydantic do output."""
        return VerdictList
