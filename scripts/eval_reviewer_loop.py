"""Teste Fase 6.2: Reviewer cloud integrado no ExecutionLoop.

Valida:
1. ContractReviewerAgent carrega prompt e schema
2. Reviewer mock integrado no ExecutionLoop (diversos cenarios)
3. Enforcement.evaluate() com verdict real do reviewer
4. Loop reage a: approve, retry, reject, escalate
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import MagicMock
from src.orchestration.execution_loop import ExecutionLoop, ExecutionStatus
from src.orchestration.enforcement import EnforcementEngine
from src.schemas.contract import TaskContract
from src.schemas.verdict import ReviewVerdict, ReviewIssue
from src.tools.worktree import WorktreeManager
from src.agents.review.contract_reviewer import ContractReviewerAgent
from src.validators.pipeline import ValidationPipeline


TEMPDIR = Path(__file__).parent.parent / "logs" / "reviewer_test"
TEMPDIR.mkdir(parents=True, exist_ok=True)


def _mock_client():
    return MagicMock()


def banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


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


def _mock_loop(project, reviewer_mock=None):
    """Cria ExecutionLoop com mocks de router e executor."""
    mock_router = MagicMock()
    mock_class = MagicMock()
    mock_class.risk_score = 0
    mock_class.complexity_score = 1
    mock_class.tier = "local"
    mock_router.route.return_value = ("local-qwen", mock_class)

    loop = ExecutionLoop(
        router=mock_router,
        worktree=WorktreeManager(project),
        project_root=str(project),
        validation_pipeline=ValidationPipeline(validators=[]),
        reviewer=reviewer_mock,
        max_attempts_default=2,
        max_cost_per_task=10.0,
    )

    mock_exec = MagicMock()
    mock_exec.provider_name = "local-qwen"
    mock_res = MagicMock()
    mock_res.success = True
    mock_res.output = (
        'def add(a, b):\n'
        '    """Soma dois numeros."""\n'
        '    return a + b\n'
    )
    mock_res.tokens_used = 50
    mock_res.cost = 0.0
    mock_res.model = "qwen"
    mock_res.error = None
    mock_res.metadata = {}
    mock_exec.execute_raw.return_value = mock_res
    loop._default_executor = mock_exec

    return loop


# ─────────────────────────────────────────────────────────────
# TESTE 1: Agent carrega prompt e schema
# ─────────────────────────────────────────────────────────────
def test_agent_loads():
    banner("TESTE 1: ContractReviewerAgent carrega prompt")
    agent = ContractReviewerAgent(client=_mock_client())
    try:
        prompt = agent.load_prompt()
        assert "Anti-Sycophancy" in prompt
        assert "Provenance" in prompt
        assert "deterministic" in prompt
        assert "opinion" in prompt
        assert "approval_evidence" in prompt
        print(f"  [OK] Prompt carregado: {len(prompt)} chars")
        print("  [OK] P6 Provenance presente")
        print("  [OK] P7 Anti-Sycophancy presente")
        print("  [OK] deterministic/opinion classification presente")
        print("  [OK] approval_evidence presente")
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        return False


# ─────────────────────────────────────────────────────────────
# TESTE 2: Parse ReviewVerdict
# ─────────────────────────────────────────────────────────────
def test_parse_verdict():
    banner("TESTE 2: Parse ReviewVerdict JSON")
    agent = ContractReviewerAgent(client=_mock_client())

    cases = [
        {
            "name": "Aprovacao com evidencia",
            "json_str": json.dumps({
                "status": "approved",
                "confidence": 0.9,
                "summary": "Codigo atende aos criterios.",
                "issues": [],
                "approval_evidence": ["pytest: 1 passed", "lint: 0 violations"],
            }),
            "checks": lambda v: (
                v.status == "approved"
                and v.approval_evidence is not None
                and len(v.approval_evidence) == 2
            ),
        },
        {
            "name": "Rejeicao com issues deterministic",
            "json_str": json.dumps({
                "status": "changes_required",
                "confidence": 0.85,
                "summary": "Teste falhou.",
                "issues": [
                    {
                        "kind": "deterministic",
                        "severity": "high",
                        "title": "Teste falhou",
                        "description": "pytest falhou",
                        "evidence": "exit code 1",
                    },
                    {
                        "kind": "opinion",
                        "severity": "low",
                        "title": "Nomenclatura",
                        "description": "variavel x pouco descritiva",
                    },
                ],
                "approval_evidence": None,
            }),
            "checks": lambda v: (
                v.has_blocking_issues
                and len(v.deterministic_issues) == 1
                and len(v.opinion_issues) == 1
            ),
        },
    ]

    passed = 0
    for c in cases:
        try:
            verdict = agent.parse_output(c["json_str"])
            if c["checks"](verdict):
                print(f"  [OK] {c['name']}")
                passed += 1
            else:
                print(f"  [FALHA] {c['name']}")
        except Exception as e:
            print(f"  [ERRO] {c['name']}: {e}")

    print(f"\n  Parse: {passed}/{len(cases)}")
    return passed == len(cases)


# ─────────────────────────────────────────────────────────────
# TESTE 3: Loop aprova quando reviewer aprova com evidencia
# ─────────────────────────────────────────────────────────────
def test_reviewer_approve():
    banner("TESTE 3: Loop aprova com reviewer aprovando (evidencia)")

    project = _setup_test_project()
    mock_reviewer = MagicMock(spec=ContractReviewerAgent)

    approve_verdict = ReviewVerdict(
        status="approved",
        confidence=0.9,
        summary="Codigo OK.",
        issues=[],
        approval_evidence=["pytest: 1 passed", "lint: 0"],
    )
    mock_reviewer.review.return_value = approve_verdict

    loop = _mock_loop(project, mock_reviewer)

    contract = TaskContract(
        task_id="rv-001",
        objective="Adicionar docstring em add()",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=2,
    )

    try:
        result = loop.execute(contract)
        print(f"  Status: {result.status.value}")
        print(f"  Modified: {result.modified_files}")

        assert result.status == ExecutionStatus.MERGED
        assert "src/math.py" in result.modified_files

        real_content = (project / "src/math.py").read_text(encoding="utf-8")
        assert "Soma dois numeros" in real_content
        print("  [OK] Reviewer aprovou → codigo merged no projeto")
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        return False
    finally:
        wt = getattr(loop, 'worktree', None)
        if wt and wt.active:
            wt._session_active = False
            wt._worktree = None


# ─────────────────────────────────────────────────────────────
# TESTE 4: Loop retry quando reviewer pede changes_required
# ─────────────────────────────────────────────────────────────
def test_reviewer_retry():
    banner("TESTE 4: Loop retry com reviewer pedindo changes_required")

    project = _setup_test_project()
    mock_reviewer = MagicMock(spec=ContractReviewerAgent)

    reject_verdict = ReviewVerdict(
        status="changes_required",
        confidence=0.85,
        summary="Teste falhou.",
        issues=[
            ReviewIssue(
                kind="deterministic",
                severity="high",
                title="Teste falhou",
                description="pytest falhou no teste test_add",
                evidence="exit code 1",
            ),
        ],
        approval_evidence=None,
    )
    mock_reviewer.review.return_value = reject_verdict

    loop = _mock_loop(project, mock_reviewer)

    contract = TaskContract(
        task_id="rv-002",
        objective="Adicionar docstring em add()",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=2,
    )

    try:
        result = loop.execute(contract)
        print(f"  Status: {result.status.value}")
        print(f"  Attempts: {result.attempts_used}")

        # Deve ter feito retry e depois escalado (max_attempts=2)
        assert result.status in (ExecutionStatus.RETRYING, ExecutionStatus.ESCALATED)
        assert result.attempts_used >= 1

        history_statuses = [h.get("step") for h in result.history]
        assert "enforcement_verdict" in history_statuses
        print(f"  [OK] Reviewer pediu retry → loop tentou novamente")
        print(f"  [OK] History: {history_statuses}")
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        return False
    finally:
        wt = getattr(loop, 'worktree', None)
        if wt and wt.active:
            wt._session_active = False
            wt._worktree = None


# ─────────────────────────────────────────────────────────────
# TESTE 5: Reviewer escalou → loop escala
# ─────────────────────────────────────────────────────────────
def test_reviewer_escalate():
    banner("TESTE 5: Reviewer escalou → loop escala")

    project = _setup_test_project()
    mock_reviewer = MagicMock(spec=ContractReviewerAgent)

    escalate_verdict = ReviewVerdict(
        status="escalated",
        confidence=0.5,
        summary="Contexto insuficiente para revisar.",
        issues=[],
        approval_evidence=None,
    )
    mock_reviewer.review.return_value = escalate_verdict

    loop = _mock_loop(project, mock_reviewer)

    contract = TaskContract(
        task_id="rv-003",
        objective="Adicionar docstring em add()",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=2,
    )

    try:
        result = loop.execute(contract)
        print(f"  Status: {result.status.value}")

        assert result.status == ExecutionStatus.ESCALATED
        assert "escalou" in result.escalation_reason.lower()
        print(f"  [OK] Reviewer escalou → loop escalou")
        print(f"  [OK] Reason: {result.escalation_reason[:80]}")
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        return False
    finally:
        wt = getattr(loop, 'worktree', None)
        if wt and wt.active:
            wt._session_active = False
            wt._worktree = None


# ─────────────────────────────────────────────────────────────
# TESTE 6: Envio de feedback do reviewer para retry do executor
# ─────────────────────────────────────────────────────────────
def test_reviewer_feedback_to_executor():
    banner("TESTE 6: Feedback do reviewer vai para prompt de retry")

    project = _setup_test_project()
    mock_reviewer = MagicMock(spec=ContractReviewerAgent)

    reject_verdict = ReviewVerdict(
        status="changes_required",
        confidence=0.8,
        summary="Bug encontrado.",
        issues=[
            ReviewIssue(
                kind="deterministic",
                severity="high",
                title="Bug X",
                description="A funcao retorna None para input vazio",
                evidence="pytest test_empty falhou",
            ),
        ],
        approval_evidence=None,
    )
    mock_reviewer.review.return_value = reject_verdict

    loop = _mock_loop(project, mock_reviewer)

    # Spy no _build_prompt para verificar que recebeu feedback
    original_build = loop._build_prompt
    captured_prompts = []

    def spy_build(contract, feedback=""):
        result = original_build(contract, feedback)
        captured_prompts.append((feedback, result))
        return result

    loop._build_prompt = spy_build

    contract = TaskContract(
        task_id="rv-004",
        objective="Adicionar docstring em add()",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=2,
    )

    try:
        loop.execute(contract)

        assert len(captured_prompts) >= 2
        second_feedback = captured_prompts[1][0]
        assert "Revisor solicitou" in second_feedback or "deterministic" in second_feedback
        print(f"  [OK] Retry prompt inclui feedback do reviewer")
        print(f"  [OK] Feedback: {second_feedback[:120]}...")
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        return False
    finally:
        wt = getattr(loop, 'worktree', None)
        if wt and wt.active:
            wt._session_active = False
            wt._worktree = None


# ─────────────────────────────────────────────────────────────
# TESTE 7: Loop sem reviewer (modo leve) continua funcionando
# ─────────────────────────────────────────────────────────────
def test_no_reviewer_still_works():
    banner("TESTE 7: Loop sem reviewer (backward compatible)")

    project = _setup_test_project()
    loop = _mock_loop(project, reviewer_mock=None)

    contract = TaskContract(
        task_id="rv-005",
        objective="Adicionar docstring em add()",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=2,
    )

    try:
        result = loop.execute(contract)
        print(f"  Status: {result.status.value}")

        assert result.status == ExecutionStatus.MERGED
        assert "src/math.py" in result.modified_files
        print("  [OK] Modo sem reviewer funciona (P1 apenas)")
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        return False
    finally:
        wt = getattr(loop, 'worktree', None)
        if wt and wt.active:
            wt._session_active = False
            wt._worktree = None


def main():
    print("=" * 60)
    print("  FASE 6.2 — Reviewer cloud no ExecutionLoop")
    print("=" * 60)

    results = {
        "agent_loads": test_agent_loads(),
        "parse_verdict": test_parse_verdict(),
        "reviewer_approve": test_reviewer_approve(),
        "reviewer_retry": test_reviewer_retry(),
        "reviewer_escalate": test_reviewer_escalate(),
        "feedback_to_executor": test_reviewer_feedback_to_executor(),
        "no_reviewer_still_works": test_no_reviewer_still_works(),
    }

    banner("RESUMO")
    passed = sum(1 for v in results.values() if v)
    for name, ok in results.items():
        print(f"  {'[OK]' if ok else '[FALHA]'} {name}")

    print(f"\n  Total: {passed}/{len(results)}")

    import shutil
    shutil.rmtree(TEMPDIR, ignore_errors=True)

    if passed == len(results):
        print("\n  Fase 6.2 validada!")
        sys.exit(0)
    else:
        print("\n  Alguns testes falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()
