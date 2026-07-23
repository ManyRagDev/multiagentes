"""
Avaliação da Fase 5.4 — Enforcement Engine (P1 + P6 + P7).

Testa o EnforcementEngine.evaluate() com ReviewVerdict e um TaskContract,
cobrindo os 7 cenários críticos:
- P7: aprovação sem evidência → retry (suspeita)
- P7: aprovação COM evidência → continue
- P6: issue deterministic → retry
- P6: só opinion issues → approve_with_warnings
- P1: constraint violada (install) → reject
- P1: arquivo proibido alterado → reject
- Revisor escalou → escalate

Também testa check_output() (modo leve usado pelo ExecutionLoop).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas.contract import TaskContract
from src.schemas.verdict import ReviewVerdict, ReviewIssue
from src.orchestration.enforcement import EnforcementEngine


def banner(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


def _base_contract() -> TaskContract:
    return TaskContract(
        task_id="t-001",
        objective="Adicionar função soma",
        tier="local",
        allowed_files=["src/math.py"],
        forbidden_files=["src/auth.py"],
        constraints=["Não instalar dependências", "Manter interface pública"],
        acceptance_criteria=["soma(1,2) == 3"],
    )


def test_enforcement_evaluate() -> bool:
    banner("TESTE 1: EnforcementEngine.evaluate() (P1 + P6 + P7)")

    engine = EnforcementEngine()
    contract = _base_contract()
    clean_output = "def soma(a, b): return a + b"

    cases = [
        {
            "name": "P7: Aprovação sem evidência → retry (suspeita)",
            "verdict": ReviewVerdict(
                status="approved",
                confidence=0.9,
                summary="Bom código!",
                issues=[],
                approval_evidence=None,
            ),
            "output": clean_output,
            "expected": "retry",
        },
        {
            "name": "P7: Aprovação COM evidência → continue",
            "verdict": ReviewVerdict(
                status="approved",
                confidence=0.9,
                summary="Código aprovado.",
                issues=[],
                approval_evidence=["pytest: 1 passed", "lint: 0"],
            ),
            "output": clean_output,
            "expected": "continue",
        },
        {
            "name": "P6: Issue deterministic → retry",
            "verdict": ReviewVerdict(
                status="changes_required",
                confidence=0.85,
                summary="Teste falhou.",
                issues=[
                    ReviewIssue(
                        kind="deterministic",
                        severity="high",
                        title="Teste falhou",
                        description="pytest falhou",
                        evidence="exit 1",
                    )
                ],
                approval_evidence=None,
            ),
            "output": clean_output,
            "expected": "retry",
        },
        {
            "name": "P6: Só opinion issues → approve_with_warnings",
            "verdict": ReviewVerdict(
                status="approved",
                confidence=0.88,
                summary="Funciona, mas poderia ser mais claro.",
                issues=[
                    ReviewIssue(
                        kind="opinion",
                        severity="low",
                        title="Nome de variável",
                        description="Poderia ser mais descritivo",
                    )
                ],
                approval_evidence=["pytest: 1 passed"],
            ),
            "output": clean_output,
            "expected": "approve_with_warnings",
        },
        {
            "name": "P1: Constraint violada (install) → reject",
            "verdict": ReviewVerdict(
                status="approved",
                confidence=0.9,
                summary="OK",
                issues=[],
                approval_evidence=["pytest: 1 passed"],
            ),
            "output": "# pip install numpy\ndef soma(a, b): return a + b",
            "expected": "reject",
        },
        {
            "name": "P1: Arquivo proibido alterado → reject",
            "verdict": ReviewVerdict(
                status="approved",
                confidence=0.9,
                summary="OK",
                issues=[],
                approval_evidence=["pytest: 1 passed"],
            ),
            "output": "--- a/src/auth.py\n+++ b/src/auth.py\n@@\n+changed",
            "expected": "reject",
        },
        {
            "name": "Revisor escalou → escalate",
            "verdict": ReviewVerdict(
                status="escalated",
                confidence=0.5,
                summary="Não tenho contexto suficiente.",
                issues=[],
            ),
            "output": clean_output,
            "expected": "escalate",
        },
    ]

    passed = 0
    for c in cases:
        result = engine.evaluate(
            contract=contract,
            verdict=c["verdict"],
            executor_output=c["output"],
        )
        ok = result.action == c["expected"]
        icon = "✅" if ok else "❌"
        print(f"  {icon} {c['name']}")
        print(f"     esperado={c['expected']} | obtido={result.action}")
        print(f"     reason: {result.reason[:80]}")
        if ok:
            passed += 1

    print(f"\nResultado evaluate(): {passed}/{len(cases)}")
    return passed == len(cases)


def test_enforcement_check_output() -> bool:
    banner("TESTE 2: EnforcementEngine.check_output() (modo leve P1)")

    engine = EnforcementEngine()
    contract = _base_contract()

    cases = [
        {
            "name": "Output limpo → continue",
            "output": "def soma(a, b): return a + b",
            "expected": "continue",
        },
        {
            "name": "Output com pip install → reject",
            "output": "# pip install requests\ndef soma(a, b): return a + b",
            "expected": "reject",
        },
        {
            "name": "Output tocando arquivo proibido → reject",
            "output": "diff --git a/src/auth.py b/src/auth.py\n+++ b/src/auth.py\n+x",
            "expected": "reject",
        },
        {
            "name": "Output None → continue",
            "output": None,
            "expected": "continue",
        },
    ]

    passed = 0
    for c in cases:
        result = engine.check_output(contract, c["output"])
        ok = result.action == c["expected"]
        icon = "✅" if ok else "❌"
        print(f"  {icon} {c['name']}")
        print(f"     esperado={c['expected']} | obtido={result.action}")
        if ok:
            passed += 1

    print(f"\nResultado check_output(): {passed}/{len(cases)}")
    return passed == len(cases)


def main():
    print("🚀" * 30)
    print("  AVALIAÇÃO FASE 5.4 — Enforcement (P1 + P6 + P7)")
    print("🚀" * 30)

    results = {
        "evaluate": test_enforcement_evaluate(),
        "check_output": test_enforcement_check_output(),
    }

    banner("RESULTADO")
    for k, v in results.items():
        print(f"  {'✅' if v else '❌'} {k}")

    if all(results.values()):
        print("\n🎉 Fase 5.4 validada!")
    else:
        print("\n⚠️ Alguns checks falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()
