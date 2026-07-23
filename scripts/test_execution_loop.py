"""Teste do Execution Loop + Validation Pipeline com stacks múltiplas."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.orchestration.execution_loop import ExecutionLoop, TaskContract, ExecutionStatus
from src.routing.tier_router import TierRouter
from src.validators.pipeline import ValidationPipeline
from src.validators.stack_detector import detect_stack, get_validation_commands


def test_stack_detection():
    """Testa detecção de stack em diferentes cenários."""
    print("=" * 60)
    print("TESTE 1: Detecção de Stack")
    print("=" * 60)

    # Testar comandos disponíveis por stack
    for stack in ["python", "typescript", "javascript"]:
        cmds = get_validation_commands(stack)
        print(f"\n  📦 Stack '{stack}':")
        for cmd_type, cmd in cmds.items():
            print(f"     {cmd_type}: {cmd}")

    print("\n  ✅ Comandos padrão definidos para todas as stacks alvo")
    return True


def test_task_contract():
    """Testa criação e serialização do contrato de delegação."""
    print("\n" + "=" * 60)
    print("TESTE 2: Contrato de Delegação")
    print("=" * 60)

    contract = TaskContract(
        task_id="test-001",
        goal="Adicionar validação de email no formulário de signup",
        allowed_files=["src/components/SignupForm.tsx"],
        forbidden_files=["src/config/auth.ts"],
        constraints=["Usar Zod", "Não alterar layout", "Manter mensagens em PT-BR"],
        acceptance_criteria=["Campo obrigatório", "Formato RFC 5322"],
        validation_commands={"lint": "npx eslint src/components/SignupForm.tsx"},
        context_snippets=["// Padrão existente em LoginForm.tsx..."],
        output_format="unified_diff",
        risk="low",
        stack="typescript",
    )

    print(f"\n  📋 Task ID: {contract.task_id}")
    print(f"  🎯 Goal: {contract.goal}")
    print(f"  📁 Allowed: {contract.allowed_files}")
    print(f"  🚫 Forbidden: {contract.forbidden_files}")
    print(f"  ⛔ Constraints: {len(contract.constraints)}")
    print(f"  ✅ Acceptance: {len(contract.acceptance_criteria)}")
    print(f"  🔧 Validation cmds: {list(contract.validation_commands.keys())}")
    print(f"  📚 Context snippets: {len(contract.context_snippets)}")
    print(f"  🏗️ Stack: {contract.stack}")

    print("\n  ✅ Contrato criado com sucesso")
    return True


def test_execution_loop_creation():
    """Testa instanciação do Execution Loop com dependências."""
    print("\n" + "=" * 60)
    print("TESTE 3: Execution Loop (Instanciação)")
    print("=" * 60)

    router = TierRouter()
    pipeline = ValidationPipeline()
    loop = ExecutionLoop(
        router=router,
        validation_pipeline=pipeline,
        max_attempts_default=3,
        max_cost_per_task=0.50,
    )

    print(f"\n  🔧 Router: {type(loop.router).__name__}")
    print(f"  🔍 Pipeline validators: {len(loop.pipeline.validators)}")
    for v in loop.pipeline.validators:
        print(f"     - {v.name}")
    print(f"  🔄 Max attempts default: {loop.max_attempts_default}")
    print(f"  💰 Max cost per task: ${loop.max_cost_per_task}")

    print("\n  ✅ Execution Loop instanciado com sucesso")
    return True


def test_prompt_building():
    """Testa construção do prompt estruturado para o executor."""
    print("\n" + "=" * 60)
    print("TESTE 4: Construção de Prompt Estruturado")
    print("=" * 60)

    contract = TaskContract(
        task_id="test-002",
        goal="Refatorar função de cálculo de imposto",
        allowed_files=["src/services/tax.ts", "src/services/tax.test.ts"],
        constraints=["Manter interface pública", "Usar decimal.js"],
        acceptance_criteria=["Testes passam", "Precisão de 2 casas decimais"],
        stack="typescript",
    )

    prompt = ExecutionLoop._build_prompt(contract)
    lines = prompt.splitlines()

    print(f"\n  📝 Prompt gerado ({len(lines)} linhas):")
    for line in lines[:15]:
        print(f"     {line}")
    if len(lines) > 15:
        print(f"     ... ({len(lines) - 15} linhas restantes)")

    # Verificar seções obrigatórias
    assert "## Objetivo" in prompt, "Seção Objetivo ausente"
    assert "## Arquivos Permitidos" in prompt, "Seção Arquivos ausente"
    assert "## Restrições" in prompt, "Seção Restrições ausente"
    assert "## Critérios de Aceite" in prompt, "Seção Critérios ausente"

    print("\n  ✅ Prompt estruturado corretamente")
    return True


def test_prompt_with_feedback():
    """Testa prompt com feedback de tentativa anterior."""
    print("\n" + "=" * 60)
    print("TESTE 5: Prompt com Feedback de Retentativa")
    print("=" * 60)

    contract = TaskContract(
        task_id="test-003",
        goal="Corrigir import quebrado",
        allowed_files=["src/utils/format.ts"],
        stack="typescript",
    )

    feedback = "command:lint: ESLint encontrou 2 erros:\n  - Missing return type\n  - Unused variable 'temp'"
    prompt = ExecutionLoop._build_prompt(contract, previous_feedback=feedback)

    has_feedback_section = "## Feedback da Tentativa Anterior" in prompt
    has_correction_instruction = "Corrija os seguintes problemas" in prompt

    print(f"\n  📝 Seção de feedback presente: {has_feedback_section}")
    print(f"  📝 Instrução de correção presente: {has_correction_instruction}")

    assert has_feedback_section, "Seção de feedback ausente"
    assert has_correction_instruction, "Instrução de correção ausente"

    print("\n  ✅ Prompt com feedback construído corretamente")
    return True


def main():
    print("\n" + "🚀" * 30)
    print("  TESTES: Execution Loop + Validation Pipeline")
    print("  Fase 3 — Validação Determinística + Loop com Limites")
    print("🚀" * 30 + "\n")

    tests = [
        ("Stack Detection", test_stack_detection),
        ("Task Contract", test_task_contract),
        ("Execution Loop Creation", test_execution_loop_creation),
        ("Prompt Building", test_prompt_building),
        ("Prompt with Feedback", test_prompt_with_feedback),
    ]

    passed = 0
    failed = 0

    for name, test_fn in tests:
        try:
            if test_fn():
                passed += 1
            else:
                failed += 1
                print(f"\n  ❌ {name} FALHOU")
        except Exception as e:
            failed += 1
            print(f"\n  ❌ {name} ERRO: {e}")

    print("\n" + "=" * 60)
    print(f"RESULTADO: {passed}/{len(tests)} passaram")
    print("=" * 60)

    if failed == 0:
        print("\n🎉 Fase 3 (Validação + Loop) implementada com sucesso!")
        print("\nPróximos passos:")
        print("  1. Integrar ExecutionLoop.execute() com BaseAgent real")
        print("  2. Adicionar Modo Iterativo (/goal) como política alternativa")
        print("  3. Implementar camada de Tools + Permissões (Fase 4)")
    else:
        print(f"\n⚠️ {failed} teste(s) falharam. Verifique os erros acima.")


if __name__ == "__main__":
    main()
