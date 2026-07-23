"""Skill /plano - Gera plano de implementação validado."""

import json
from typing import Optional

from src.agents.planning import (
    PlanCreatorAgent,
    PlanValidatorAgent,
    DependencyCheckerAgent
)
from src.orchestration import Orchestrator, WorkflowResult
from src.schemas.plano import Plan


def skill_plano(
    objetivo: str,
    contexto: str = "",
    max_tentativas: int = 3
) -> dict:
    """
    Skill /plano: Gera plano de implementação validado.

    Workflow:
    1. PlanCreator gera o plano
    2. PlanValidator valida inconsistências
    3. DependencyChecker valida dependências
    4. Se não aprovado, refina com feedback (loop)
    5. Retorna plano aprovado

    Args:
        objetivo: O que precisa ser feito
        contexto: Contexto adicional (opcional)
        max_tentativas: Máximo de iterações de refinamento

    Returns:
        dict com:
        - plano: Plan aprovado
        - validacao: PlanValidation final
        - tentativas: número de tentativas
        - tokens_totais: tokens consumidos
    """
    # Inicializar agentes
    creator = PlanCreatorAgent()
    validator = PlanValidatorAgent()
    dep_checker = DependencyCheckerAgent()

    # Estado inicial
    feedback_problemas: list[str] = []
    tentativa = 0
    tokens_totais = 0

    for tentativa in range(max_tentativas):
        print(f"\n🔄 /plano - Tentativa {tentativa + 1}/{max_tentativas}")

        # Step 1: Criar plano (com feedback se houver)
        inputs = {"objetivo": objetivo, "contexto": contexto}
        if feedback_problemas:
            inputs["feedback"] = "\\n".join(feedback_problemas)

        creator_result = creator.run(**inputs)
        tokens_totais += creator_result.tokens_usados or 0

        if not creator_result.sucesso:
            return {
                "sucesso": False,
                "erro": creator_result.erro,
                "tentativas": tentativa + 1,
                "tokens_totais": tokens_totais
            }

        plano_dict = creator_result.output
        print(f"   ✅ Plano gerado com {len(plano_dict.get('passos', []))} passos")

        # Step 2: Validar inconsistências gerais
        plano_json = json.dumps(plano_dict, ensure_ascii=False)
        validator_result = validator.run(plano_json=plano_json)
        tokens_totais += validator_result.tokens_usados or 0

        if not validator_result.sucesso:
            return {
                "sucesso": False,
                "erro": validator_result.erro,
                "tentativas": tentativa + 1,
                "tokens_totais": tokens_totais
            }

        validacao = validator_result.output

        # Step 3: Validar dependências
        dep_result = dep_checker.run(plano_json=plano_json)
        tokens_totais += dep_result.tokens_usados or 0

        if dep_result.sucesso and dep_result.output:
            # Adiciona problemas de dependência à validação
            dep_problemas = dep_result.output.get("problemas", [])
            if dep_problemas:
                validacao["problemas"].extend(dep_problemas)

        # Verificar se aprovado
        aprovado = validacao.get("aprovado", False)
        problemas = validacao.get("problemas", [])

        if aprovado:
            print(f"   ✅ Plano aprovado!")
            return {
                "sucesso": True,
                "plano": plano_dict,
                "validacao": validacao,
                "tentativas": tentativa + 1,
                "tokens_totais": tokens_totais
            }

        # Coletar feedback para próxima tentativa
        print(f"   ❌ Plano rejeitado: {len(problemas)} problemas")
        feedback_problemas = [
            f"- {p.get('descricao', p)}" for p in problemas
        ]

    # Limite de tentativas atingido
    return {
        "sucesso": False,
        "erro": "Limite de tentativas atingido sem aprovação",
        "plano": plano_dict,  # Último plano gerado
        "validacao": validacao,
        "tentativas": max_tentativas,
        "tokens_totais": tokens_totais
    }


# Alias para CLI
def main():
    """Entry point para uso via CLI."""
    import sys

    if len(sys.argv) < 2:
        print("Uso: python -m src.skills.plano <objetivo> [contexto]")
        sys.exit(1)

    objetivo = sys.argv[1]
    contexto = sys.argv[2] if len(sys.argv) > 2 else ""

    resultado = skill_plano(objetivo, contexto)

    if resultado.get("sucesso"):
        print("\\n✅ PLANO APROVADO:")
        print(json.dumps(resultado["plano"], indent=2, ensure_ascii=False))
    else:
        print(f"\\n❌ FALHA: {resultado.get('erro', 'Desconhecido')}")
        if "plano" in resultado:
            print("\\nÚltimo plano gerado:")
            print(json.dumps(resultado["plano"], indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
