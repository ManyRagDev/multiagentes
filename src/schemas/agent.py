"""Schemas para configuração e output de agentes."""

from pydantic import BaseModel, Field
from typing import Any, Dict, Optional, Literal


class AgentConfig(BaseModel):
    """Configuração de um agente."""

    nome: str = Field(..., description="Nome do agente")
    role: str = Field(..., description="Papel/função do agente")
    model: str = Field(..., description="Modelo a usar (ex: claude-sonnet-4-6)")
    temperature: float = Field(
        ...,
        ge=0.0,
        le=1.0,
        description="Temperatura para geração"
    )
    prompt_file: Optional[str] = Field(
        None,
        description="Caminho para o arquivo de prompt"
    )
    prompt_template: Optional[str] = Field(
        None,
        description="Template de prompt (se não usar arquivo)"
    )
    dominio: Literal["planning", "audit", "verify", "codegen"] = Field(
        ...,
        description="Domínio do agente"
    )
    output_schema: Optional[str] = Field(
        None,
        description="Nome do schema Pydantic do output"
    )
    provider: Optional[str] = Field(
        None,
        description="Provider a usar (ex: local-qwen, glm, deepseek). "
                    "Se None, usa inferência pelo nome do modelo."
    )


class AgentOutput(BaseModel):
    """Output genérico de um agente."""

    agente: str = Field(..., description="Nome do agente que gerou")
    sucesso: bool = Field(..., description="True se execução foi bem-sucedida")
    output: Optional[Dict[str, Any]] = Field(
        None,
        description="Output estruturado (dados do schema)"
    )
    raw_output: Optional[str] = Field(
        None,
        description="Output bruto do modelo (antes do parse)"
    )
    erro: Optional[str] = Field(
        None,
        description="Mensagem de erro, se houve falha"
    )
    tokens_usados: Optional[int] = Field(
        None,
        description="Tokens consumidos na chamada"
    )
