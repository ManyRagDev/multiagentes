"""Schemas para planejamento - Planos, Steps, Validação."""

from pydantic import BaseModel, Field
from typing import List, Optional, Literal


class Step(BaseModel):
    """Um passo em um plano de implementação."""

    id: int = Field(..., description="Ordinal do passo, começando em 1")
    descricao: str = Field(..., description="O que fazer, de forma acionável")
    depende_de: List[int] = Field(
        default_factory=list,
        description="IDs dos passos que devem vir antes, vazia se independente"
    )
    riscos: List[str] = Field(
        default_factory=list,
        description="O que pode dar errado neste passo"
    )
    rollback: Optional[str] = Field(
        None,
        description="Como desfazer se falhar, null se não aplicável"
    )


class Plan(BaseModel):
    """Plano de implementação detalhado."""

    objetivo: str = Field(..., description="Qual o objetivo do plano")
    pre_condicoes: List[str] = Field(
        default_factory=list,
        description="O que deve ser verdade antes de começar"
    )
    passos: List[Step] = Field(
        default_factory=list,
        description="Passos do plano em ordem sequencial"
    )
    pos_condicoes: List[str] = Field(
        default_factory=list,
        description="Como saber que terminou com sucesso"
    )


class PlanProblem(BaseModel):
    """Um problema encontrado em um plano."""

    tipo: Literal[
        "ordem",
        "falta_passo",
        "dependencia",
        "dependencia_ciclica",
        "dependencia_nao_resolvida",
        "dependencia_transitiva",
        "self_referencia",
        "rollback",
        "pre_condicao",
        "risco_omitido",
        "vago"
    ] = Field(..., description="Tipo do problema")
    passo: Optional[int] = Field(
        None,
        description="ID do passo com problema, null se for geral"
    )
    descricao: str = Field(..., description="Descrição clara do problema")


class PlanValidation(BaseModel):
    """Resultado da validação de um plano."""

    aprovado: bool = Field(..., description="True se SEM problemas críticos")
    problemas: List[PlanProblem] = Field(
        default_factory=list,
        description="Problemas encontrados, críticos primeiro"
    )
    passos_faltando: List[str] = Field(
        default_factory=list,
        description="Passos que deveriam estar no plano mas não estão"
    )
    sugestoes: List[str] = Field(
        default_factory=list,
        description="Sugestões de melhoria (não obrigatório)"
    )
