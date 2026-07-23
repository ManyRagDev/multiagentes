#!/usr/bin/env python3
"""
Wrapper para usar skills do multiagentes de qualquer projeto.

Uso:
    python claude_skills.py plano "Criar API de autenticação"
    python claude_skills.py auditoria src/ bugs,security
"""

import sys
import os
from pathlib import Path

# Adiciona o diretório do multiagentes ao PATH
multiagentes_dir = Path(__file__).parent
sys.path.insert(0, str(multiagentes_dir / "src"))

def cmd_plano(args):
    """Executa skill /plano."""
    from skills.plano import skill_plano

    tarefa = " ".join(args) if args else input("Descreva a tarefa: ")

    resultado = skill_plano(tarefa=tarefa)

    print("\n" + "="*60)
    print("📋 PLANO GERADO")
    print("="*60)
    print(resultado.get("resumo", "Plano gerado com sucesso"))
    print("="*60)

    return resultado


def cmd_auditoria(args):
    """Executa skill /auditoria."""
    from skills.auditoria import skill_auditoria

    if not args:
        print("Uso: python claude_skills.py auditoria <caminho> [dimensoes]")
        print("Exemplo: python claude_skills.py auditoria src/ bugs,security")
        sys.exit(1)

    caminho = args[0]
    dimensoes = args[1].split(",") if len(args) > 1 else ["bugs", "security", "performance"]

    resultado = skill_auditoria(
        caminho_codigo=caminho,
        dimensoes=dimensoes
    )

    print("\n" + "="*60)
    print("🔍 AUDITORIA CONCLUÍDA")
    print("="*60)
    print(resultado.get("resumo", "Auditoria concluída"))
    print(f"Tokens usados: {resultado.get('tokens_totais', 0)}")
    print("="*60)

    return resultado


def cmd_implementar(args):
    """Executa skill /implementar."""
    from skills.implementar import skill_implementar

    print("⚠️  /implementar requer arquivo de plano (feature em desenvolvimento)")
    print("Por enquanto, implemente você mesmo com ajuda do Claude Code!")
    return {}


def main():
    """Ponto de entrada principal."""
    if len(sys.argv) < 2:
        print("="*60)
        print("Multiagentes - Skills Disponíveis")
        print("="*60)
        print("\nUso:")
        print("  python claude_skills.py <skill> <argumentos>")
        print("\nSkills disponíveis:")
        print("  plano       - Gerar e validar planos")
        print("  auditoria   - Auditar código")
        print("  implementar - Implementar código (em dev)")
        print("\nExemplos:")
        print("  python claude_skills.py plano Criar API de usuários")
        print("  python claude_skills.py auditoria src/ bugs,security")
        print("="*60)
        sys.exit(1)

    comando = sys.argv[1]
    args = sys.argv[2:]

    comandos = {
        "plano": cmd_plano,
        "auditoria": cmd_auditoria,
        "implementar": cmd_implementar,
    }

    if comando not in comandos:
        print(f"❌ Comando desconhecido: {comando}")
        print(f"Comandos disponíveis: {', '.join(comandos.keys())}")
        sys.exit(1)

    try:
        comandos[comando](args)
    except KeyboardInterrupt:
        print("\n\n⚠️  Operação cancelada")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erro: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
