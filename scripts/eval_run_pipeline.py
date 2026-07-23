"""Teste Fase 6.3: CLI run — pipeline completo com mocks.

Valida:
1. CLI registrada e parseia argumentos
2. Fluxo skill_run com mocks (Planner → Loop → Merge)
3. Modo --no-reviewer funciona
4. Erro do Planner propagado corretamente
"""
import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas.contract import TaskContract
from src.orchestration.execution_loop import ExecutionStatus
from src.skills.run import skill_run


TEMPDIR = Path(__file__).parent.parent / "logs" / "run_test"
TEMPDIR.mkdir(parents=True, exist_ok=True)


def _setup_test_project():
    project = TEMPDIR / "testproject"
    import shutil
    if project.exists():
        shutil.rmtree(project, ignore_errors=True)
    (project / "src").mkdir(parents=True)
    (project / "src" / "math.py").write_text(
        "def add(a, b):\n    return a + b\n", encoding="utf-8"
    )
    return project


def banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_run_pipeline_full():
    """Teste 1: Pipeline completo (Planner + Loop) com mocks."""
    banner("TESTE 1: skill_run pipeline completo")

    project = _setup_test_project()

    mock_contract = TaskContract(
        task_id="run-001",
        objective="Adicionar docstring em add()",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=2,
    )

    with (
        patch("src.skills.run.PlanContractAgent") as mock_plan,
        patch("src.skills.run.TierRouter") as mock_router_cls,
        patch("src.skills.run.ExecutionLoop") as mock_loop_cls,
        patch("src.skills.run.ContractReviewerAgent") as mock_reviewer_cls,
    ):
        plan_instance = MagicMock()
        plan_instance.run_with_objective.return_value = mock_contract
        plan_instance._last_tokens = 100
        mock_plan.return_value = plan_instance

        mock_router = MagicMock()
        mock_router_cls.return_value = mock_router

        reviewer_instance = MagicMock()
        mock_reviewer_cls.return_value = reviewer_instance

        mock_loop = MagicMock()
        mock_result = MagicMock()
        mock_result.status = ExecutionStatus.MERGED
        mock_result.total_tokens = 50
        mock_result.total_cost = 0.0
        mock_result.diff = "def add(a, b):\n    \"\"\"Soma.\"\"\"\n    return a + b\n"
        mock_result.modified_files = ["src/math.py"]
        mock_result.to_dict.return_value = {"status": "merged"}
        mock_result.escalation_reason = ""
        mock_loop.execute.return_value = mock_result
        mock_loop_cls.return_value = mock_loop

        result = skill_run(
            objetivo="Adicionar docstring em add()",
            project_root=str(project),
            use_reviewer=True,
            max_attempts=2,
        )

        assert result["sucesso"]
        assert result["status"] == "merged"
        assert result["modified_files"] == ["src/math.py"]
        assert result["tokens"] == 150

        plan_instance.run_with_objective.assert_called_once()
        mock_loop_cls.assert_called_once()
        mock_loop.execute.assert_called_once()

        print("  [OK] Planner chamado → TaskContract gerado")
        print("  [OK] ExecutionLoop executado com reviewer")
        print(f"  [OK] Status: {result['status']}")
        print(f"  [OK] Tokens: {result['tokens']}")
        return True


def test_run_no_reviewer():
    """Teste 2: Modo --no-reviewer."""
    banner("TESTE 2: skill_run sem reviewer")

    project = _setup_test_project()

    mock_contract = TaskContract(
        task_id="run-002",
        objective="Teste",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        risk="low",
    )

    with (
        patch("src.skills.run.PlanContractAgent") as mock_plan,
        patch("src.skills.run.TierRouter") as mock_router_cls,
        patch("src.skills.run.ExecutionLoop") as mock_loop_cls,
    ):
        plan_instance = MagicMock()
        plan_instance.run_with_objective.return_value = mock_contract
        plan_instance._last_tokens = 50
        mock_plan.return_value = plan_instance

        mock_router = MagicMock()
        mock_router_cls.return_value = mock_router

        mock_loop = MagicMock()
        mock_result = MagicMock()
        mock_result.status = ExecutionStatus.MERGED
        mock_result.total_tokens = 30
        mock_result.total_cost = 0.0
        mock_result.diff = ""
        mock_result.modified_files = []
        mock_result.to_dict.return_value = {"status": "merged"}
        mock_result.escalation_reason = ""
        mock_loop.execute.return_value = mock_result
        mock_loop_cls.return_value = mock_loop

        result = skill_run(
            objetivo="Teste",
            project_root=str(project),
            use_reviewer=False,
            max_attempts=2,
        )

        assert result["sucesso"]

        call_kwargs = mock_loop_cls.call_args[1]
        assert call_kwargs["reviewer"] is None
        print("  [OK] Reviewer nao foi passado para ExecutionLoop")
        print("  [OK] Pipeline executou sem reviewer")
        return True


def test_run_planner_needs_clarification():
    """Teste 3: Planner retorna needs_clarification."""
    banner("TESTE 3: Planner needs_clarification")

    project = _setup_test_project()

    with patch("src.skills.run.PlanContractAgent") as mock_plan:
        plan_instance = MagicMock()
        plan_instance.run_with_objective.side_effect = ValueError(
            "Planner precisa de mais contexto: Qual framework usar?"
        )
        mock_plan.return_value = plan_instance

        result = skill_run(
            objetivo="Algo ambiguo",
            project_root=str(project),
            use_reviewer=False,
        )

        assert not result["sucesso"]
        assert result["needs_clarification"]
        assert result["etapa"] == "planning"
        print("  [OK] needs_clarification detectado")
        print(f"  [OK] Erro: {result['erro'][:80]}")
        return True


def test_run_planner_failure():
    """Teste 4: Planner falha com erro generico."""
    banner("TESTE 4: Planner API failure")

    project = _setup_test_project()

    with patch("src.skills.run.PlanContractAgent") as mock_plan:
        plan_instance = MagicMock()
        plan_instance.run_with_objective.side_effect = RuntimeError(
            "PlanContractAgent falhou: API timeout"
        )
        mock_plan.return_value = plan_instance

        result = skill_run(
            objetivo="Qualquer coisa",
            project_root=str(project),
        )

        assert not result["sucesso"]
        assert result["etapa"] == "planning"
        assert "API timeout" in result["erro"]
        print("  [OK] Erro de API propagado corretamente")
        return True


def test_cli_help():
    """Teste 5: CLI help mostra opcoes."""
    banner("TESTE 5: CLI help")

    import subprocess
    result = subprocess.run(
        [sys.executable, "-m", "src", "run", "--help"],
        capture_output=True, text=True,
        cwd=str(Path(__file__).parent.parent),
    )

    output = result.stdout
    checks = [
        ("--no-reviewer", "flag no-reviewer"),
        ("--project-root", "flag project-root"),
        ("--contexto", "flag contexto"),
        ("--max-attempts", "flag max-attempts"),
        ("objetivo", "argumento objetivo"),
    ]

    passed = 0
    for flag, desc in checks:
        if flag in output:
            print(f"  [OK] {desc}")
            passed += 1
        else:
            print(f"  [FALHA] {desc} nao encontrado")

    print(f"\n  CLI args: {passed}/{len(checks)}")
    return passed == len(checks)


def main():
    print("=" * 60)
    print("  FASE 6.3 — CLI Unificada: multiagentes run")
    print("=" * 60)

    results = {
        "pipeline_full": test_run_pipeline_full(),
        "no_reviewer": test_run_no_reviewer(),
        "needs_clarification": test_run_planner_needs_clarification(),
        "planner_failure": test_run_planner_failure(),
        "cli_help": test_cli_help(),
    }

    banner("RESUMO")
    passed = sum(1 for v in results.values() if v)
    for name, ok in results.items():
        print(f"  {'[OK]' if ok else '[FALHA]'} {name}")

    print(f"\n  Total: {passed}/{len(results)}")

    import shutil
    shutil.rmtree(TEMPDIR, ignore_errors=True)

    if passed == len(results):
        print("\n  Fase 6.3 validada!")
        sys.exit(0)
    else:
        print("\n  Alguns testes falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()
