"""Skill /implementar - Implementa planos com verificação de código."""

import json
from pathlib import Path
from typing import Optional

from src.agents.codegen import CodeGenAgent, CodeVerifierAgent
from src.schemas.plano import Plan


def skill_implementar(
    plano: Plan | dict,
    output_dir: str | None = None,
    linguagem: str = "python"
) -> dict:
    """
    Skill /implementar: Implementa plano com verificação de código.

    Workflow:
    1. CodeGen implementa o plano
    2. CodeVerifier verifica se código satisfaz o plano
    3. Se não aprovado, refinamento (loop)
    4. Retorna código aprovado

    Args:
        plano: Plano a implementar (objeto Plan ou dict)
        output_dir: Diretório para salvar arquivos (opcional)
        linguagem: Linguagem do código (default: python)

    Returns:
        dict com:
        - sucesso: bool
        - arquivos: lista de arquivos gerados
        - verificacao: resultado da verificação
        - tentativas: número de iterações
        - tokens_totais: tokens consumidos
    """
    # Normalizar plano para dict
    if isinstance(plano, Plan):
        plano_dict = plano.model_dump()
    else:
        plano_dict = plano

    max_tentativas = 3
    tentativa = 0
    tokens_totais = 0

    # Inicializar agentes
    generator = CodeGenAgent()
    verifier = CodeVerifierAgent()

    for tentativa in range(max_tentativas):
        print(f"\n🔧 /implementar - Tentativa {tentativa + 1}/{max_tentativas}")

        # Step 1: Gerar código
        plano_json = json.dumps(plano_dict, ensure_ascii=False)
        gen_result = generator.run(
            plano_json=plano_json,
            contexto_codigo="",  # Código existente, se houver
            linguagem=linguagem
        )
        tokens_totais += gen_result.tokens_usados or 0

        if not gen_result.sucesso:
            return {
                "sucesso": False,
                "erro": gen_result.erro,
                "tentativas": tentativa + 1,
                "tokens_totais": tokens_totais
            }

        code_output = gen_result.output
        arquivos = code_output.get("arquivos", [])
        print(f"   ✅ {len(arquivos)} arquivos gerados")

        # Step 2: Verificar código
        codigo_json = json.dumps(code_output, ensure_ascii=False)
        verif_result = verifier.run(
            plano_json=plano_json,
            codigo_json=codigo_json
        )
        tokens_totais += verif_result.tokens_usados or 0

        if not verif_result.sucesso:
            return {
                "sucesso": False,
                "erro": verif_result.erro,
                "arquivos": arquivos,
                "tentativas": tentativa + 1,
                "tokens_totais": tokens_totais
            }

        verificacao = verif_result.output

        if verificacao.get("aprovado", False):
            print(f"   ✅ Código aprovado!")

            # Salvar arquivos se output_dir fornecido
            if output_dir:
                salvar_arquivos(arquivos, output_dir)
                print(f"   💾 Arquivos salvos em {output_dir}")

            return {
                "sucesso": True,
                "arquivos": arquivos,
                "resumo": code_output.get("resumo", ""),
                "verificacao": verificacao,
                "tentativas": tentativa + 1,
                "tokens_totais": tokens_totais
            }

        # Coletar feedback para próxima tentativa
        print(f"   ❌ Código rejeitado")
        problemas = verificacao.get("problemas_codigo", [])
        passos_faltando = verificacao.get("passos_faltando", [])

        if passos_faltando:
            print(f"   ⚠️  Passos faltando: {passos_faltando}")

        # Atualizar plano com feedback (simplificado)
        # Em uma implementação mais completa, refinaríamos o prompt

    # Limite de tentativas atingido
    return {
        "sucesso": False,
        "erro": "Limite de tentativas atingido sem aprovação",
        "arquivos": arquivos,
        "verificacao": verificacao,
        "tentativas": max_tentativas,
        "tokens_totais": tokens_totais
    }


def salvar_arquivos(arquivos: list, output_dir: str) -> None:
    """
    Salva arquivos gerados no diretório de saída.

    Args:
        arquivos: Lista de dicts com caminho e conteudo
        output_dir: Diretório de saída
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for arquivo in arquivos:
        caminho = out_path / arquivo["caminho"]
        caminho.parent.mkdir(parents=True, exist_ok=True)
        caminho.write_text(arquivo["conteudo"], encoding="utf-8")
        print(f"      💾 {arquivo['caminho']}")


# Alias para CLI
def main():
    """Entry point para uso via CLI."""
    import sys

    if len(sys.argv) < 3:
        print("Uso: python -m src.implementar <plano.json> [output_dir]")
        print("\nExemplo:")
        print("  python -m src implementar plano.json src/")
        sys.exit(1)

    plano_file = sys.argv[1]
    output_dir = sys.argv[2] if len(sys.argv) > 2 else None

    # Ler plano do arquivo JSON
    try:
        with open(plano_file, 'r', encoding='utf-8') as f:
            plano = json.load(f)
    except Exception as e:
        print(f"Erro ao ler plano: {e}")
        sys.exit(1)

    resultado = skill_implementar(plano, output_dir)

    if resultado.get("sucesso"):
        print("\n✅ IMPLEMENTAÇÃO APROVADA")
        print(f"\n{resultado['resumo']}")
        print(f"\nArquivos gerados: {len(resultado['arquivos'])}")
        for arq in resultado['arquivos']:
            print(f"  • {arq['caminho']}")
    else:
        print(f"\n❌ FALHA: {resultado.get('erro', 'Desconhecido')}")


if __name__ == "__main__":
    main()
