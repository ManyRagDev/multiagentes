"""Skill /run — pipeline completo: Planner → Executor → Reviewer → Merge.

Fase 6.3: Comando unico que executa o ciclo completo do harness:
  1. Planner (cloud) transforma objetivo em TaskContract
  2. ExecutionLoop (local/cloud) gera codigo com worktree isolado
  3. Reviewer (cloud) audita output com P6+P7
  4. Se aprovado, faz merge no projeto real

Uso:
    python -m src run "Adicionar validacao de email no signup"
    python -m src run "Criar endpoint GET /products" --no-reviewer
    python -m src run "Implementar funcao soma_pares" --project-root ./myproject
"""
import sys
import time
from pathlib import Path

from src.agents.planning.contract_bridge import PlanContractAgent
from src.agents.review.contract_reviewer import ContractReviewerAgent
from src.orchestration.execution_loop import ExecutionLoop, ExecutionStatus
from src.routing.tier_router import TierRouter
from src.tools.worktree import WorktreeManager
from src.validators.pipeline import ValidationPipeline


def skill_run(
    objetivo: str,
    project_root: str = ".",
    contexto: str = "",
    use_reviewer: bool = True,
    max_attempts: int = 3,
) -> dict:
    """Pipeline completo: objetivo em NL → código no projeto.

    Args:
        objetivo: Descricao do que implementar
        project_root: Raiz do projeto alvo
        contexto: Contexto adicional para o Planner
        use_reviewer: Se True, chama Reviewer cloud apos execucao
        max_attempts: Maximo de tentativas de execucao

    Returns:
        dict com sucesso, status, diff, modified_files, tokens, cost, history
    """
    start_time = time.monotonic()
    project_path = Path(project_root).resolve()

    total_tokens = 0
    total_cost = 0.0

    # ── Etapa 1: Planner → TaskContract ────────────────────────────
    print("\n[1/3] Gerando contrato...")
    try:
        plan_agent = PlanContractAgent()
        contract = plan_agent.run_with_objective(objetivo, contexto)
        total_tokens += plan_agent._last_tokens
    except ValueError as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "needs_clarification": True,
            "etapa": "planning",
        }
    except RuntimeError as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "etapa": "planning",
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Planner API falhou: {e}",
            "etapa": "planning",
        }

    print(f"  Tier: {contract.tier or 'auto'}")
    print(f"  Arquivos: {contract.allowed_files or 'auto-detect'}")
    print(f"  Constraints: {len(contract.constraints)}")
    if contract.required_behavior:
        print(f"  required_behavior: presente")

    # ── Etapa 2: Preparar ExecutionLoop ────────────────────────────
    print(f"\n[2/3] Executando (max {max_attempts} tentativas)...")

    router = TierRouter()
    worktree = WorktreeManager(str(project_path))

    reviewer = None
    if use_reviewer:
        try:
            reviewer = ContractReviewerAgent()
            print("  Reviewer: cloud (P6+P7)")
        except Exception as e:
            print(f"  Reviewer indisponivel: {e}")

    loop = ExecutionLoop(
        router=router,
        validation_pipeline=ValidationPipeline(validators=[]),
        worktree=worktree,
        reviewer=reviewer,
        project_root=str(project_path),
        max_attempts_default=max_attempts,
    )

    # ── Etapa 3: Executar ──────────────────────────────────────────
    result = loop.execute(contract)

    total_tokens += result.total_tokens
    total_cost += result.total_cost

    # ── Resultado ──────────────────────────────────────────────────
    print(f"\n[3/3] Resultado: {result.status.value}")

    if result.status == ExecutionStatus.MERGED:
        print(f"  Arquivos modificados: {result.modified_files}")
        if result.diff:
            diff_preview = "\n".join(result.diff.split("\n")[:20])
            print(f"\n  --- Diff ---\n{diff_preview}\n  -----------")
    elif result.status == ExecutionStatus.ESCALATED:
        print(f"  Motivo: {result.escalation_reason}")
    elif result.status == ExecutionStatus.BLOCKED:
        print(f"  Motivo: {result.escalation_reason}")
    elif result.status == ExecutionStatus.ERROR:
        print(f"  Motivo: {result.escalation_reason}")

    duration_s = time.monotonic() - start_time
    print(f"\n  Tokens: {total_tokens} | Custo: ${total_cost:.4f} | Duracao: {duration_s:.1f}s")

    return {
        "sucesso": result.status in (ExecutionStatus.MERGED, ExecutionStatus.PASSED),
        "status": result.status.value,
        "diff": result.diff,
        "modified_files": result.modified_files,
        "tokens": total_tokens,
        "cost": total_cost,
        "duration_s": duration_s,
        "contract": contract.model_dump() if result.status != ExecutionStatus.BLOCKED else None,
        "history": result.to_dict(),
    }


def main():
    """Entry point CLI."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Multiagentes run — pipeline completo de implementacao",
    )
    parser.add_argument(
        "objetivo",
        help="O que implementar (ex: 'Adicionar validacao de email no signup')",
    )
    parser.add_argument(
        "--project-root", "-p",
        default=".",
        help="Diretorio raiz do projeto (default: .)",
    )
    parser.add_argument(
        "--contexto", "-c",
        default="",
        help="Contexto adicional para o Planner (stack, padroes, etc.)",
    )
    parser.add_argument(
        "--no-reviewer",
        action="store_true",
        help="Pula revisao cloud (usa apenas validacao P1 deterministica)",
    )
    parser.add_argument(
        "--max-attempts", "-m",
        type=int,
        default=3,
        help="Maximo de tentativas de execucao (default: 3)",
    )

    args = parser.parse_args()

    resultado = skill_run(
        objetivo=args.objetivo,
        project_root=args.project_root,
        contexto=args.contexto,
        use_reviewer=not args.no_reviewer,
        max_attempts=args.max_attempts,
    )

    if resultado["sucesso"]:
        sys.exit(0)
    else:
        print(f"\nFALHA: {resultado.get('erro', resultado.get('status', 'desconhecido'))}")
        if resultado.get("needs_clarification"):
            print("O Planner precisa de mais contexto. Adicione --contexto.")
        sys.exit(1)


if __name__ == "__main__":
    main()
