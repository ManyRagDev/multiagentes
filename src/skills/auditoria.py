"""Skill /auditoria - Audita código com múltiplos agentes e verificação adversarial."""

import json
from pathlib import Path
from typing import Optional, Literal

from src.agents.audit import BugHunterAgent, SecAuditAgent, PerfAnalystAgent
from src.agents.verify import (
    BugRefuterAgent,
    SecSkepticAgent,
    PerfDoubterAgent,
    CompletenessCheckAgent
)
from src.orchestration import Orchestrator
from src.orchestration.context_manager import context_manager


def skill_auditoria(
    caminho_codigo: str,
    dimensoes: list[str] | None = None,
    linguagem: str = "python"
) -> dict:
    """
    Skill /auditoria: Audita código com verificação adversarial.

    Workflow:
    1. Lê código do(s) arquivo(s)
    2. Divide contexto em chunks se necessário
    3. Auditores rodam em paralelo
    4. Verificadores adversariais contestam findings
    5. Meta-auditor verifica completude
    6. Retorna report consolidado

    Args:
        caminho_codigo: Caminho para arquivo ou diretório
        dimensoes: Dimensões para analisar ["bugs", "security", "performance"]
        linguagem: Linguagem do código (default: python)

    Returns:
        dict com:
        - sucesso: bool
        - findings: lista de findings confirmados
        - verdicts: lista de vereditos adversariais
        - completude: report de meta-auditoria
        - tokens_totais: tokens consumidos
        - resumo: resumo executivo
    """
    if dimensoes is None:
        dimensoes = ["bugs", "security", "performance"]

    # Inicializar agentes
    auditores = {}
    verificadores = {}

    if "bugs" in dimensoes:
        auditores["bug_hunter"] = BugHunterAgent()
        verificadores["bug_refuter"] = BugRefuterAgent()

    if "security" in dimensoes:
        auditores["sec_audit"] = SecAuditAgent()
        verificadores["sec_skeptic"] = SecSkepticAgent()

    if "performance" in dimensoes:
        auditores["perf_analyst"] = PerfAnalystAgent()
        verificadores["perf_doubter"] = PerfDoubterAgent()

    meta_auditor = CompletenessCheckAgent()

    # Ler código
    path = Path(caminho_codigo)
    if not path.exists():
        return {
            "sucesso": False,
            "erro": f"Caminho não encontrado: {caminho_codigo}"
        }

    codigo_dict = ler_codigo(path, linguagem)

    if not codigo_dict["arquivos"]:
        return {
            "sucesso": False,
            "erro": f"Nenhum arquivo encontrado em: {caminho_codigo}"
        }

    # Usar ContextManager para dividir trabalho se contexto grande
    contexto_summary = context_manager.get_context_summary(codigo_dict["arquivos"])
    print(f"\n📊 Contexto: {contexto_summary['num_files']} arquivos, ~{contexto_summary['estimated_tokens']} tokens")

    # Se contexto é grande, dividir em chunks
    if contexto_summary["needs_chunking"]:
        print(f"   🔄 Dividindo em chunks (max {context_manager.max_chunk_size} chars)")
        chunks = context_manager.prepare_chunks(codigo_dict["arquivos"])
        print(f"   📦 {len(chunks)} chunks criados")
    else:
        # Contexto pequeno, chunk único
        chunks = [codigo_dict["arquivos"]]

    tokens_totais = 0
    all_findings: list = []
    all_verdicts: list = []

    print(f"\n🔍 /auditoria - {len(codigo_dict['arquivos'])} arquivos")

    # Step 1: Auditores por chunk
    print(f"   📊 Processando com {len(auditores)} auditores...")

    tasks_auditores = []

    for chunk_idx, chunk in enumerate(chunks):
        chunk_summary = f"Chunk {chunk_idx + 1}/{len(chunks)} ({len(chunk)} arquivos)"
        for nome, agente in auditores.items():
            tasks_auditores.append({
                "agent": agente,
                "inputs": {
                    "chunk_info": chunk_summary,
                    "arquivos": chunk,
                    "contexto": f"Projeto: {codigo_dict['projeto']}",
                    "linguagem": linguagem
                },
                "output_name": f"{nome}_chunk{chunk_idx}"
            })

    orchestrator = Orchestrator()
    audit_result = orchestrator.run_parallel(tasks_auditores, max_workers=len(auditores))
    tokens_totais += audit_result.tokens_totais

    # Coletar findings
    for output_name, output in audit_result.outputs.items():
        if isinstance(output, list):
            all_findings.extend(output)
            print(f"   ✅ {output_name}: {len(output)} findings")

    if not all_findings:
        print(f"   ℹ️  Nenhum finding encontrado")

        # Ainda assim, rodar meta-check
        completeness_result = meta_auditor.run(
            codigo_analisado=str(codigo_dict),
            audit_json=json.dumps({"findings": []}, ensure_ascii=False)
        )
        tokens_totais += completeness_result.tokens_usados or 0

        return {
            "sucesso": True,
            "findings": [],
            "verdicts": [],
            "completude": completeness_result.output if completeness_result.sucesso else None,
            "tokens_totais": tokens_totais,
            "resumo": "Nenhum problema encontrado. Código limpo."
        }

    # Step 2: Verificadores adversariais (por tipo)
    print(f"   ⚖️  Verificando {len(all_findings)} findings...")

    # Agrupar findings por tipo
    findings_by_type: dict[str, list] = {"bug": [], "security": [], "performance": []}
    for f in all_findings:
        tipo = f.get("tipo", "bug")
        if tipo in findings_by_type:
            findings_by_type[tipo].append(f)

    tasks_verificadores = []
    for tipo, findings in findings_by_type.items():
        if not findings:
            continue

        # Selecionar verificador apropriado
        verificador_key = f"{tipo}_refuter" if tipo == "bug" else f"{tipo}_skeptic" if tipo == "security" else f"{tipo}_doubter"
        verificador = verificadores.get(verificador_key)

        if verificador:
            # Código completo para contexto
            codigo_completo = "\n\n".join(
                f"# {arq}\n{cont}" for arq, cont in codigo_dict["arquivos"].items()
            )

            tasks_verificadores.append({
                "agent": verificador,
                "inputs": {
                    "codigo": codigo_completo,
                    "linguagem": linguagem,
                    "findings_json": json.dumps(findings, ensure_ascii=False)
                },
                "output_name": f"verdict_{tipo}"
            })

    if tasks_verificadores:
        verify_result = orchestrator.run_parallel(tasks_verificadores, max_workers=len(tasks_verificadores))
        tokens_totais += verify_result.tokens_totais

        # Coletar verdicts
        for output_name, output in verify_result.outputs.items():
            if isinstance(output, list):
                all_verdicts.extend(output)
                confirmados = sum(1 for v in output if v.get("confirmado"))
                print(f"   ✅ {output_name}: {confirmados}/{len(output)} confirmados")

    # Step 3: Meta-check (completude)
    print(f"   🔎 Verificando completude...")

    codigo_completo = "\n\n".join(
        f"# {arq}\n{cont}" for arq, cont in codigo_dict["arquivos"].items()
    )

    completeness_result = meta_auditor.run(
        codigo_analisado=codigo_completo,
        audit_json=json.dumps({
            "findings": all_findings,
            "verdicts": all_verdicts,
            "files_analisados": list(codigo_dict["arquivos"].keys())
        }, ensure_ascii=False)
    )
    tokens_totais += completeness_result.tokens_usados or 0

    if completeness_result.sucesso:
        completude = completeness_result.output
        esta_completo = completude.get("conclusao", {}).get("completa", False)
        print(f"   {'✅' if esta_completo else '⚠️'} Completude: {'completa' if esta_completo else 'incompleta'}")

    # Gerar resumo
    resumo = gerar_resumo(all_findings, all_verdicts, completude if completeness_result.sucesso else None)

    return {
        "sucesso": True,
        "findings": all_findings,
        "verdicts": all_verdicts,
        "completude": completude if completeness_result.sucesso else None,
        "tokens_totais": tokens_totais,
        "resumo": resumo
    }


def ler_codigo(path: Path, linguagem: str) -> dict:
    """
    Lê código de arquivo ou diretório.

    Args:
        path: Caminho para arquivo ou diretório
        linguagem: Linguagem do código

    Returns:
        dict com projeto e arquivos
    """
    extensoes = {
        "python": [".py"],
        "javascript": [".js", ".jsx", ".ts", ".tsx"],
        "java": [".java"],
        "go": [".go"],
        "rust": [".rs"],
    }

    exts = extensoes.get(linguagem, [f".{linguagem}"])

    if path.is_file():
        return {
            "projeto": path.parent.name,
            "arquivos": {str(path): path.read_text(encoding="utf-8", errors="ignore")}
        }

    # Diretório
    arquivos = {}
    for ext in exts:
        for arquivo in path.rglob(f"*{ext}"):
            if "__pycache__" not in str(arquivo) and ".venv" not in str(arquivo):
                try:
                    arquivos[str(arquivo)] = arquivo.read_text(encoding="utf-8", errors="ignore")
                except Exception:
                    pass

    return {
        "projeto": path.name,
        "arquivos": arquivos
    }


def gerar_resumo(findings: list, verdicts: list, completude: dict | None) -> str:
    """
    Gera resumo executivo da auditoria.

    Args:
        findings: Todos os findings encontrados
        verdicts: Vereditos adversariais
        completude: Report de completude

    Returns:
        Resumo em texto
    """
    total = len(findings)
    confirmados = sum(1 for v in verdicts if v.get("confirmado"))

    por_severidade = {}
    for f in findings:
        sev = f.get("severidade", "info")
        por_severidade[sev] = por_severidade.get(sev, 0) + 1

    linhas = [
        f"📊 Auditoria de Código",
        f"",
        f"• {total} findings encontrados",
        f"• {confirmados} confirmados após verificação adversarial",
    ]

    if por_severidade:
        linhas.append(f"")
        linhas.append(f"Por severidade:")
        for sev in ["critical", "high", "medium", "low", "info"]:
            if sev in por_severidade:
                linhas.append(f"  • {sev.upper()}: {por_severidade[sev]}")

    if completude:
        conclusao = completude.get("conclusao", {})
        if not conclusao.get("completa", True):
            faltando = completude.get("faltando", [])
            if faltando:
                linhas.append(f"")
                linhas.append(f"⚠️  Gaps identificados:")
                for falta in faltando[:3]:
                    linhas.append(f"  • {falta.get('categoria', '')}: {falta.get('descricao', '')}")

    return "\n".join(linhas)


# Alias para CLI
def main():
    """Entry point para uso via CLI."""
    import sys

    if len(sys.argv) < 2:
        print("Uso: python -m src.auditoria <caminho> [dimensoes]")
        print("\nDimensões (separadas por vírgula):")
        print("  bugs,security,performance")
        print("\nExemplo:")
        print("  python -m src auditoria src/ bugs,security")
        sys.exit(1)

    caminho = sys.argv[1]
    dimensoes = sys.argv[2].split(",") if len(sys.argv) > 2 else ["bugs", "security", "performance"]

    resultado = skill_auditoria(caminho, dimensoes)

    if resultado.get("sucesso"):
        print("\n" + resultado["resumo"])
        print(f"\nTokens usados: {resultado['tokens_totais']}")
    else:
        print(f"\n❌ FALHA: {resultado.get('erro', 'Desconhecido')}")


if __name__ == "__main__":
    main()
