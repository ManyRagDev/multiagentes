"""Router - Roteamento baseado em regras (sem LLM)."""

import re
from typing import Literal


class Router:
    """
    Router que direciona inputs para skills apropriadas.

    Usa regras - ultra rápido, sem custo, determinístico.
    """

    # Padrões de roteamento em ordem de especificidade
    PATTERNS = [
        # (padrão_regex, skill)
        (r"\b(planejar|plano|estratégia|design|architecture)\b", "plano"),
        (r"\b(auditar|auditoria|analisar código|review|bug|security|performance)\b", "auditoria"),
        (r"\b(implementar|gerar código|criar código|escrever|codificar)\b", "implementar"),
    ]

    def route(self, user_input: str, context: dict | None = None) -> Literal["plano", "auditoria", "implementar", "indeciso"]:
        """
        Roteia input para skill apropriada.

        Args:
            user_input: Input do usuário
            context: Contexto adicional (arquivos, etc.)

        Returns:
            Skill selecionada ou "indeciso"
        """
        if not user_input:
            return "indeciso"

        input_lower = user_input.lower()

        # Tenta cada padrão
        for pattern, skill in self.PATTERNS:
            if re.search(pattern, input_lower):
                return skill

        # Nenhum padrão bateu
        return "indeciso"

    def route_batch(self, inputs: list[str]) -> list[Literal["plano", "auditoria", "implementar", "indeciso"]]:
        """
        Roteia múltiplos inputs em batch.

        Args:
            inputs: Lista de inputs

        Returns:
            Lista de skills
        """
        return [self.route(inp) for inp in inputs]


# Instância singleton
router = Router()
