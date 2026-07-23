"""
Avaliação da Fase 5.3 — Reviewer com provenance (P6) + anti-sycophancy (P7).

Testa:
1. Schema ReviewVerdict (kind deterministic|opinion, approval_evidence,
   properties has_blocking_issues / is_suspicious_approval).
2. Prompt reviewer.prompty (presença dos princípios P6, P7, exemplos,
   decision tree e formato de saída).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas.verdict import ReviewVerdict, ReviewIssue


def banner(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


# ─────────────────────────────────────────────────────────────
# TESTE 1: Schema ReviewVerdict com provenance
# ─────────────────────────────────────────────────────────────
def test_verdict_schema() -> bool:
    banner("TESTE 1: Schema ReviewVerdict (kind deterministic|opinion)")

    cases = [
        {
            "name": "Verdict aprovado com evidência",
            "data": {
                "status": "approved",
                "confidence": 0.92,
                "summary": "Código atende a todos os critérios.",
                "issues": [],
                "approval_evidence": ["pytest: 5 passed", "lint: 0 violations"],
            },
            "checks": lambda v: (
                v.status == "approved"
                and not v.has_blocking_issues
                and not v.is_suspicious_approval
            ),
        },
        {
            "name": "Aprovação suspeita (sem evidência)",
            "data": {
                "status": "approved",
                "confidence": 0.95,
                "summary": "Ótimo código!",
                "issues": [],
                "approval_evidence": None,
            },
            "checks": lambda v: v.is_suspicious_approval,
        },
        {
            "name": "Rejeição com issues deterministic + opinion",
            "data": {
                "status": "changes_required",
                "confidence": 0.88,
                "summary": "Falha em teste e sugestão de refactor.",
                "issues": [
                    {
                        "kind": "deterministic",
                        "severity": "high",
                        "file": "src/math.py",
                        "title": "Teste falhou",
                        "description": "pytest::test_sum falhou",
                        "evidence": "exit code 1",
                    },
                    {
                        "kind": "opinion",
                        "severity": "low",
                        "title": "Nome de variável",
                        "description": "x poderia ser total_sum",
                    },
                ],
            },
            "checks": lambda v: (
                v.has_blocking_issues
                and len(v.deterministic_issues) == 1
                and len(v.opinion_issues) == 1
            ),
        },
        {
            "name": "Rejeita kind inválido",
            "data": {
                "status": "changes_required",
                "confidence": 0.8,
                "summary": "Problema",
                "issues": [
                    {
                        "kind": "feeling",  # inválido
                        "severity": "medium",
                        "title": "Algo",
                        "description": "algo",
                    }
                ],
            },
            "should_fail": True,
        },
    ]

    passed = 0
    for c in cases:
        try:
            v = ReviewVerdict(**c["data"])
            if c.get("should_fail"):
                print(f"  ❌ {c['name']} (deveria ter rejeitado)")
            elif c["checks"](v):
                print(f"  ✅ {c['name']}")
                passed += 1
            else:
                print(f"  ❌ {c['name']} (check falhou)")
        except Exception as e:
            if c.get("should_fail"):
                print(f"  ✅ {c['name']} (rejeitou: {type(e).__name__})")
                passed += 1
            else:
                print(f"  ❌ {c['name']} ({type(e).__name__}: {e})")

    print(f"\nResultado Schema: {passed}/{len(cases)}")
    return passed == len(cases)


# ─────────────────────────────────────────────────────────────
# TESTE 2: Prompt do Reviewer (princípios)
# ─────────────────────────────────────────────────────────────
def test_reviewer_prompt() -> bool:
    banner("TESTE 2: Prompt do Reviewer (P6 + P7)")

    prompt_path = Path("src/prompts/verify/reviewer.prompty")
    if not prompt_path.exists():
        print(f"  ❌ Arquivo não encontrado: {prompt_path}")
        return False

    content = prompt_path.read_text(encoding="utf-8")

    checks = [
        ("P6 - Provenance", "Provenance" in content or "deterministic" in content),
        ("P7 - Anti-Sycophancy", "Anti-Sycophancy" in content),
        ("Classificação deterministic", "deterministic" in content),
        ("Classificação opinion", "opinion" in content),
        ("Fragmento compartilhado", "_shared/principles" in content),
        ("Exemplo BOM (rejeição)", "Exemplo BOM" in content),
        ("Anti-padrão (aprovação suspeita)", "Anti-padrão" in content),
        ("approval_evidence no schema", "approval_evidence" in content),
        ("ReviewVerdict JSON output", "ReviewVerdict" in content and "JSON" in content),
        ("Decision tree", "Decision tree" in content),
    ]

    passed = 0
    for name, cond in checks:
        icon = "✅" if cond else "❌"
        print(f"  {icon} {name}")
        if cond:
            passed += 1

    print(f"\nPrompt total: {len(content)} chars (~{len(content)//4} tokens)")
    print(f"Resultado Prompt: {passed}/{len(checks)}")
    return passed == len(checks)


def main():
    print("🚀" * 30)
    print("  AVALIAÇÃO FASE 5.3 — Reviewer + Provenance + Anti-Sycophancy")
    print("🚀" * 30)

    results = {
        "schema": test_verdict_schema(),
        "prompt": test_reviewer_prompt(),
    }

    banner("RESUMO FINAL")
    for k, v in results.items():
        print(f"  {'✅' if v else '❌'} {k}")

    total = sum(results.values())
    print(f"\nTotal: {total}/{len(results)}")

    if total == len(results):
        print("\n🎉 Fase 5.3 validada!")
    else:
        print("\n⚠️ Alguns checks falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()
