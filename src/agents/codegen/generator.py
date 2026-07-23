"""Agente CodeGen - gera código a partir de planos."""

from src.agents.base import BaseAgent
from src.schemas.findings import CodeOutput
from src.schemas.agent import AgentConfig


class CodeGenAgent(BaseAgent[CodeOutput]):
    """Agente que gera código a partir de planos validados."""

    def __init__(self, config: AgentConfig | None = None):
        if config is None:
            config = AgentConfig(
                nome="CodeGen",
                role="Gerador de código a partir de planos",
                model="claude-sonnet-4-6",
                temperature=0.3,
                prompt_file="src/prompts/codegen/generator.prompty",
                dominio="codegen",
                output_schema="CodeOutput"
            )
        super().__init__(config)

    def get_output_schema(self) -> type[CodeOutput]:
        """Retorna o schema Pydantic do output."""
        return CodeOutput
