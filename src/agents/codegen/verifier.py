"""Agente CodeVerifier - verifica código gerado vs plano."""

from src.agents.base import BaseAgent
from src.schemas.findings import CodeVerification
from src.schemas.agent import AgentConfig


class CodeVerifierAgent(BaseAgent[CodeVerification]):
    """Agente que verifica se código gerado satisfaz o plano."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                nome="CodeVerifier",
                role="Verificador de código gerado",
                model="claude-sonnet-4-6",
                temperature=0.2,
                prompt_file="src/prompts/codegen/verifier.prompty",
                dominio="codegen",
                output_schema="CodeVerification"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[CodeVerification]:
        """Retorna o schema Pydantic do output."""
        return CodeVerification
