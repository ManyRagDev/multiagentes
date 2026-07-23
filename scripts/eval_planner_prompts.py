"""
Avaliação da Fase 5.2 — Planner com decision tree + required_behavior
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas.contract import TaskContract
from src.routing.task_classifier import TaskClassifier, TaskTier


def banner(title: str):
    print(f"\n{'='*70}")
    print(f"  {title}")
    print('='*70)


# ─────────────────────────────────────────────────────────────
# TESTE 1: Schema TaskContract com required_behavior
# ─────────────────────────────────────────────────────────────
def test_contract_schema() -> bool:
    banner("TESTE 1: Schema TaskContract (required_behavior)")

    cases = [
        {
            "name": "Contrato LOCAL bem preenchido",
            "data": {
                "task_id": "t-001",
                "objective": "Adicionar função soma_pares",
                "tier": "local",
                "allowed_files": ["src/math.py"],
                "constraints": ["Não alterar interface pública"],
                "acceptance_criteria": ["soma_pares([1,2,3,4]) == 6"],
                "validation_commands": ["lint", "test"],
                "required_behavior": {
                    "parameters": {"lista": {"type": "list[int]"}},
                    "returns": "int",
                    "edge_cases": {"empty_list": 0}
                },
                "max_files_changed": 1,
                "risk": "low"
            },
            "should_pass": True,
        },
        {
            "name": "required_behavior opcional (tier=medium)",
            "data": {
                "task_id": "t-002",
                "objective": "Refatorar service de autenticação",
                "tier": "medium",
                "allowed_files": ["src/auth/service.py"],
                "risk": "medium"
            },
            "should_pass": True,
        },
        {
            "name": "Rejeita campos desconhecidos (extra=forbid)",
            "data": {
                "task_id": "t-003",
                "objective": "Algo",
                "campo_inventado": "não deveria existir"
            },
            "should_pass": False,
        },
    ]

    passed = 0
    for c in cases:
        try:
            contract = TaskContract(**c["data"])
            ok = c["should_pass"]
            if ok:
                has_rb = contract.required_behavior is not None
                print(f"  ✅ {c['name']}")
                print(f"     tier={contract.tier} | required_behavior={'presente' if has_rb else 'ausente'}")
                passed += 1
            else:
                print(f"  ❌ {c['name']} (deveria ter rejeitado)")
        except Exception as e:
            if not c["should_pass"]:
                print(f"  ✅ {c['name']} (rejeitou corretamente: {type(e).__name__})")
                passed += 1
            else:
                print(f"  ❌ {c['name']} (falhou inesperado: {e})")

    print(f"\nResultado Schema: {passed}/{len(cases)}")
    return passed == len(cases)


# ─────────────────────────────────────────────────────────────
# TESTE 2: Coerência Planner↔Classifier (decision tree)
# ─────────────────────────────────────────────────────────────
def test_planner_classifier_coherence() -> bool:
    banner("TESTE 2: Coerência entre Planner (tier) e Classifier (risk)")

    classifier = TaskClassifier()

    # Casos onde planner e classifier devem concordar
    coherence_cases = [
        {
            "description": "Adicionar validação de email no signup",
            "objective": "Adicionar validação de email no formulário de signup usando Zod",
            "expected_tier_by_classifier": TaskTier.LOCAL,
            "files": ["src/components/SignupForm.tsx"],
        },
        {
            "description": "Implementar refresh token JWT",
            "objective": "Implementar refresh token JWT no sistema de autenticação",
            "expected_tier_by_classifier": TaskTier.STRONG,
            "files": ["src/auth/tokens.ts"],
        },
        {
            "description": "Refatoração multi-arquivo",
            "objective": "Refatorar 5 arquivos do módulo de produtos para usar o novo padrão",
            "expected_tier_by_classifier": TaskTier.MEDIUM,
            "files": [f"src/products/{i}.ts" for i in range(5)],
        },
    ]

    passed = 0
    for c in coherence_cases:
        classification = classifier.classify(
            objective=c["objective"],
            files=c["files"],
            constraints=[]
        )
        match = classification.tier == c["expected_tier_by_classifier"]
        icon = "✅" if match else "❌"
        print(f"  {icon} {c['description']}")
        print(f"     classifier→{classification.tier.value} | esperado→{c['expected_tier_by_classifier'].value}")
        print(f"     risk={classification.risk_score} | complexity={classification.complexity_score}")
        if match:
            passed += 1

    print(f"\nResultado Coerência: {passed}/{len(coherence_cases)}")
    return passed == len(coherence_cases)


# ─────────────────────────────────────────────────────────────
# TESTE 3: Prompt do Planner (princípios carregados)
# ─────────────────────────────────────────────────────────────
def test_planner_prompt() -> bool:
    banner("TESTE 3: System Prompt do Planner (princípios + decision tree)")

    prompt_path = Path("src/prompts/planning/planner.prompty")
    if not prompt_path.exists():
        print(f"  ❌ Arquivo não encontrado: {prompt_path}")
        return False

    content = prompt_path.read_text(encoding="utf-8")

    checks = [
        ("P3 - Decision Tree", "Decision Tree" in content or "tier =" in content),
        ("P5 - Contexto Enxuto", "Contexto Enxuto" in content or "context_snippets" in content),
        ("O3 - Especificidade Inversa", "Especificidade Inversa" in content or "required_behavior" in content),
        ("Fragmento compartilhado", "_shared/principles" in content),
        ("Exemplo BOM", "Exemplo BOM" in content or "BOM" in content),
        ("Anti-padrão", "Anti-padrão" in content or "anti-padrão" in content.lower()),
        ("Formato JSON puro", "APENAS" in content and "JSON" in content),
        ("Needs clarification escape hatch", "needs_clarification" in content),
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


# ─────────────────────────────────────────────────────────────
def main():
    print("🚀" * 30)
    print("  AVALIAÇÃO FASE 5.2 — Planner + required_behavior")
    print("🚀" * 30)

    results = {
        "schema": test_contract_schema(),
        "coherence": test_planner_classifier_coherence(),
        "prompt": test_planner_prompt(),
    }

    banner("RESUMO FINAL")
    for k, v in results.items():
        print(f"  {'✅' if v else '❌'} {k}")

    total = sum(results.values())
    print(f"\nTotal: {total}/{len(results)}")

    if total == len(results):
        print("\n🎉 Fase 5.2 implementada e validada com sucesso!")
    else:
        print("\n⚠️  Alguns checks falharam. Verifique acima.")


if __name__ == "__main__":
    main()
