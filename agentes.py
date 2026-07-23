import os
import json
from dotenv import load_dotenv
from openai import OpenAI

# Carrega as variáveis do .env
load_dotenv()

# Configura o client apontando para a z.ai
client = OpenAI(
    api_key=os.getenv("ZAI_API_KEY"),
    base_url=os.getenv("ZAI_BASE_URL")
)

MODEL_NAME = os.getenv("ZAI_MODEL", "glm-5.2")


def agente_gerador(topico, feedback_anterior=""):
    """Agente 1: escreve o relatório"""
    prompt = f"""Escreva sobre: "{topico}"

Seja direto e natural. Escreva como se estivesse explicando para um colega.

{f'FEEDBACK ANTERIOR: {feedback_anterior}' if feedback_anterior else ''}

Dica: use bullet points e vá direto ao ponto. Sem enrolação.
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[
            {"role": "system", "content": "Escreva de forma direta e clara. Sem burocracia."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.4
    )
    return response.choices[0].message.content


def agente_revisor(relatorio):
    """Agente 2: audita o relatório"""
    prompt = f"""Analise o texto abaixo e responda APENAS em JSON válido:
{{
  "aprovado": true/false,
  "nota": 0-10,
  "feedback": "o que corrigir (vazio se aprovado)"
}}

Rejeite se tiver typos ou erros de português.

TEXTO:
{relatorio}
"""
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{"role": "user", "content": prompt}],
        temperature=0.2  # Revisor deve ser determinístico
    )
    raw = response.choices[0].message.content
    
    # Limpa markdown caso o modelo envolva em ```json ... ```
    raw = raw.replace('```json', '').replace('```', '').strip()
    return json.loads(raw)


# --- ORQUESTRAÇÃO ---
if __name__ == "__main__":
    import sys
    import io

    # Fix encoding para Windows terminal
    if sys.platform == "win32":
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    
    # Pega o tópico da linha de comando
    if len(sys.argv) > 1:
        topico = " ".join(sys.argv[1:])
    else:
        print("⚠️  Uso: python agentes.py <tópico>")
        print("   Exemplo: python agentes.py 'Análise de desempenho do Q2'")
        sys.exit(1)
    
    max_tentativas = 5
    feedback = ""
    
    print(f"🎯 Tópico: {topico}")

    for tentativa in range(max_tentativas):
        print(f"\n{'='*50}")
        print(f"🔄 Tentativa {tentativa + 1}/{max_tentativas}")
        print(f"{'='*50}")
        
        relatorio = agente_gerador(topico, feedback)
        print("\n📝 RELATÓRIO GERADO:")
        print(relatorio[:500] + "..." if len(relatorio) > 500 else relatorio)
        
        try:
            auditoria = agente_revisor(relatorio)
            print(f"\n🔍 AUDITORIA: Nota {auditoria['nota']}/10 | Aprovado: {auditoria['aprovado']}")
            
            if auditoria['aprovado']:
                print("\n✅ RELATÓRIO FINAL APROVADO!")
                print(relatorio)
                break
            else:
                print(f"❌ Rejeitado. Feedback: {auditoria['feedback']}")
                feedback = auditoria['feedback']
        except json.JSONDecodeError as e:
            print(f"⚠️ Revisor não retornou JSON válido: {e}")
            feedback = "Responda estritamente em JSON válido, sem texto adicional."
    else:
        print("\n⚠️ Limite de tentativas atingido.")
        print("\n📄 Última versão gerada:")
        print(relatorio)