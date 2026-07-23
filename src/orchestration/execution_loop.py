"""Execution Loop: deterministic state machine for the Direct Mode MVP.

Flow: EXECUTE → VALIDATE → (passed?) → DONE or RETRY
                                      → (failed + attempts < max?) → RETRY
                                      → (failed + attempts >= max?) → ESCALATE

This is the core loop that integrates:
- TierRouter (decides which provider handles each task)
- ValidationPipeline (deterministic quality gates before review)
- CostLedger (budget tracking per task)
- BaseAgent (actual LLM execution)
"""
from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from src.agents.executor.agent import ExecutorAgent, ExecutorResult
from src.orchestration.enforcement import EnforcementEngine
from src.routing.tier_router import TierRouter
from src.tools.worktree import WorktreeManager
from src.validators.pipeline import PipelineResult, ValidationPipeline
from src.validators.base import ValidationContext, ValidationStatus
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.review.contract_reviewer import ContractReviewerAgent

logger = logging.getLogger(__name__)


class ExecutionStatus(str, Enum):
    """Estados possíveis da execução."""
    PENDING = "pending"
    EXECUTING = "executing"
    VALIDATING = "validating"
    PASSED = "passed"           # Validação passou → pronto para revisão ou done
    MERGED = "merged"           # Alterações aplicadas no repositório real
    RETRYING = "retrying"       # Validação falhou → nova tentativa local
    ESCALATED = "escalated"     # Limite de tentativas atingido → escalar para API
    BLOCKED = "blocked"         # Tarefa STRONG sem budget → bloqueada
    ERROR = "error"             # Erro inesperado


from src.schemas.contract import TaskContract


@dataclass
class ExecutionResult:
    """Resultado completo de uma execução."""
    task_id: str
    status: ExecutionStatus
    output: str = ""
    diff: str = ""
    modified_files: list[str] = field(default_factory=list)
    validation_result: PipelineResult | None = None
    attempts_used: int = 0
    total_tokens: int = 0
    total_cost: float = 0.0
    duration_ms: float = 0.0
    escalation_reason: str = ""
    history: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "task_id": self.task_id,
            "status": self.status.value,
            "attempts_used": self.attempts_used,
            "total_tokens": self.total_tokens,
            "total_cost": round(self.total_cost, 4),
            "duration_ms": round(self.duration_ms, 2),
            "modified_files": self.modified_files,
            "validation_passed": self.validation_result.passed if self.validation_result else None,
            "escalation_reason": self.escalation_reason,
            "history_steps": len(self.history),
        }


class ExecutionLoop:
    """Máquina de estados para execução direta (MVP).

    Integra TierRouter + ValidationPipeline + CostLedger em um loop
    determinístico com limites rígidos de tentativas e orçamento.
    """

    def __init__(
        self,
        router: TierRouter,
        validation_pipeline: ValidationPipeline | None = None,
        executor: ExecutorAgent | None = None,
        worktree: WorktreeManager | None = None,
        reviewer = None,  # ContractReviewerAgent (import lazy para evitar circular)
        project_root: str = "",
        max_attempts_default: int = 3,
        max_cost_per_task: float = 0.50,  # USD
    ):
        self.router = router
        self.pipeline = validation_pipeline or ValidationPipeline()
        self._default_executor = executor
        self.worktree = worktree
        self._reviewer = reviewer
        self.project_root = project_root
        self.max_attempts_default = max_attempts_default
        self.max_cost_per_task = max_cost_per_task
        self.enforcement = EnforcementEngine()

    def execute(self, contract: TaskContract) -> ExecutionResult:
        """Executa uma tarefa seguindo o contrato de delegação.

        Flow:
        1. Classificar risco → decidir provider via TierRouter
        2. EXECUTE: chamar LLM com o contrato
        3. VALIDATE: rodar pipeline determinístico
        4. Se passou → DONE (status=PASSED)
        5. Se falhou e tentativas < max → RETRY (volta ao passo 2 com feedback)
        6. Se falhou e tentativas >= max → ESCALATE
        7. Se custo excedeu max_cost_per_task → ESCALATE
        """
        start = time.monotonic()
        result = ExecutionResult(task_id=contract.task_id, status=ExecutionStatus.PENDING)
        max_attempts = contract.max_attempts or self.max_attempts_default

        # Passo 1: Roteamento
        try:
            provider_name, classification = self.router.route(
                objective=contract.objective,
                files=contract.allowed_files,
                constraints=contract.constraints,
            )
            result.history.append({
                "step": "route",
                "provider": provider_name,
                "risk": classification.risk_score,
                "complexity": classification.complexity_score,
                "tier": classification.tier,
            })
            logger.info(
                f"[{contract.task_id}] Roteado para {provider_name} "
                f"(risk={classification.risk_score}, tier={classification.tier})"
            )
        except RuntimeError as e:
            # Tarefa STRONG sem budget disponível
            result.status = ExecutionStatus.BLOCKED
            result.escalation_reason = str(e)
            result.duration_ms = (time.monotonic() - start) * 1000
            logger.warning(f"[{contract.task_id}] BLOQUEADO: {e}")
            return result

        # Loop de execução + validação
        last_validation_feedback = ""

        # ── Worktree (Fase 6.0): execução isolada ─────────────────────
        _use_worktree = (
            self.worktree is not None
            and not self.worktree.active
            and contract.allowed_files
        )
        if _use_worktree:
            self.worktree._create(contract.allowed_files)
            logger.info(
                f"[{contract.task_id}] Worktree ativo: {self.worktree.worktree_path}"
            )
        # ───────────────────────────────────────────────────────────────

        for attempt in range(1, max_attempts + 1):
            result.attempts_used = attempt

            # Verificar budget da tarefa
            if result.total_cost >= self.max_cost_per_task:
                result.status = ExecutionStatus.ESCALATED
                result.escalation_reason = (
                    f"Orçamento da tarefa excedido: ${result.total_cost:.4f} "
                    f">= ${self.max_cost_per_task}"
                )
                break

            # Passo 2: EXECUTE
            result.status = ExecutionStatus.EXECUTING
            logger.info(f"[{contract.task_id}] Tentativa {attempt}/{max_attempts}")

            try:
                # Construir prompt com contrato + feedback anterior
                prompt = self._build_prompt(contract, last_validation_feedback)

                # Obter ou criar executor para o provider roteado
                executor = self._get_executor(provider_name)

                # Executar chamada real ao LLM
                exec_result: ExecutorResult = executor.execute_raw(prompt)

                if not exec_result.success:
                    result.status = ExecutionStatus.ERROR
                    result.escalation_reason = f"Erro no executor: {exec_result.error}"
                    result.history.append({
                        "step": "error",
                        "attempt": attempt,
                        "error": exec_result.error,
                        "provider": provider_name,
                    })
                    break

                result.output = exec_result.output
                result.total_tokens += exec_result.tokens_used
                result.total_cost += exec_result.cost

                # ── Worktree: aplicar output aos arquivos ──────────
                if _use_worktree and result.output.strip():
                    self.worktree.apply_output(
                        result.output, contract.allowed_files
                    )
                # ─────────────────────────────────────────────────────

                result.history.append({
                    "step": "execute",
                    "attempt": attempt,
                    "tokens": exec_result.tokens_used,
                    "cost": exec_result.cost,
                    "provider": provider_name,
                    "model": exec_result.model,
                    "output_length": len(exec_result.output),
                })

            except Exception as e:
                result.status = ExecutionStatus.ERROR
                result.escalation_reason = f"Erro na execução: {e}"
                result.history.append({"step": "error", "attempt": attempt, "error": str(e)})
                break

            # Passo 3: VALIDATE
            result.status = ExecutionStatus.VALIDATING

            validation_context = ValidationContext(
                changed_files=contract.allowed_files,
                project_root=str(self.worktree.worktree_path) if _use_worktree else self.project_root,
                stack=contract.stack,
                custom_commands={},
                diff=result.output,
                command_timeout=contract.command_timeout,
            )

            pipeline_result = self.pipeline.run(validation_context)
            result.validation_result = pipeline_result

            result.history.append({
                "step": "validate",
                "attempt": attempt,
                "status": pipeline_result.status.value,
                "duration_ms": pipeline_result.total_duration_ms,
            })

            # Passo 4: Decisão
            if pipeline_result.passed:
                # ── Enforcement P1 (Fase 5.4) ──────────────────────────
                enforcement_result = self.enforcement.check_output(
                    contract, result.output
                )
                result.history.append({
                    "step": "enforcement_p1",
                    "attempt": attempt,
                    "action": enforcement_result.action,
                    "reason": enforcement_result.reason,
                    "blocking_count": len(enforcement_result.blocking_issues),
                    "warnings_count": len(enforcement_result.warnings),
                })
                if enforcement_result.action in ("reject", "escalate"):
                    result.status = ExecutionStatus.ESCALATED
                    result.escalation_reason = (
                        f"Enforcement P1: {enforcement_result.reason}"
                    )
                    logger.warning(
                        f"[{contract.task_id}] Enforcement bloqueou: "
                        f"{enforcement_result.reason}"
                    )
                    break

                # ── Reviewer (Fase 6.2): P6 + P7 via cloud API ──────
                reviewer_needs_retry = False
                if self._reviewer:
                    validation_summary = (
                        f"Pipeline: {pipeline_result.status.value} "
                        f"({pipeline_result.total_duration_ms:.0f}ms)"
                    )
                    if pipeline_result.results:
                        for r in pipeline_result.results:
                            validation_summary += (
                                f"\n  {r.validator_name}: {r.status.value}"
                            )

                    try:
                        verdict = self._reviewer.review(
                            contract, result.output, validation_summary
                        )
                        enforcement_result = self.enforcement.evaluate(
                            contract, verdict, result.output,
                            validation_passed=True,
                        )
                        result.history.append({
                            "step": "enforcement_verdict",
                            "attempt": attempt,
                            "status": verdict.status,
                            "confidence": verdict.confidence,
                            "action": enforcement_result.action,
                            "reason": enforcement_result.reason,
                            "blocking_count": len(enforcement_result.blocking_issues),
                            "warnings_count": len(enforcement_result.warnings),
                            "opinion_count": len(verdict.opinion_issues),
                        })
                        logger.info(
                            f"[{contract.task_id}] Reviewer: "
                            f"status={verdict.status} "
                            f"action={enforcement_result.action}"
                        )

                        if enforcement_result.action == "retry":
                            issues_feedback = [
                                f"[{i.kind}] {i.title}: {i.description}"
                                for i in verdict.issues
                            ]
                            last_validation_feedback = (
                                f"Revisor solicitou correcoes:\n"
                                + "\n".join(issues_feedback[:5])
                            )
                            reviewer_needs_retry = True
                        elif enforcement_result.action == "reject":
                            result.status = ExecutionStatus.ESCALATED
                            result.escalation_reason = (
                                f"Revisor rejeitou: {verdict.summary}"
                            )
                            break
                        elif enforcement_result.action == "escalate":
                            result.status = ExecutionStatus.ESCALATED
                            result.escalation_reason = (
                                f"Revisor escalou: {verdict.summary}"
                            )
                            break
                        # approve_with_warnings → prossegue para merge
                    except Exception as e:
                        logger.error(
                            f"[{contract.task_id}] Reviewer falhou: {e}"
                        )
                        result.history.append({
                            "step": "enforcement_verdict",
                            "attempt": attempt,
                            "error": str(e),
                        })
                # ───────────────────────────────────────────────────────

                if reviewer_needs_retry:
                    if attempt < max_attempts:
                        result.status = ExecutionStatus.RETRYING
                        if _use_worktree:
                            self.worktree._reset_files(contract.allowed_files)
                        logger.warning(
                            f"[{contract.task_id}] Revisor pediu retry. "
                            f"Retentando... ({last_validation_feedback[:200]})"
                        )
                        continue
                    else:
                        result.status = ExecutionStatus.ESCALATED
                        result.escalation_reason = (
                            f"Limite de {max_attempts} tentativas atingido "
                            f"apos pedido de correcao do revisor"
                        )
                        break

                # ── Worktree: merge no repositório real ─────────────
                if _use_worktree:
                    result.diff = self.worktree.collect_diff(
                        contract.allowed_files
                    )
                    result.modified_files = self.worktree.merge(
                        contract.allowed_files
                    )
                    result.status = ExecutionStatus.MERGED
                    logger.info(
                        f"[{contract.task_id}] Merge: "
                        f"{len(result.modified_files)} arquivos alterados"
                    )
                else:
                    result.status = ExecutionStatus.PASSED
                # ─────────────────────────────────────────────────────

                logger.info(
                    f"[{contract.task_id}] Validação passou na tentativa {attempt}"
                )
                break
            else:
                # Preparar feedback para próxima tentativa
                failed_validators = [
                    f"{r.validator_name}: {r.message}"
                    for r in pipeline_result.failed_results
                ]
                last_validation_feedback = "\n".join(failed_validators)

                if attempt < max_attempts:
                    result.status = ExecutionStatus.RETRYING
                    # ── Worktree: reset files para estado original ──
                    if _use_worktree:
                        self.worktree._reset_files(contract.allowed_files)
                    # ─────────────────────────────────────────────────
                    logger.warning(
                        f"[{contract.task_id}] Validação falhou. "
                        f"Retentando... ({last_validation_feedback[:200]})"
                    )
                else:
                    result.status = ExecutionStatus.ESCALATED
                    result.escalation_reason = (
                        f"Limite de {max_attempts} tentativas atingido. "
                        f"Última falha: {last_validation_feedback[:300]}"
                    )
                    logger.warning(
                        f"[{contract.task_id}] ESCALADO após {max_attempts} tentativas"
                    )

        # ── Worktree cleanup ──────────────────────────────────────
        if _use_worktree and self.worktree.active:
            if result.status != ExecutionStatus.MERGED:
                self.worktree.discard()
            else:
                self.worktree._session_active = False
                self.worktree._worktree = None
                self.worktree._original_files = {}
        # ───────────────────────────────────────────────────────────

        result.duration_ms = (time.monotonic() - start) * 1000
        return result

    @staticmethod
    def _build_prompt(contract: TaskContract, previous_feedback: str = "") -> str:
        """Constrói o prompt estruturado para o executor local.

        O formato segue o contrato de delegação recomendado pelos documentos
        de pesquisa: objetivo claro + arquivos permitidos + restrições +
        critérios de aceite + feedback de tentativa anterior.
        """
        parts = [
            f"## Objetivo\n{contract.objective}",
            f"\n## Arquivos Permitidos\n{chr(10).join(f'- {f}' for f in contract.allowed_files) or '- Nenhum especificado'}",
        ]

        if contract.forbidden_files:
            parts.append(
                f"\n## Arquivos Proibidos\n{chr(10).join(f'- {f}' for f in contract.forbidden_files)}"
            )

        if contract.constraints:
            parts.append(
                f"\n## Restrições\n{chr(10).join(f'- {c}' for c in contract.constraints)}"
            )

        if contract.acceptance_criteria:
            parts.append(
                f"\n## Critérios de Aceite\n{chr(10).join(f'- {a}' for a in contract.acceptance_criteria)}"
            )

        if contract.context_snippets:
            parts.append(
                f"\n## Contexto Relevante\n{chr(10).join(contract.context_snippets)}"
            )

        if previous_feedback:
            parts.append(
                f"\n## Feedback da Tentativa Anterior\n"
                f"A validação falhou. Corrija os seguintes problemas:\n{previous_feedback}"
            )

        parts.append(f"\n## Formato de Saída\n{contract.output_format}")

        return "\n".join(parts)

    def _get_executor(self, provider_name: str) -> ExecutorAgent:
        """Obtém ou cria um ExecutorAgent para o provider especificado.

        Se o executor default já usa o mesmo provider, reutiliza.
        Caso contrário, cria um novo executor sob demanda (para escalonamento).
        """
        if (
            self._default_executor is not None
            and self._default_executor.provider_name == provider_name
        ):
            return self._default_executor

        # Criar executor específico para este provider
        logger.info(f"Criando ExecutorAgent para provider: {provider_name}")
        return ExecutorAgent(provider_name=provider_name)
