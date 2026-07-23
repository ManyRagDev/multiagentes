"""End-to-End Test: ExecutionLoop + ExecutorAgent + TierRouter (real LLM call).

Este script valida a integração completa do fluxo:
  TaskContract → TierRouter → ExecutorAgent (Qwen local real) → ValidationPipeline → Result

Requisitos:
  - llama-server rodando em http://127.0.0.1:8080
  - uv run python scripts/test_e2e.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.agents.executor.agent import ExecutorAgent
from src.orchestration.execution_loop import ExecutionLoop, TaskContract, ExecutionStatus
from src.routing.tier_router import TierRouter
from src.validators.pipeline import ValidationPipeline


def separator(title: str):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}\n")


def test_executor_agent_direct():
    """Teste 1: ExecutorAgent chamando Qwen local diretamente."""
    separator("TESTE 1: ExecutorAgent → Qwen Local (chamada direta)")

    agent = ExecutorAgent(provider_name="local-qwen", temperature=0.3)

    prompt = (
        "## Objetivo\n"
        "Criar uma função Python chamada `is_palindrome` que verifica se uma string é palíndromo.\n\n"
        "## Restrições\n"
        "- Ignorar maiúsculas/minúsculas e espaços\n"
        "- Incluir type hints\n"
        "- Incluir docstring\n\n"
        "## Formato de Saída\n"
        "Apenas o código Python, sem explicações."
    )

    print(f"📤 Enviando prompt ({len(prompt)} chars)...")
    result = agent.execute_raw(prompt)

    if result.success:
        print(f"✅ Sucesso!")
        print(f"   Provider: {result.provider}/{result.model}")
        print(f"   Tokens: {result.tokens_used}")
        print(f"   Custo: ${result.cost:.4f}")
        print(f"   Output ({len(result.output)} chars):")
        print(f"   ---")
        for line in result.output.strip().split("\n")[:20]:
            print(f"   {line}")
        print(f"   ---")
    else:
        print(f"❌ Falhou: {result.error}")

    return result.success


def test_execution_loop_e2e():
    """Teste 2: ExecutionLoop completo com tarefa simples (sem validação de comandos)."""
    separator("TESTE 2: ExecutionLoop End-to-End (tarefa LOCAL)")

    # Router + Pipeline sem command validators (não temos projeto alvo aqui)
    router = TierRouter()
    pipeline = ValidationPipeline(validators=[])  # Sem validadores para este teste
    loop = ExecutionLoop(router=router, validation_pipeline=pipeline)

    contract = TaskContract(
        task_id="e2e-test-001",
        goal="Criar uma função Python chamada `calculate_bmi(weight_kg, height_m)` que calcula o IMC e retorna um dict com 'bmi' (float) e 'category' (str: underweight/normal/overweight/obese). Incluir type hints e docstring.",
        allowed_files=["health/bmi.py"],
        constraints=[
            "Usar fórmula padrão: peso / altura²",
            "Categorias: <18.5 underweight, 18.5-24.9 normal, 25-29.9 overweight, >=30 obese",
        ],
        acceptance_criteria=[
            "Função recebe dois floats e retorna dict",
            "Type hints presentes",
        ],
        output_format="full_file",
        risk="low",
        max_attempts=2,
        stack="python",
    )

    print(f"🎯 Tarefa: {contract.goal[:80]}...")
    print(f"   Risk: {contract.risk} | Max attempts: {contract.max_attempts}")
    print()

    result = loop.execute(contract)

    print(f"\n📊 Resultado:")
    print(f"   Status: {result.status.value}")
    print(f"   Tentativas: {result.attempts_used}")
    print(f"   Tokens totais: {result.total_tokens}")
    print(f"   Custo total: ${result.total_cost:.4f}")
    print(f"   Duração: {result.duration_ms:.0f}ms")

    if result.history:
        print(f"\n📜 Histórico ({len(result.history)} passos):")
        for step in result.history:
            print(f"   • {step}")

    if result.output:
        print(f"\n📦 Output ({len(result.output)} chars):")
        print("   ---")
        for line in result.output.strip().split("\n")[:25]:
            print(f"   {line}")
        if len(result.output.strip().split("\n")) > 25:
            print(f"   ... ({len(result.output.strip().split(chr(10)))} linhas total)")
        print("   ---")

    success = result.status in (ExecutionStatus.PASSED, ExecutionStatus.EXECUTING)
    return success


def test_execution_loop_medium():
    """Teste 3: Tarefa de complexidade média (deve rotear para MEDIUM ou LOCAL)."""
    separator("TESTE 3: ExecutionLoop — Tarefa Média (endpoint + paginação)")

    router = TierRouter()
    pipeline = ValidationPipeline(validators=[])
    # Executor com timeout de 60s para evitar travamento infinito
    executor = ExecutorAgent(provider_name="local-qwen", temperature=0.3, timeout=60.0)
    loop = ExecutionLoop(router=router, validation_pipeline=pipeline, executor=executor)

    contract = TaskContract(
        task_id="e2e-test-002",
        goal="Adicionar endpoint GET /products com paginação usando query params page e limit. Retornar JSON com items, page, limit, total e totalPages.",
        allowed_files=[
            "src/routes/products.ts",
            "src/services/product-service.ts",
            "src/types/product.ts",
        ],
        constraints=[
            "Seguir padrão existente de src/routes/orders.ts",
            "Não alterar interface Product",
            "Validar page >= 1 e limit entre 1-100",
        ],
        acceptance_criteria=[
            "Endpoint responde com paginação correta",
            "Parâmetros inválidos retornam erro 400",
        ],
        output_format="unified_diff",
        risk="medium",
        max_attempts=2,
        stack="typescript",
        command_timeout=30,
    )

    print(f"🎯 Tarefa: {contract.goal[:80]}...")
    print(f"   Risk: {contract.risk} | Files: {len(contract.allowed_files)}")
    print()

    result = loop.execute(contract)

    print(f"\n📊 Resultado:")
    print(f"   Status: {result.status.value}")
    print(f"   Tentativas: {result.attempts_used}")
    print(f"   Tokens totais: {result.total_tokens}")
    print(f"   Custo total: ${result.total_cost:.4f}")
    print(f"   Duração: {result.duration_ms:.0f}ms")

    # Mostrar qual provider foi usado
    route_steps = [s for s in result.history if s.get("step") == "route"]
    if route_steps:
        print(f"   Provider roteado: {route_steps[0].get('provider')} (tier={route_steps[0].get('tier')})")

    if result.output:
        lines = result.output.strip().split("\n")
        print(f"\n📦 Output ({len(lines)} linhas, {len(result.output)} chars):")
        print("   ---")
        for line in lines[:20]:
            print(f"   {line}")
        if len(lines) > 20:
            print(f"   ... ({len(lines)} linhas total)")
        print("   ---")

    return result.status != ExecutionStatus.ERROR


def main():
    print("🚀" * 35)
    print("  INTEGRAÇÃO END-TO-END: ExecutionLoop + ExecutorAgent + TierRouter")
    print("  Fase 3 → Integração Real com Qwen Local")
    print("🚀" * 35)

    results = {}

    # Teste 1: Executor direto
    try:
        results["executor_direct"] = test_executor_agent_direct()
    except Exception as e:
        print(f"\n❌ Teste 1 exceção: {e}")
        results["executor_direct"] = False

    # Teste 2: Loop E2E simples
    try:
        results["loop_simple"] = test_execution_loop_e2e()
    except Exception as e:
        print(f"\n❌ Teste 2 exceção: {e}")
        results["loop_simple"] = False

    # Teste 3: Loop E2E médio
    try:
        results["loop_medium"] = test_execution_loop_medium()
    except Exception as e:
        print(f"\n❌ Teste 3 exceção: {e}")
        results["loop_medium"] = False

    # Resumo
    separator("RESUMO FINAL")
    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, ok in results.items():
        icon = "✅" if ok else "❌"
        print(f"  {icon} {name}")

    print(f"\n  Total: {passed}/{total} passaram")

    if passed == total:
        print("\n🎉 Integração end-to-end validada com sucesso!")
    else:
        print("\n⚠️ Alguns testes falharam. Verifique os logs acima.")


if __name__ == "__main__":
    main()
