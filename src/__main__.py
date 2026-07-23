"""Entry point para CLI do sistema multiagentes."""

import sys


def main():
    """Entry point principal."""
    if len(sys.argv) < 2:
        print("Uso: python -m src <skill> [args...]")
        print("\nSkills disponíveis:")
        print("  plano       - Gerar plano de implementação")
        print("  auditoria   - Auditar código com verificação adversarial")
        print("  implementar - Implementar plano com geração de código")
        print("  contrato    - Gerar TaskContract (Planner v2) pronto para execução")
        print("  run         - Pipeline completo: Planner → Executor → Reviewer → Merge")
        print("\nExemplos:")
        print("  python -m src plano 'Adicionar autenticação JWT'")
        print("  python -m src auditoria src/ bugs,security")
        print("  python -m src implementar plano.json src/")
        print("  python -m src contrato 'Adicionar validação de email no signup'")
        print("  python -m src run 'Criar função soma_pares em src/math.py'")
        sys.exit(1)

    skill = sys.argv[1]

    if skill == "plano":
        from src.skills.plano import main as plano_main
        sys.argv = ["plano"] + sys.argv[2:]
        plano_main()
    elif skill in ("auditoria", "audit"):
        from src.skills.auditoria import main as auditoria_main
        sys.argv = ["auditoria"] + sys.argv[2:]
        auditoria_main()
    elif skill in ("implementar", "impl"):
        from src.skills.implementar import main as implementar_main
        sys.argv = ["implementar"] + sys.argv[2:]
        implementar_main()
    elif skill in ("contrato", "contract"):
        from src.skills.contrato import main as contrato_main
        sys.argv = ["contrato"] + sys.argv[2:]
        contrato_main()
    elif skill in ("run", "executar"):
        from src.skills.run import main as run_main
        sys.argv = ["run"] + sys.argv[2:]
        run_main()
    else:
        print(f"Skill desconhecida: {skill}")
        print("Use 'python -m src' para ver skills disponíveis")
        sys.exit(1)


if __name__ == "__main__":
    main()
