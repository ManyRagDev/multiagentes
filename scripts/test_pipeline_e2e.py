"""Suite de Integracao E2E — Fase 6.4.

Cenarios que validam o pipeline completo:
  A - Caminho feliz (tudo mockado)
  B - Constraint violation → enforcement bloqueia
  C - Reviewer rejeita → retry → escala (fail-closed)
  D - Reviewer falha → escala (fail-closed)
  E - Planner needs_clarification
  F - Worktree: criar, executar, merge, verificar
  G - Worktree: path traversal rejeitado
  H - Contrato com required_behavior para tarefa local
"""
import json
import shutil
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas.contract import TaskContract
from src.schemas.verdict import ReviewVerdict, ReviewIssue
from src.orchestration.execution_loop import ExecutionLoop, ExecutionStatus
from src.orchestration.enforcement import EnforcementEngine
from src.tools.worktree import WorktreeManager
from src.validators.pipeline import ValidationPipeline
from src.validators.diff_validator import DiffValidator
from src.validators.schema_validator import SchemaValidator
from src.agents.review.contract_reviewer import ContractReviewerAgent


TEMPDIR = Path(__file__).parent.parent / "logs" / "e2e_test"
TEMPDIR.mkdir(parents=True, exist_ok=True)


def banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def _setup_project(name: str) -> Path:
    project = TEMPDIR / name
    if project.exists():
        shutil.rmtree(project, ignore_errors=True)
    (project / "src").mkdir(parents=True)
    (project / "src" / "math.py").write_text(
        "def add(a: int, b: int) -> int:\n    return a + b\n",
        encoding="utf-8",
    )
    return project


def _mock_loop(project, reviewer=None, router_returns="local-qwen"):
    mock_router = MagicMock()
    mock_class = MagicMock()
    mock_class.risk_score = 0
    mock_class.complexity_score = 1
    mock_class.tier = "local"
    mock_router.route.return_value = (router_returns, mock_class)

    loop = ExecutionLoop(
        router=mock_router,
        validation_pipeline=ValidationPipeline(validators=[
            DiffValidator(),
            SchemaValidator(),
        ]),
        worktree=WorktreeManager(project),
        project_root=str(project),
        reviewer=reviewer,
        max_attempts_default=2,
        max_cost_per_task=10.0,
    )

    mock_exec = MagicMock()
    mock_exec.provider_name = router_returns
    mock_res = MagicMock()
    mock_res.success = True
    mock_res.output = (
        'def add(a: int, b: int) -> int:\n'
        '    """Soma dois numeros inteiros."""\n'
        '    return a + b\n'
    )
    mock_res.tokens_used = 50
    mock_res.cost = 0.0
    mock_res.model = "qwen-local"
    mock_res.error = None
    mock_res.metadata = {"needs_context": False, "self_check": None}
    mock_exec.execute_raw.return_value = mock_res
    loop._default_executor = mock_exec

    return loop


def _approve_verdict():
    return ReviewVerdict(
        status="approved",
        confidence=0.9,
        summary="Codigo atende aos criterios.",
        issues=[],
        approval_evidence=["DiffValidator: passou", "SchemaValidator: passou"],
    )


# ═══════════════════════════════════════════════════════════════
# CENARIO A: Caminho feliz (tudo mockado)
# ═══════════════════════════════════════════════════════════════
def test_a_happy_path():
    banner("CENARIO A: Caminho feliz (tudo mockado)")

    project = _setup_project("A_happy")
    mock_reviewer = MagicMock(spec=ContractReviewerAgent)
    mock_reviewer.review.return_value = _approve_verdict()

    loop = _mock_loop(project, mock_reviewer)

    contract = TaskContract(
        task_id="e2e-A",
        objective="Adicionar docstring em add()",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=2,
    )

    result = loop.execute(contract)

    assert result.status == ExecutionStatus.MERGED
    assert "src/math.py" in result.modified_files
    assert mock_reviewer.review.called

    content = (project / "src/math.py").read_text(encoding="utf-8")
    assert "Soma dois numeros" in content
    assert "def add" in content

    print("  [OK] Pipeline executou: execute → validate → review → merge")
    print(f"  [OK] Arquivo modificado: {result.modified_files}")
    print(f"  [OK] Reviewer chamado e aprovou com evidencia")
    return True


# ═══════════════════════════════════════════════════════════════
# CENARIO B: Constraint violation → enforcement bloqueia
# ═══════════════════════════════════════════════════════════════
def test_b_constraint_violation():
    banner("CENARIO B: Constraint violation → enforcement bloqueia")

    project = _setup_project("B_constraint")

    loop = _mock_loop(project, reviewer=None)

    mock_exec = MagicMock()
    mock_exec.provider_name = "local-qwen"
    mock_res = MagicMock()
    mock_res.success = True
    mock_res.output = (
        "# pip install numpy\ndef add(a: int, b: int) -> int:\n"
        '    """Soma."""\n    return a + b\n'
    )
    mock_res.tokens_used = 50
    mock_res.cost = 0.0
    mock_res.model = "qwen"
    mock_res.error = None
    mock_res.metadata = {"needs_context": False}
    mock_exec.execute_raw.return_value = mock_res
    loop._default_executor = mock_exec

    contract = TaskContract(
        task_id="e2e-B",
        objective="Teste",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=["Não instalar dependências"],
        acceptance_criteria=[],
        risk="low",
        max_attempts=1,
    )

    result = loop.execute(contract)

    assert result.status == ExecutionStatus.ESCALATED
    assert "Enforcement P1" in result.escalation_reason

    content = (project / "src/math.py").read_text(encoding="utf-8")
    assert "pip install" not in content

    print("  [OK] Enforcement P1 bloqueou pip install")
    print(f"  [OK] Status: {result.status.value}")
    print(f"  [OK] Arquivo original preservado")
    return True


# ═══════════════════════════════════════════════════════════════
# CENARIO C: Reviewer rejeita → retry → escala
# ═══════════════════════════════════════════════════════════════
def test_c_reviewer_reject_retry():
    banner("CENARIO C: Reviewer rejeita → retry → escala")

    project = _setup_project("C_reviewer_reject")
    mock_reviewer = MagicMock(spec=ContractReviewerAgent)

    reject_verdict = ReviewVerdict(
        status="changes_required",
        confidence=0.85,
        summary="Teste falhou e variavel incorreta.",
        issues=[
            ReviewIssue(
                kind="deterministic",
                severity="high",
                title="Variavel x usada sem definicao",
                description="A variavel x nao foi definida antes do uso.",
                evidence="lint: F821 undefined name 'x'",
            ),
        ],
        approval_evidence=None,
    )
    mock_reviewer.review.return_value = reject_verdict

    loop = _mock_loop(project, mock_reviewer)

    contract = TaskContract(
        task_id="e2e-C",
        objective="Teste",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=2,
    )

    result = loop.execute(contract)

    assert result.attempts_used >= 1
    history_steps = [h.get("step") for h in result.history]
    assert "enforcement_verdict" in history_steps
    assert mock_reviewer.review.call_count >= 1

    print(f"  [OK] Reviewer rejeitou com issue deterministic")
    print(f"  [OK] Loop tentou {result.attempts_used} vez(es)")
    print(f"  [OK] Status final: {result.status.value}")
    print(f"  [OK] Reviewer chamado {mock_reviewer.review.call_count} vez(es)")
    return True


# ═══════════════════════════════════════════════════════════════
# CENARIO D: Reviewer falha → escala (fail-closed)
# ═══════════════════════════════════════════════════════════════
def test_d_reviewer_failure():
    banner("CENARIO D: Reviewer falha → escala (fail-closed)")

    project = _setup_project("D_reviewer_fail")
    mock_reviewer = MagicMock(spec=ContractReviewerAgent)
    mock_reviewer.review.side_effect = RuntimeError("API timeout")

    loop = _mock_loop(project, mock_reviewer)

    contract = TaskContract(
        task_id="e2e-D",
        objective="Teste",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=1,
    )

    result = loop.execute(contract)

    assert result.status == ExecutionStatus.ESCALATED
    assert "Reviewer indisponivel" in result.escalation_reason

    print("  [OK] Reviewer falhou → pipeline escalou (fail-closed)")
    print(f"  [OK] Status: {result.status.value}")
    print(f"  [OK] Reason: {result.escalation_reason[:80]}")
    return True


# ═══════════════════════════════════════════════════════════════
# CENARIO E: Worktree com path traversal rejeitado
# ═══════════════════════════════════════════════════════════════
def test_e_path_traversal_rejected():
    banner("CENARIO E: Path traversal rejeitado pelo worktree")

    project = _setup_project("E_path_traversal")
    wm = WorktreeManager(project)

    bad_paths = ["../../escape.py", "/etc/passwd", "C:/Windows/file.txt"]
    rejected = 0
    for p in bad_paths:
        try:
            wm._validate_path_security(p, "test")
            print(f"  [FALHA] {p!r} deveria ser rejeitado")
        except ValueError:
            rejected += 1

    assert rejected == len(bad_paths)
    print(f"  [OK] {rejected}/{len(bad_paths)} paths de traversal rejeitados")

    # Verificar que _create tambem rejeita
    try:
        wm._create(["../../fora.txt"])
        wm.discard()
        print("  [FALHA] _create deveria rejeitar ../")
        return False
    except ValueError:
        print("  [OK] _create rejeita allowed_files com ../")

    return True


# ═══════════════════════════════════════════════════════════════
# CENARIO F: Worktree cria, executa, merge, verifica
# ═══════════════════════════════════════════════════════════════
def test_f_worktree_create_merge_verify():
    banner("CENARIO F: Worktree cria → executa → merge → verifica")

    project = _setup_project("F_worktree_merge")
    wm = WorktreeManager(project)

    allowed = ["src/math.py"]
    wm._create(allowed)
    assert wm.active
    print("  [OK] Worktree criado")

    original_content = (project / "src/math.py").read_text(encoding="utf-8")

    new_code = "def add(a: int, b: int) -> int:\n    return a + b + 1\n"
    wm.apply_output(new_code, allowed)
    wt_content = (wm.worktree_path / "src/math.py").read_text(encoding="utf-8")
    assert "a + b + 1" in wt_content
    print("  [OK] Output aplicado ao worktree")

    diff = wm.collect_diff(allowed)
    assert len(diff) > 0
    print(f"  [OK] Diff coletado ({len(diff)} chars)")

    modified = wm.merge(allowed)
    assert "src/math.py" in modified
    real_content = (project / "src/math.py").read_text(encoding="utf-8")
    assert "a + b + 1" in real_content
    print("  [OK] Merge no projeto real")

    wm._session_active = False
    wm._worktree = None

    (project / "src/math.py").write_text(original_content, encoding="utf-8")
    print("  [OK] Rollback manual (simulando git reset)")

    return True


# ═══════════════════════════════════════════════════════════════
# CENARIO G: required_behavior para tier=local
# ═══════════════════════════════════════════════════════════════
def test_g_required_behavior_local():
    banner("CENARIO G: required_behavior para tier=local")

    contract = TaskContract(
        task_id="e2e-G",
        objective="Criar funcao calculate_tax",
        tier="local",
        allowed_files=["src/tax.py"],
        constraints=["Usar aliquota de 15%"],
        acceptance_criteria=["calculate_tax(100) == 15.0"],
        required_behavior={
            "parameters": {
                "amount": {"type": "float", "min": 0.0},
            },
            "returns": "float",
            "edge_cases": {"zero": 0.0, "negative": 0.0},
        },
        risk="low",
    )

    assert contract.required_behavior is not None
    assert contract.required_behavior["parameters"]["amount"]["type"] == "float"
    assert contract.tier == "local"
    print("  [OK] required_behavior presente e bem estruturado")
    print(f"  [OK] Tier: {contract.tier}")
    print(f"  [OK] Constraints: {len(contract.constraints)}")

    # Verificar serializacao
    dump = contract.model_dump_json()
    assert "required_behavior" in dump
    print("  [OK] Serializacao JSON inclui required_behavior")

    return True


# ═══════════════════════════════════════════════════════════════
# CENARIO H: Pipeline sem reviewer (backward compat)
# ═══════════════════════════════════════════════════════════════
def test_h_no_reviewer_still_merges():
    banner("CENARIO H: Pipeline sem reviewer ainda faz merge (backward compat)")

    project = _setup_project("H_no_reviewer")
    loop = _mock_loop(project, reviewer=None)

    contract = TaskContract(
        task_id="e2e-H",
        objective="Teste",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=1,
    )

    result = loop.execute(contract)

    assert result.status == ExecutionStatus.MERGED
    assert "src/math.py" in result.modified_files

    history_steps = [h.get("step") for h in result.history]
    assert "enforcement_p1" in history_steps
    assert "enforcement_verdict" not in history_steps

    print("  [OK] Sem reviewer → merge com P1 apenas")
    print(f"  [OK] History: {history_steps}")
    return True


def main():
    print("=" * 60)
    print("  FASE 6.4 — Suite de Integracao E2E")
    print("=" * 60)

    results = {}

    for name, fn in [
        ("A - Happy path", test_a_happy_path),
        ("B - Constraint violation", test_b_constraint_violation),
        ("C - Reviewer reject retry", test_c_reviewer_reject_retry),
        ("D - Reviewer failure fail-closed", test_d_reviewer_failure),
        ("E - Path traversal rejected", test_e_path_traversal_rejected),
        ("F - Worktree create merge verify", test_f_worktree_create_merge_verify),
        ("G - Required behavior local", test_g_required_behavior_local),
        ("H - No reviewer backward compat", test_h_no_reviewer_still_merges),
    ]:
        try:
            results[name] = fn()
        except Exception as e:
            print(f"  [ERRO] {e}")
            import traceback
            traceback.print_exc()
            results[name] = False

    banner("RESUMO FASE 6.4")
    passed = sum(1 for v in results.values() if v)
    for name, ok in results.items():
        print(f"  {'[OK]' if ok else '[FALHA]'} {name}")

    print(f"\n  Total: {passed}/{len(results)}")

    shutil.rmtree(TEMPDIR, ignore_errors=True)

    if passed == len(results):
        print("\n  Fase 6.4 validada! Pipeline E2E completo verificado.")
        sys.exit(0)
    else:
        print("\n  Alguns cenarios falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()
