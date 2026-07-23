"""
Verdict schema com provenance (P6) e anti-sycophancy (P7).

Cada issue tem um `kind` que indica se é um fato determinístico
(verificável por máquina) ou uma opinião (juízo do revisor).

Nota de nomenclatura: nomeado ReviewVerdict/ReviewIssue para evitar
colisão com o `Verdict` de src/schemas/findings.py (usado pelos agentes
de verify já existentes). Este é o veredito do Revisor da Fase 5.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ReviewIssue(BaseModel):
    """Issue encontrada na revisão."""

    kind: Literal["deterministic", "opinion"] = Field(
        ...,
        description=(
            "deterministic = fato objetivo (teste falhou, lint acusou, contrato "
            "violado). opinion = juízo do revisor (design, clareza, estilo)."
        ),
    )
    severity: Literal["high", "medium", "low"] = Field(
        "medium", description="Impacto no sistema"
    )
    file: str | None = Field(None, description="Arquivo afetado (se aplicável)")
    line: int | None = Field(None, description="Linha aproximada (se aplicável)")
    title: str = Field(..., description="Título curto da issue")
    description: str = Field(..., description="Explicação do problema")
    evidence: str | None = Field(
        None,
        description=(
            "Fonte verificável que justifica a issue. Para issues deterministic, "
            "é OBRIGATÓRIO citar a fonte (nome do teste, regra de lint, contrato)."
        ),
    )
    suggestion: str | None = Field(
        None, description="Sugestão concreta de correção (opcional)"
    )


class ReviewVerdict(BaseModel):
    """Resultado estruturado de uma revisão."""

    status: Literal["approved", "changes_required", "rejected", "escalated"] = Field(
        ...,
        description=(
            "approved = passa para o próximo passo. changes_required = volta ao "
            "executor com issues. rejected = não pode ser corrigido, precisa de "
            "replanejamento. escalated = fora da capacidade do revisor."
        ),
    )
    confidence: float = Field(
        ..., ge=0.0, le=1.0, description="Confiança do revisor (0.0 a 1.0)"
    )
    summary: str = Field(
        ..., description="Resumo objetivo da decisão, sem floreios"
    )
    issues: list[ReviewIssue] = Field(
        default_factory=list, description="Lista de issues encontradas"
    )

    # P7 — Anti-sycophancy: aprovação exige evidência concreta
    approval_evidence: list[str] | None = Field(
        None,
        description=(
            "Quando status=approved, liste AS EVIDÊNCIAS concretas que justificam "
            "a aprovação (ex: 'pytest: 5 passed', 'ruff: 0 violations', 'contrato "
            "respeitado'). Aprovação sem evidência é tratada como suspeita (P7)."
        ),
    )

    @property
    def deterministic_issues(self) -> list[ReviewIssue]:
        return [i for i in self.issues if i.kind == "deterministic"]

    @property
    def opinion_issues(self) -> list[ReviewIssue]:
        return [i for i in self.issues if i.kind == "opinion"]

    @property
    def has_blocking_issues(self) -> bool:
        """Apenas issues deterministic bloqueiam o fluxo (P6)."""
        return len(self.deterministic_issues) > 0

    @property
    def is_suspicious_approval(self) -> bool:
        """P7: aprovação sem evidência concreta é suspeita."""
        if self.status != "approved":
            return False
        return not self.approval_evidence

    model_config = {"extra": "forbid"}
