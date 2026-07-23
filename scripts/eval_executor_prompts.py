"""Avaliação da Fase 5.0 + 5.1: Fragmento compartilhado + Executor reformulado.

Testa:
1. Parser extract_payload() com cenários sintéticos (self-check, fences, anti-padrão)
2. System prompt carregado (verifica se princípios P1/P4/O2 + P2/O1 estão presentes)
3. [Opcional] Chamada real ao Qwen local para medir economia de tokens
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.executor.agent import ExecutorAgent


# ============================================================================
# TESTE 1: Parser extract_payload() com cenários sintéticos
# ============================================================================

def test_parser():
    print("=" * 70)
    print("TESTE 1: Parser extract_payload() - Cenários Sintéticos")
    print("=" * 70)

    scenarios = [
        {
            "name": "Código limpo sem self_check (ideal)",
            "input": """```python
def is_even(n: int) -> bool:
    return n % 2 == 0
```""",
            "expect_needs_context": False,
            "expect_has_code": True,
            "expect_has_self_check": False,
        },
        {
            "name": "Self_check com needs_context (sinalização correta)",
            "input": """<self_check>
- goal_ambiguo: true
- constraints_honradas: false
- arquivos_suficientes: false
- decision: needs_context
- motivo: Novo gateway não definido; allowed_files insuficientes.
</self_check>""",
            "expect_needs_context": True,
            "expect_has_code": False,
            "expect_has_self_check": True,
        },
        {
            "name": "Self_check + código (incerteza parcial, mas emite)",
            "input": """<self_check>
- goal_ambiguo: false
- constraints_honradas: true
- arquivos_suficientes: true
- decision: emitir_codigo
</self_check>

```python
def calculate_discount(price: float, pct: float) -> float:
    return price * (1 - pct / 100)
```""",
            "expect_needs_context": False,
            "expect_has_code": True,
            "expect_has_self_check": True,
        },
        {
            "name": "Anti-padrão com preâmbulo (parser deve limpar)",
            "input": """Claro! Vou fazer essa alteração pra você. Aqui está:

```python
def add(a: int, b: int) -> int:
    return a + b
```

Espero que ajude! Qualquer coisa me chame.""",
            "expect_needs_context": False,
            "expect_has_code": True,
            "expect_has_self_check": False,
            "expect_code_is_clean": True,  # Só a função, sem preâmbulo
        },
        {
            "name": "Múltiplos arquivos (diffs concatenados)",
            "input": """```diff
--- a/src/a.py
+++ b/src/a.py
@@ -1 +1 @@
-old
+new
```

```diff
--- a/src/b.py
+++ b/src/b.py
@@ -1 +1 @@
-x
+y
```""",
            "expect_needs_context": False,
            "expect_has_code": True,
            "expect_has_self_check": False,
            "expect_multi_file": True,
        },
    ]

    passed = 0
    total = len(scenarios)

    for s in scenarios:
        code, self_check, needs_context = ExecutorAgent.extract_payload(s["input"])

        ok = True
        reasons = []

        if needs_context != s["expect_needs_context"]:
            ok = False
            reasons.append(
                f"needs_context esperado={s['expect_needs_context']}, "
                f"obtido={needs_context}"
            )

        if s["expect_has_code"] and not code.strip():
            ok = False
            reasons.append("esperava código mas veio vazio")

        if not s["expect_has_code"] and code.strip():
            ok = False
            reasons.append(f"não esperava código mas veio: {code[:60]}...")

        if s["expect_has_self_check"] and self_check is None:
            ok = False
            reasons.append("esperava self_check mas veio None")

        if not s["expect_has_self_check"] and self_check is not None:
            ok = False
            reasons.append(f"não esperava self_check mas veio: {self_check[:60]}...")

        if s.get("expect_code_is_clean"):
            if "Claro!" in code or "Espero que ajude" in code:
                ok = False
                reasons.append("parser não limpou o preâmbulo")

        if s.get("expect_multi_file"):
            if code.count("--- a/") != 2:
                ok = False
                reasons.append(f"esperava 2 diffs, obteve {code.count('--- a/')}")

        status = "✅" if ok else "❌"
        print(f"\n{status} {s['name']}")
        print(f"   code: {len(code)} chars | self_check: {'presente' if self_check else 'ausente'} | needs_context: {needs_context}")
        if not ok:
            for r in reasons:
                print(f"   ⚠️  {r}")

        if ok:
            passed += 1

    print(f"\nResultado Parser: {passed}/{total}")
    return passed == total


# ============================================================================
# TESTE 2: System prompt carregado (princípios incluídos)
# ============================================================================

def test_system_prompt():
    print("\n" + "=" * 70)
    print("TESTE 2: System Prompt do Executor (princípios carregados)")
    print("=" * 70)

    agent = ExecutorAgent.__new__(ExecutorAgent)  # Não chama __init__
    prompt = ExecutorAgent._default_system_prompt()

    checks = [
        ("P1 - Hierarquia de Autoridade", "Hierarquia de Autoridade" in prompt),
        ("P2 - Auto-auditoria", "Auto-auditoria" in prompt),
        ("P4 - Fail-Safe / Default-Deny", "Fail-Safe" in prompt or "Default-Deny" in prompt),
        ("O1 - Self-Check", "Self-Check" in prompt or "self_check" in prompt),
        ("O2 - Minimalismo", "Minimalismo" in prompt or "minimalismo" in prompt.lower()),
        ("Instrução de parser", "parseado automaticamente" in prompt),
        ("allowed_files mencionado", "allowed_files" in prompt),
    ]

    passed = sum(1 for _, ok in checks if ok)
    total = len(checks)

    for name, ok in checks:
        print(f"   {'✅' if ok else '❌'} {name}")

    print(f"\nPrompt total: {len(prompt)} chars (~{len(prompt) // 4} tokens)")
    print(f"Resultado System Prompt: {passed}/{total}")
    return passed == total


# ============================================================================
# TESTE 3 [OPCIONAL]: Chamada real ao Qwen local para medir economia
# ============================================================================

def test_real_call():
    print("\n" + "=" * 70)
    print("TESTE 3: Chamada Real ao Qwen Local (economia de tokens)")
    print("=" * 70)

    try:
        agent = ExecutorAgent(provider_name="local-qwen", timeout=60.0)
    except Exception as e:
        print(f"⚠️  Pulando (provider indisponível): {e}")
        return True  # Não é falha

    prompt = """## Objetivo
Criar função `calculate_bmi(weight_kg, height_m)` que calcula o IMC e retorna dict.

## Arquivos Permitidos
- src/health/bmi.py

## Restrições
- Usar type hints Python 3.10+
- Retornar dict com chaves: bmi (float), category (str)

## Critérios de Aceite
- BMI < 18.5 → "underweight"
- 18.5 <= BMI < 25 → "normal"
- 25 <= BMI < 30 → "overweight"
- BMI >= 30 → "obese"

## Formato de Saída
full_file"""

    print("📤 Chamando Qwen local com novo prompt...")
    result = agent.execute_raw(prompt)

    if not result.success:
        print(f"❌ Erro: {result.error}")
        return False

    print(f"   ✅ Sucesso")
    print(f"   Tokens: {result.tokens_used}")
    print(f"   Raw → Clean: {result.metadata['raw_output_length']} → {result.metadata['clean_output_length']} chars")
    print(f"   Economia: {result.metadata['raw_output_length'] - result.metadata['clean_output_length']} chars")
    print(f"   Needs context: {result.metadata['needs_context']}")
    print(f"   Self-check: {'presente' if result.metadata['self_check'] else 'ausente'}")
    print(f"\n--- Output Limpo ---\n{result.output[:600]}\n-------------------")

    # Critérios de sucesso: output limpo deve ter código + não ter preâmbulo
    code = result.output
    has_code = "def calculate_bmi" in code
    no_preamble = not any(
        p in code for p in ["Claro", "Aqui está", "Vamos lá", "espero que", "Vou criar"]
    )

    ok = has_code and no_preamble
    print(f"\n   {'✅' if has_code else '❌'} Código presente")
    print(f"   {'✅' if no_preamble else '❌'} Sem preâmbulo conversacional")

    return ok


# ============================================================================
# MAIN
# ============================================================================

def main():
    print("🚀" * 40)
    print("  AVALIAÇÃO FASE 5.0 + 5.1 — Engenharia de Prompt por Princípios")
    print("🚀" * 40 + "\n")

    results = {
        "parser": test_parser(),
        "system_prompt": test_system_prompt(),
        "real_call": test_real_call(),
    }

    print("\n" + "=" * 70)
    print("RESUMO FINAL")
    print("=" * 70)
    for name, ok in results.items():
        print(f"   {'✅' if ok else '❌'} {name}")

    total_ok = sum(1 for ok in results.values() if ok)
    print(f"\nTotal: {total_ok}/{len(results)} componentes validados")

    if total_ok == len(results):
        print("\n🎉 Fase 5.0 + 5.1 implementadas e validadas com sucesso!")
    else:
        print("\n⚠️  Há componentes com falha. Verifique os detalhes acima.")


if __name__ == "__main__":
    main()
