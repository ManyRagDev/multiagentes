#!/usr/bin/env python3
"""
Script para instalar multiagentes globalmente e configurar para Claude Code.
"""

import subprocess
import sys
import os
from pathlib import Path


def run_command(cmd, description):
    """Executa comando e mostra progresso."""
    print(f"\n📦 {description}...")
    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"   ✅ {description} concluído")
        return True
    except subprocess.CalledProcessError as e:
        print(f"   ❌ Erro: {e.stderr}")
        return False


def main():
    """Instala multiagentes globalmente."""
    print("=" * 60)
    print("🚀 Instalando Multiagentes Globalmente")
    print("=" * 60)

    # 1. Instalar pacote globalmente
    project_dir = Path(__file__).parent
    success = run_command(
        f'cd "{project_dir}" && pip install -e .',
        "Instalando pacote multiagentes"
    )

    if not success:
        print("\n❌ Falha na instalação")
        sys.exit(1)

    # 2. Verificar instalação
    print("\n🔍 Verificando instalação...")
    try:
        result = subprocess.run(
            ["pip", "show", "multiagentes"],
            capture_output=True,
            text=True,
            check=True
        )
        print("   ✅ Pacote instalado:")
        for line in result.stdout.split('\n')[:5]:
            if line.strip():
                print(f"      {line}")
    except:
        print("   ⚠️  Não foi possível verificar instalação")

    # 3. Testar comandos
    print("\n🧪 Testando comandos...")
    commands = ["multiagentes-plano", "multiagentes-auditoria", "multiagentes-implementar"]
    for cmd in commands:
        try:
            result = subprocess.run(
                ["python", "-m", f"src.skills.{cmd.split('-')[1]}"],
                capture_output=True,
                cwd=project_dir,
                timeout=2
            )
            print(f"   ✅ {cmd}: disponível")
        except:
            print(f"   ⚠️  {cmd}: não verificável")

    # 4. Criar arquivo de configuração para Claude Code
    print("\n📝 Criando configuração para Claude Code...")
    claude_config_dir = Path.home() / ".claude"
    claude_config_dir.mkdir(exist_ok=True)

    config_file = claude_config_dir / "multiagentes_config.json"
    import json
    config = {
        "skills_path": str(project_dir / "src" / "skills"),
        "project_dir": str(project_dir),
        "version": "0.1.0"
    }

    with open(config_file, 'w') as f:
        json.dump(config, f, indent=2)
    print(f"   ✅ Configuração salva em: {config_file}")

    # 5. Instruções
    print("\n" + "=" * 60)
    print("✅ Instalação Concluída!")
    print("=" * 60)
    print("\n📖 Como Usar em Qualquer Projeto:")
    print("\n1. Abra seu projeto no Claude Code:")
    print("   cd C:\\Users\\emanu\\Documents\\Projetos\\PostSpark\\ 3")
    print("   claude")
    print("\n2. No chat do Claude Code, use:")
    print("   /plano Criar sistema de autenticação")
    print("   /auditoria src/ --dimensoes bugs,security")
    print("   /implementar --plano <dados>")
    print("\n3. Ou via linha de comando:")
    print("   multiagentes-plano")
    print("   multiagentes-auditoria src/")
    print("   multiagentes-implementar --plano plano.json")
    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()
