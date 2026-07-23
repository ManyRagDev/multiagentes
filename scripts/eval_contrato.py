"""Teste Fase 6.1: Bridge Plan -> TaskContract.

Valida:
1. PlanContractAgent carrega prompt e schema
2. TaskContract parse (sem API, usando JSON mock)
3. CLI contrato registrada
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from unittest.mock import MagicMock
from src.agents.planning.contract_bridge import PlanContractAgent
from src.schemas.contract import TaskContract


def _mock_client():
    """Cliente mockado para testes que nao precisam de API real."""
    return MagicMock()


def banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def test_agent_loads_prompt():
    """Teste 1: Agent carrega o planner.prompty."""
    banner("TESTE 1: PlanContractAgent carrega prompt")
    agent = PlanContractAgent(client=_mock_client())
    try:
        prompt = agent.load_prompt()
        assert "Decision Tree" in prompt
        assert "required_behavior" in prompt
        assert "needs_clarification" in prompt
        print(f"  [OK] Prompt carregado: {len(prompt)} chars")
        print(f"  [OK] Decision Tree presente")
        print(f"  [OK] required_behavior presente")
        print(f"  [OK] needs_clarification escape hatch presente")
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        return False


def test_schema_parse():
    """Teste 2: TaskContract parse de JSON valido."""
    banner("TESTE 2: Parse TaskContract de JSON")
    agent = PlanContractAgent(client=_mock_client())

    cases = [
        {
            "name": "Contrato LOCAL completo",
            "json_str": json.dumps({
                "task_id": "t-001",
                "objective": "Adicionar validacao de email com Zod no SignupForm",
                "tier": "local",
                "allowed_files": ["src/components/SignupForm.tsx"],
                "constraints": ["Usar Zod schema", "Manter estado existente"],
                "acceptance_criteria": ["Email invalido mostra erro"],
                "required_behavior": {
                    "validation": "email regex + min 5 chars",
                    "error_message": "Formato de email invalido",
                },
                "max_files_changed": 1,
                "risk": "low",
            }),
            "checks": lambda c: (
                c.tier == "local"
                and c.required_behavior is not None
                and c.max_files_changed == 1
            ),
        },
        {
            "name": "Contrato STRONG (auth)",
            "json_str": json.dumps({
                "task_id": "t-002",
                "objective": "Implementar rotacao de JWT secrets",
                "tier": "strong",
                "allowed_files": ["src/auth/secrets.py", "src/config.py"],
                "forbidden_files": ["src/auth/tokens.py"],
                "constraints": ["Nao commitar secrets em plaintext", "Usar KMS"],
                "acceptance_criteria": ["Secrets rotacionam sem downtime"],
                "risk": "high",
            }),
            "checks": lambda c: (
                c.tier == "strong"
                and "src/auth/tokens.py" in c.forbidden_files
            ),
        },
        {
            "name": "Contrato sem required_behavior (tier=medium, opcional)",
            "json_str": json.dumps({
                "task_id": "t-003",
                "objective": "Refatorar 3 arquivos de products",
                "tier": "medium",
                "allowed_files": ["src/products/a.ts", "src/products/b.ts", "src/products/c.ts"],
                "required_behavior": None,
                "risk": "medium",
            }),
            "checks": lambda c: (
                c.tier == "medium"
                and c.required_behavior is None
            ),
        },
    ]

    passed = 0
    for c in cases:
        try:
            contract = agent.parse_output(c["json_str"])
            if c["checks"](contract):
                print(f"  [OK] {c['name']}")
                print(f"       tier={contract.tier} | risk={contract.risk}")
                passed += 1
            else:
                print(f"  [FALHA] {c['name']} (checks falharam)")
        except Exception as e:
            print(f"  [ERRO] {c['name']}: {e}")

    print(f"\n  Parse: {passed}/{len(cases)}")
    return passed == len(cases)


def test_needs_clarification_detection():
    """Teste 3: Deteccao de needs_clarification no output bruto."""
    banner("TESTE 3: needs_clarification detection")
    agent = PlanContractAgent(client=_mock_client())

    clarification_json = json.dumps({
        "status": "needs_clarification",
        "questions": [
            "Qual framework de validacao esta em uso?",
            "Qual o formato atual do SignupForm?",
        ],
    })

    try:
        agent.parse_output(clarification_json)
        print("  [FALHA] Deveria ter rejeitado needs_clarification")
        return False
    except ValueError as e:
        if "task_id" in str(e).lower() or "field required" in str(e).lower():
            print("  [OK] needs_clarification rejeitado pelo schema TaskContract")
            print(f"       Erro: {str(e)[:100]}")
            return True
        print(f"  [FALHA] Erro inesperado: {e}")
        return False


def test_extra_fields_rejected():
    """Teste 4: Campos desconhecidos sao rejeitados (extra=forbid)."""
    banner("TESTE 4: extra=forbid no TaskContract")
    agent = PlanContractAgent(client=_mock_client())
    bad_json = json.dumps({
        "task_id": "t-004",
        "objective": "Algo",
        "campo_inventado": 42,
    })

    try:
        agent.parse_output(bad_json)
        print("  [FALHA] Deveria ter rejeitado campo extra")
        return False
    except ValueError:
        print("  [OK] Campo extra rejeitado corretamente")
        return True


def test_skill_module_loads():
    """Teste 5: Modulo de skill carrega sem erro."""
    banner("TESTE 5: Skill /contrato carrega")
    try:
        from src.skills.contrato import skill_contrato, main
        print("  [OK] skill_contrato importado")
        print("  [OK] main importada")
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        return False


def test_cli_registered():
    """Teste 6: CLI registrada no __main__.py e pyproject.toml."""
    banner("TESTE 6: CLI registrada")

    ok = True

    main_py = Path("src/__main__.py").read_text(encoding="utf-8")
    if "contrato" in main_py:
        print("  [OK] Registrado em __main__.py")
    else:
        print("  [FALHA] Nao encontrado em __main__.py")
        ok = False

    toml = Path("pyproject.toml").read_text(encoding="utf-8")
    if "multiagentes-contrato" in toml:
        print("  [OK] Registrado em pyproject.toml")
    else:
        print("  [FALHA] Nao encontrado em pyproject.toml")
        ok = False

    return ok


def main():
    print("=" * 60)
    print("  FASE 6.1 — Bridge: Plan -> TaskContract")
    print("=" * 60)

    results = {
        "agent_loads_prompt": test_agent_loads_prompt(),
        "schema_parse": test_schema_parse(),
        "needs_clarification": test_needs_clarification_detection(),
        "extra_fields_rejected": test_extra_fields_rejected(),
        "skill_module_loads": test_skill_module_loads(),
        "cli_registered": test_cli_registered(),
    }

    banner("RESUMO")
    passed = sum(1 for v in results.values() if v)
    for name, ok in results.items():
        print(f"  {'[OK]' if ok else '[FALHA]'} {name}")

    print(f"\n  Total: {passed}/{len(results)}")

    if passed == len(results):
        print("\n  Fase 6.1 validada!")
        sys.exit(0)
    else:
        print("\n  Alguns testes falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()
