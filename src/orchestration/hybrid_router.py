"""HybridRouter - Router híbrido: regras + Groq quando necessário."""

import os
from openai import OpenAI
from typing import Literal

from .router import Router


class HybridRouter:
    """
    Router híbrido que usa regras primeiro, LLM depois se necessário.

    Economia: usa LLM apenas quando realmente precisa.
    """

    def __init__(self):
        """Inicializa HybridRouter."""
        self.router = Router()
        self.groq_client = None

        # Inicializa cliente Groq se API key disponível
        groq_key = os.getenv("GROQ_API_KEY")
        if groq_key:
            self.groq_client = OpenAI(
                base_url="https://api.groq.com/openai/v1",
                api_key=groq_key
            )

    def route(
        self,
        user_input: str,
        context: dict | None = None
    ) -> Literal["plano", "auditoria", "implementar", "indeciso"]:
        """
        Roteia input para skill apropriada.

        Tenta regras primeiro, LLM depois.

        Args:
            user_input: Input do usuário
            context: Contexto adicional

        Returns:
            Skill selecionada
        """
        # Tenta regras primeiro (grátis, instantâneo)
        skill = self.router.route(user_input, context)

        if skill != "indeciso":
            return skill

        # Regras falharam e tem Groq disponível?
        if self.groq_client:
            return self._route_with_llm(user_input, context)

        # Sem Groq, retorna indeciso
        return "indeciso"

    def _route_with_llm(
        self,
        user_input: str,
        context: dict | None = None
    ) -> Literal["plano", "auditoria", "implementar", "indeciso"]:
        """
        Usa Groq + GPT-QWEN-12B para decidir rota.

        Prompt minimalista para custo mínimo.
        """
        # Prepara contexto resumido se disponível
        context_hint = ""
        if context and "files" in context:
            num_files = len(context["files"])
            context_hint = f" (envolvendo {num_files} arquivos)"

        # Prompt ultra minimalista
        prompt = f"""Classifique este pedido em uma palavra: plano, auditoria, implementar

Pedido: "{user_input[:200]}"{context_hint}

Responda apenas uma palavra."""

        try:
            response = self.groq_client.chat.completions.create(
                model="gpt-qwen-12b",  # ou modelo disponível no Groq
                messages=[{"role": "user", "content": prompt}],
                max_tokens=10,
                temperature=0.1
            )

            result = response.choices[0].message.content.strip().lower()

            # Mapeia resposta para skill
            if "plano" in result or "planej" in result:
                return "plano"
            elif "audit" in result or "anális" in result or "review" in result:
                return "auditoria"
            elif "implement" in result or "gerar" in result or "codific" in result:
                return "implementar"

            return "indeciso"

        except Exception as e:
            # Erro com Groq? Fallback para indeciso
            print(f"⚠️ Erro Groq routing: {e}")
            return "indeciso"


# Instância singleton
hybrid_router = HybridRouter()
