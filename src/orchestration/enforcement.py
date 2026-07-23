"""
Enforcement Engine — aplica P1, P6 e P7 no fluxo de execução.

Responsabilidades:
- P1 (Hierarquia de Autoridade): constraints do contrato e allowed_files
  são absolutos. Qualquer output que os viole é bloqueado, independente da
  "interpretação" do executor ou da aprovação do revisor.
- P6 (Provenance): issues deterministic (fatos) bloqueiam; opinion (juízos)
  viram sugestões que não bloqueiam.
- P7 (Anti-Sycophancy): aprovação sem evidência concreta é tratada como
  suspeita e força reavaliação.

Dois modos de uso:
- check_output(contract, output): checks P1 determinísticos, sem precisar de
  um Verdict. Usado pelo ExecutionLoop mesmo sem revisor LLM conectado.
- evaluate(contract, verdict, output, validation_passed): análise completa
  incluindo o Verdict do revisor. Usado quando houver um ReviewerAgent.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from typing import Any

from src.schemas.verdict import ReviewVerdict

logger = logging.getLogger(__name__)


@dataclass
class EnforcementResult:
    """Resultado da análise de enforcement."""

    action: str  # continue | retry | reject | escalate | approve_with_warnings
    reason: str
    blocking_issues: list = field(default_factory=list)
    warnings: list = field(default_factory=list)

    def __repr__(self) -> str:
        return f"EnforcementResult(action={self.action}, reason={self.reason!r})"


# Sinais de instalação de dependências (violação comum de constraint)
_INSTALL_SIGNALS = [
    "pip install", "npm install", "yarn add", "pnpm add", "uv add",
    "go get", "cargo add", "apt install", "apt-get install", "brew install",
    "composer require", "gem install",
]

# Padrões de diff (git unified) para extrair arquivos mencionados no output
_DIFF_PATTERNS = [
    r"^diff --git a/(.+?) b/",
    r"^\+\+\+ b/(.+)$",
    r"^--- a/(.+)$",
]


class EnforcementEngine:
    """Aplica regras duras sobre o output do executor e o Verdict do revisor.

    Este engine é a última palavra antes do loop decidir o próximo passo.
    Ele não depende de o revisor ser "honesto" — valida estruturalmente.
    """

    # ─────────────────────────────────────────────────────────────
    # MODO LEVE: só P1 (usado pelo ExecutionLoop sem revisor)
    # ─────────────────────────────────────────────────────────────
    def check_output(self, contract: Any, output: str | None) -> EnforcementResult:
        """Aplica apenas os checks determinísticos P1 sobre o output.

        Não requer um Verdict. Retorna 'continue' se nada violar, 'reject'
        se constraints ou allowed_files forem violados.
        """
        constraint_violations = self._check_constraints(contract, output)
        if constraint_violations:
            logger.warning(
                f"P1 enforcement: {len(constraint_violations)} constraint violation(s)"
            )
            return EnforcementResult(
                action="reject",
                reason=f"Constraints do contrato violadas: {constraint_violations}",
                blocking_issues=constraint_violations,
            )

        forbidden_changes = self._check_allowed_files(contract, output)
        if forbidden_changes:
            logger.warning(
                f"P1 enforcement: changes outside allowed_files: {forbidden_changes}"
            )
            return EnforcementResult(
                action="reject",
                reason=f"Arquivos fora do permitido foram alterados: {forbidden_changes}",
                blocking_issues=forbidden_changes,
            )

        return EnforcementResult(action="continue", reason="Checks P1 OK")

    # ─────────────────────────────────────────────────────────────
    # MODO COMPLETO: P1 + P6 + P7 (usado com ReviewerAgent)
    # ─────────────────────────────────────────────────────────────
    def evaluate(
        self,
        contract: Any,
        verdict: ReviewVerdict,
        executor_output: str | None = None,
        validation_passed: bool = True,
    ) -> EnforcementResult:
        """Avalia um Verdict contra o contrato e o output do executor."""
        # CHECK 1 (P1): constraints são absolutas
        constraint_violations = self._check_constraints(contract, executor_output)
        if constraint_violations:
            return EnforcementResult(
                action="reject",
                reason=f"Constraints do contrato violadas: {constraint_violations}",
                blocking_issues=constraint_violations,
            )

        # CHECK 2 (P1): allowed_files respeitado
        forbidden_changes = self._check_allowed_files(contract, executor_output)
        if forbidden_changes:
            return EnforcementResult(
                action="reject",
                reason=f"Arquivos fora do permitido foram alterados: {forbidden_changes}",
                blocking_issues=forbidden_changes,
            )

        # CHECK 3 (P7): aprovação sem evidência é suspeita
        if verdict.is_suspicious_approval:
            logger.warning("P7 enforcement: aprovação sem approval_evidence (suspeita)")
            return EnforcementResult(
                action="retry",
                reason=(
                    "Aprovação suspeita: revisor aprovou sem listar evidências "
                    "concretas (P7). Solicitar reavaliação com approval_evidence."
                ),
                warnings=["Aprovação sem evidência"],
            )

        # CHECK 4 (P6): issues deterministic bloqueiam
        if verdict.has_blocking_issues:
            deterministic = verdict.deterministic_issues
            return EnforcementResult(
                action="retry" if verdict.status == "changes_required" else "reject",
                reason=f"{len(deterministic)} issue(s) deterministic bloqueante(s)",
                blocking_issues=deterministic,
                warnings=(
                    [f"{len(verdict.opinion_issues)} opinion issue(s) (não bloqueiam)"]
                    if verdict.opinion_issues
                    else []
                ),
            )

        # CHECK 5: validação determinística externa
        if not validation_passed:
            return EnforcementResult(
                action="retry",
                reason="Validação determinística externa falhou (lint/teste/build)",
            )

        # CHECK 6: status do revisor
        if verdict.status == "approved":
            if verdict.opinion_issues:
                return EnforcementResult(
                    action="approve_with_warnings",
                    reason=(
                        f"Aprovado com {len(verdict.opinion_issues)} "
                        f"sugestão(ões) não-bloqueante(s)"
                    ),
                    warnings=[
                        f"{i.severity}: {i.title}" for i in verdict.opinion_issues
                    ],
                )
            return EnforcementResult(
                action="continue", reason="Aprovado limpo. Sem issues."
            )

        if verdict.status == "changes_required":
            return EnforcementResult(
                action="retry",
                reason="Revisor solicitou mudanças (apenas opinion issues)",
                warnings=[f"{i.severity}: {i.title}" for i in verdict.issues],
            )

        if verdict.status == "rejected":
            return EnforcementResult(
                action="reject", reason=f"Revisor rejeitou: {verdict.summary}"
            )

        if verdict.status == "escalated":
            return EnforcementResult(
                action="escalate", reason=f"Revisor escalou: {verdict.summary}"
            )

        return EnforcementResult(
            action="continue", reason=f"Status desconhecido: {verdict.status}"
        )

    # ─────────────────────────────────────────────────────────────
    # Helpers P1
    # ─────────────────────────────────────────────────────────────
    def _check_constraints(self, contract: Any, output: str | None) -> list[str]:
        """P1: detecta violações estruturais de constraints no output."""
        violations: list[str] = []
        if not output:
            return violations
        constraints = getattr(contract, "constraints", None) or []
        if not constraints:
            return violations

        out_lower = output.lower()
        for c in constraints:
            c_lower = c.lower()
            if (
                "não instalar" in c_lower
                or "não instale" in c_lower
                or "no new dependenc" in c_lower
            ):
                for sig in _INSTALL_SIGNALS:
                    if sig in out_lower:
                        violations.append(
                            f"Constraint '{c}' violada: detectado '{sig}' no output"
                        )
                        break
        return violations

    def _check_allowed_files(self, contract: Any, output: str | None) -> list[str]:
        """P1: detecta alterações em arquivos proibidos ou fora do permitido."""
        violations: list[str] = []
        if not output:
            return violations
        allowed = getattr(contract, "allowed_files", None) or []
        forbidden = getattr(contract, "forbidden_files", None) or []
        if not allowed and not forbidden:
            return violations

        mentioned: set[str] = set()
        for line in output.split("\n"):
            stripped = line.strip()
            for pattern in _DIFF_PATTERNS:
                match = re.match(pattern, stripped)
                if match:
                    mentioned.add(match.group(1).strip())

        for f in mentioned:
            if f in forbidden:
                violations.append(f"Arquivo proibido modificado: {f}")
            elif allowed and f not in allowed:
                violations.append(
                    f"Arquivo fora de allowed_files modificado: {f} "
                    f"(permitidos: {allowed})"
                )
        return violations
