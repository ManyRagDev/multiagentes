"""Teste rápido do provider local com auto-recovery.

Valida:
1. Health check do llama-server
2. Auto-recovery se o servidor estiver down
3. Geração de código via OpenAI-compatible API
"""

import sys
from pathlib import Path

# Adiciona o projeto ao path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.providers import ProviderRegistry


def main():
    print("=" * 60)
    print("TESTE: Local Qwen Provider + Auto-Recovery")
    print("=" * 60)

    # Obter provider
    provider = ProviderRegistry.get("local-qwen")

    # Teste 1: Health check
    print("\n[1/3] Verificando saúde do servidor...")
    if provider.is_available():
        print("  ✅ Servidor já está rodando")
    else:
        print("  ⚠️ Servidor não respondendo. Tentando auto-recovery...")
        try:
            provider.ensure_ready()
            print("  ✅ Auto-recovery bem-sucedido!")
        except Exception as e:
            print(f"  ❌ Falha no auto-recovery: {e}")
            return

    # Teste 2: Cliente OpenAI
    print("\n[2/3] Obtendo cliente OpenAI...")
    client = provider.get_client()
    print(f"  ✅ Cliente criado: base_url={client.base_url}")

    # Teste 3: Geração simples
    print("\n[3/3] Testando geração de código...")
    try:
        response = client.chat.completions.create(
            model="qwen2.5-coder-7b-instruct",
            messages=[
                {
                    "role": "system",
                    "content": "Você é um assistente de código Python. Responda apenas com código."
                },
                {
                    "role": "user",
                    "content": "Escreva uma função que calcula fatorial recursivamente com type hints e docstring."
                }
            ],
            temperature=0.3,
            max_tokens=256,
        )
        code = response.choices[0].message.content
        tokens = response.usage.total_tokens if response.usage else "?"
        print(f"  ✅ Geração OK ({tokens} tokens)")
        print(f"\n--- Código Gerado ---\n{code}\n---------------------")
    except Exception as e:
        print(f"  ❌ Erro na geração: {e}")
        import traceback
        traceback.print_exc()

    print("\n" + "=" * 60)
    print("Teste concluído!")
    print("=" * 60)


if __name__ == "__main__":
    main()
