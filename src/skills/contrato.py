"""Skill /contrato — gera TaskContract a partir de objetivo em NL.

Fase 6.1: Bridge entre Planner cloud (API) e ExecutionLoop (local).
"""
import json
import sys

from src.agents.planning.contract_bridge import PlanContractAgent


def skill_contrato(
    objetivo: str,
    contexto: str = "",
) -> dict:
    """Gera um TaskContract estruturado a partir de um objetivo.

    Chama o Planner v2 (cloud API) que usa o prompt planner.prompty
    com decision tree, contexto enxuto e required_behavior.

    Args:
        objetivo: O que precisa ser implementado
        contexto: Contexto adicional (estrutura do projeto, padroes, etc.)

    Returns:
        dict com:
        - sucesso: bool
        - contrato: TaskContract (se sucesso) ou None
        - tier: local|medium|strong
        - tokens_usados: int
    """
    agent = PlanContractAgent()

    try:
        contract = agent.run_with_objective(objetivo, contexto or "")
        tokens = getattr(agent, '_last_tokens', 0)

        return {
            "sucesso": True,
            "contrato": contract,
            "tier": contract.tier or "local",
            "objective": contract.objective,
            "allowed_files": contract.allowed_files,
            "tokens_usados": tokens,
        }

    except ValueError as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "needs_clarification": True,
            "contrato": None,
        }
    except RuntimeError as e:
        return {
            "sucesso": False,
            "erro": str(e),
            "needs_clarification": False,
            "contrato": None,
        }
    except Exception as e:
        return {
            "sucesso": False,
            "erro": f"Erro inesperado: {e}",
            "needs_clarification": False,
            "contrato": None,
        }


def main():
    """Entry point CLI: python -m src contrato <objetivo> [contexto]"""
    if len(sys.argv) < 2:
        print("Uso: python -m src contrato <objetivo> [contexto]")
        print()
        print("Exemplos:")
        print('  python -m src contrato "Adicionar validacao de email no signup"')
        print('  python -m src contrato "Criar endpoint GET /products com paginacao" "Usa FastAPI + SQLAlchemy"')
        sys.exit(1)

    objetivo = sys.argv[1]
    contexto = sys.argv[2] if len(sys.argv) > 2 else ""

    print(f"Gerando contrato para: {objetivo}")
    if contexto:
        print(f"Contexto: {contexto}")
    print()

    resultado = skill_contrato(objetivo, contexto)

    if resultado["sucesso"]:
        contract = resultado["contrato"]
        print(f"Tier: {contract.tier}")
        print(f"Risk: {contract.risk}")
        print(f"Files: {contract.allowed_files}")
        print(f"Constraints: {contract.constraints}")
        print(f"Acceptance: {contract.acceptance_criteria}")
        if contract.required_behavior:
            print(f"Required behavior: {json.dumps(contract.required_behavior, indent=2, default=str)}")
        print(f"\nTokens: {resultado['tokens_usados']}")

        # Exportar como JSON para uso em pipeline
        print("\n--- TASKCONTRACT JSON ---")
        print(contract.model_dump_json(indent=2))
    else:
        print(f"ERRO: {resultado['erro']}")
        if resultado.get("needs_clarification"):
            print("\nO Planner precisa de mais informacoes para gerar o contrato.")
        sys.exit(1)


if __name__ == "__main__":
    main()
