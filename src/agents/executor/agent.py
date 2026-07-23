"""ExecutorAgent: specialized agent for TaskContract execution.

Unlike BaseAgent subclasses that use prompt templates and parse JSON output,
ExecutorAgent receives a pre-built structured prompt from ExecutionLoop
and returns raw text (code/patch) without schema parsing.

This is the "arms" of the hybrid architecture — it executes well-defined
tasks delegated by the "brain" (planner API model).
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from openai import OpenAI

from src.providers import ProviderRegistry
from src.schemas.agent import AgentConfig

logger = logging.getLogger(__name__)


# Caminho do fragmento compartilhado de princípios (lido uma vez)
_PRINCIPLES_PATH = Path(__file__).parent.parent.parent / "prompts" / "_shared" / "principles.prompty"


@dataclass
class ExecutorResult:
    """Raw result from executor agent (no schema parsing)."""

    success: bool
    output: str = ""
    tokens_used: int = 0
    cost: float = 0.0
    provider: str = ""
    model: str = ""
    error: str = ""
    metadata: dict[str, Any] | None = None


class ExecutorAgent:
    """Agente executor especializado para TaskContracts.

    Diferente do BaseAgent:
    - Não usa prompt_file/prompt_template (recebe prompt pronto)
    - Não faz parse_output para schema Pydantic (retorna texto bruto)
    - Focado em gerar código/patch/diff como texto
    - Integrado com ProviderRegistry para roteamento por tier

    O ExecutionLoop constrói o prompt estruturado via _build_prompt()
    e passa diretamente para este agente.
    """

    # Custos aproximados por 1K tokens (input+output) para estimativa
    COST_PER_1K_TOKENS: dict[str, float] = {
        "local-qwen": 0.0,
        "groq": 0.0002,
        "deepseek": 0.0003,
        "glm": 0.0005,
    }

    def __init__(
        self,
        provider_name: str = "local-qwen",
        model: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 4096,
        system_prompt: str | None = None,
        timeout: float = 120.0,
    ):
        """
        Args:
            provider_name: Nome do provider no ProviderRegistry
            model: Override do modelo (se None, usa default do provider)
            temperature: Temperatura de geração
            max_tokens: Limite de tokens na resposta
            system_prompt: System prompt padrão para o executor
            timeout: Timeout em segundos para a chamada ao LLM (default 120s)
        """
        self.provider_name = provider_name
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.timeout = timeout
        self.system_prompt = system_prompt or self._default_system_prompt()

        # Resolver provider e criar cliente
        provider = ProviderRegistry.get(provider_name)
        if hasattr(provider, "ensure_ready"):
            provider.ensure_ready()
        self.client: OpenAI = provider.get_client()

        # Modelo: usar override ou tentar descobrir do provider
        self.model = model or self._resolve_model(provider_name)

    @classmethod
    def _default_system_prompt(cls) -> str:
        """System prompt padrão para o executor local.

        Combina princípios compartilhados (P1, P4, O2) com instruções
        específicas do Executor (P2, O1, minimalismo).
        """
        # Carrega princípios compartilhados (caching via classe)
        if not hasattr(cls, "_principles_cache"):
            try:
                content = _PRINCIPLES_PATH.read_text(encoding="utf-8")
                # Extrai só o corpo (pula o frontmatter YAML)
                if content.startswith("---"):
                    end = content.find("---", 3)
                    content = content[end + 3 :].strip() if end != -1 else content
                cls._principles_cache = content
            except FileNotFoundError:
                logger.warning(f"Principles não encontrado em {_PRINCIPLES_PATH}")
                cls._principles_cache = ""

        executor_specific = (
            "\n\n# P2 — Auto-auditoria antes de Emitir (Executor)\n"
            "Antes de emitir o código, revise mentalmente:\n"
            "1. Alterei APENAS os arquivos em `allowed_files`?\n"
            "2. Mantive as interfaces públicas que não foram solicitadas mudar?\n"
            "3. Meus imports existem e estão corretos?\n"
            "4. Segui o padrão de estilo do `context_snippets` fornecido?\n"
            "5. O output está no `output_format` solicitado (unified_diff/full_file/json)?\n\n"
            "Se qualquer resposta for 'não' ou 'não sei', emita `<self_check>` com "
            "`decision: needs_context` em vez de adivinhar.\n\n"
            "# O1 — Self-Check Estruturado\n"
            "Quando houver incerteza real, emita `<self_check>...</self_check>` "
            "ANTES do código, seguindo o formato do seu prompt.\n"
            "Quando não houver incerteza, emita APENAS o artefato — sem preâmbulo.\n\n"
            "# Instrução Final\n"
            "Seu output será parseado automaticamente. Qualquer texto fora de "
            "`<self_check>` e do fence de código (```lang ... ```) será descartado. "
            "Não escreva nada que você não queira perder."
        )

        return cls._principles_cache + executor_specific

    @staticmethod
    def extract_payload(raw_output: str) -> tuple[str, str | None, bool]:
        """Extrai o payload útil do output bruto do executor.

        Implementa parser tolerante aos princípios O1/O2:
        - Remove o bloco `<self_check>...</self_check>` (se presente) para metadata
        - Extrai o código/patch/diff dos fences de linguagem
        - Detecta sinalização de `needs_context`

        Args:
            raw_output: Texto bruto retornado pelo LLM

        Returns:
            (code_text, self_check_text_or_none, needs_context_flag)
        """
        # 1. Extrair self_check (se presente)
        self_check_pattern = re.compile(
            r"<self_check>(.*?)</self_check>",
            re.DOTALL | re.IGNORECASE,
        )
        self_check_match = self_check_pattern.search(raw_output)
        self_check_text: str | None = None
        needs_context = False

        if self_check_match:
            self_check_text = self_check_match.group(1).strip()
            needs_context = "needs_context" in self_check_text.lower()
            # Remove do texto para o passo seguinte
            working_text = (
                raw_output[: self_check_match.start()]
                + raw_output[self_check_match.end() :]
            )
        else:
            working_text = raw_output

        # 2. Extrair blocos fence de código (```lang ... ```)
        fence_pattern = re.compile(
            r"```([a-zA-Z0-9_+-]*)\n?(.*?)```",
            re.DOTALL,
        )
        fences = list(fence_pattern.finditer(working_text))

        if fences:
            # Concatena todos os blocos de código (útil quando há múltiplos arquivos)
            code_parts = []
            for m in fences:
                code_parts.append(m.group(2).rstrip())
            code_text = "\n\n".join(code_parts)
        else:
            # Fallback: usa o texto limpo (sem self_check) como código
            code_text = working_text.strip()

        return code_text, self_check_text, needs_context

    @staticmethod
    def _resolve_model(provider_name: str) -> str:
        """Resolve o nome do modelo baseado no provider."""
        model_map = {
            "local-qwen": "qwen2.5-coder-7b-instruct",
            "deepseek": "deepseek-chat",
            "glm": "glm-4-flash",
            "groq": "llama-3.3-70b-versatile",
        }
        return model_map.get(provider_name, "default")

    def execute_raw(self, prompt: str) -> ExecutorResult:
        """Executa o agente com um prompt pré-construído e retorna texto bruto.

        Este é o método principal chamado pelo ExecutionLoop.

        Args:
            prompt: Prompt estruturado completo (construído por ExecutionLoop._build_prompt)

        Returns:
            ExecutorResult com output bruto e metadados
        """
        try:
            messages = [
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt},
            ]

            logger.info(
                f"[ExecutorAgent] Chamando {self.provider_name}/{self.model} "
                f"(temp={self.temperature})"
            )

            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                timeout=self.timeout,
            )

            raw_output = response.choices[0].message.content or ""

            # Parse do payload (O1/O2): extrai código limpo + self_check
            code_text, self_check_text, needs_context = self.extract_payload(raw_output)

            # Token usage
            tokens = 0
            if hasattr(response, "usage") and response.usage:
                tokens = response.usage.total_tokens or 0

            # Estimativa de custo
            cost_per_1k = self.COST_PER_1K_TOKENS.get(self.provider_name, 0.0003)
            cost = (tokens / 1000) * cost_per_1k

            # Economia de tokens vs output bruto (métrica de eficácia do minimalismo)
            raw_len = len(raw_output)
            clean_len = len(code_text)
            saved_chars = raw_len - clean_len

            logger.info(
                f"[ExecutorAgent] ✅ Resposta parseada: "
                f"{raw_len}→{clean_len} chars (economia {saved_chars}), "
                f"{tokens} tokens, ${cost:.4f}, "
                f"needs_context={needs_context}"
            )

            return ExecutorResult(
                success=True,
                output=code_text,
                tokens_used=tokens,
                cost=cost,
                provider=self.provider_name,
                model=self.model,
                metadata={
                    "finish_reason": response.choices[0].finish_reason,
                    "self_check": self_check_text,
                    "needs_context": needs_context,
                    "raw_output_length": raw_len,
                    "clean_output_length": clean_len,
                },
            )

        except Exception as e:
            logger.error(f"[ExecutorAgent] ❌ Erro: {e}")
            return ExecutorResult(
                success=False,
                error=str(e),
                provider=self.provider_name,
                model=self.model,
            )

    def switch_provider(self, provider_name: str, model: str | None = None):
        """Troca o provider em tempo de execução (para escalonamento/fallback)."""
        provider = ProviderRegistry.get(provider_name)
        if hasattr(provider, "ensure_ready"):
            provider.ensure_ready()
        self.client = provider.get_client()
        self.provider_name = provider_name
        self.model = model or self._resolve_model(provider_name)
        logger.info(f"[ExecutorAgent] Provider trocado para {provider_name}/{self.model}")
