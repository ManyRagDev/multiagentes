"""Agente base - classe fundamental para todos os agentes."""

import os
import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import TypeVar, Type, Any, Dict, Generic
from openai import OpenAI
from pydantic import BaseModel

from src.schemas.agent import AgentConfig, AgentOutput
from src.providers import ProviderRegistry


T = TypeVar('T', bound=BaseModel)


class BaseAgent(ABC, Generic[T]):
    """
    Classe base para todos os agentes.

    Cada agente especializado deve herdar desta classe e implementar:
    - get_prompt(): Formatar o prompt para o modelo
    - parse_output(): Converter a resposta para o schema Pydantic
    """

    def __init__(
        self,
        config: AgentConfig,
        client: OpenAI | None = None,
        base_dir: str | None = None
    ):
        """
        Inicializa o agente.

        Args:
            config: Configuração do agente
            client: Cliente OpenAI (opcional, cria um padrão)
            base_dir: Diretório base para prompts (opcional)
        """
        self.config = config
        self.base_dir = base_dir or str(Path(__file__).parent.parent.parent)

        # Cliente OpenAI (compatível com qualquer API compatível)
        if client is None:
            # Tentar resolver via provider registrado
            provider_name = getattr(config, 'provider', None)
            if provider_name and ProviderRegistry.has(provider_name):
                provider = ProviderRegistry.get(provider_name)
                # Garante que providers locais estão prontos
                if hasattr(provider, 'ensure_ready'):
                    provider.ensure_ready()
                self.client = provider.get_client()
            else:
                # Fallback: API remota padrão
                api_key = os.getenv("ZAI_API_KEY") or os.getenv("OPENAI_API_KEY")
                base_url = os.getenv("ZAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
                self.client = OpenAI(api_key=api_key, base_url=base_url)
        else:
            self.client = client

        # Cache do prompt
        self._prompt_template: str | None = None

    def load_prompt(self) -> str:
        """
        Carrega o template do prompt.

        Tenta carregar do arquivo especificado na config.
        Se não existir, usa prompt_template se disponível.
        """
        if self._prompt_template is not None:
            return self._prompt_template

        # Tentar carregar do arquivo
        if self.config.prompt_file:
            prompt_path = Path(self.base_dir) / self.config.prompt_file
            if prompt_path.exists():
                with open(prompt_path, 'r', encoding='utf-8') as f:
                    self._prompt_template = f.read()
                    return self._prompt_template

        # Usar template direto
        if self.config.prompt_template:
            self._prompt_template = self.config.prompt_template
            return self._prompt_template

        raise ValueError(
            f"Prompt não encontrado para {self.config.nome}. "
            f"Especifique prompt_file ou prompt_template."
        )

    def format_prompt(self, **kwargs) -> str:
        """
        Formata o prompt com as variáveis fornecidas.

        Args:
            **kwargs: Variáveis para substituir no prompt

        Returns:
            Prompt formatado
        """
        template = self.load_prompt()

        # Substituir variáveis no formato {{var}}
        for key, value in kwargs.items():
            placeholder = f"{{{{{key}}}}}"
            template = template.replace(placeholder, str(value))

        return template

    @abstractmethod
    def get_output_schema(self) -> Type[T]:
        """
        Retorna o schema Pydantic do output.

        Returns:
            Tipo Pydantic do output
        """
        pass

    def parse_output(self, raw: str) -> T:
        """
        Parseia a resposta bruta para o schema Pydantic.

        Args:
            raw: Resposta bruta do modelo

        Returns:
            Objeto Pydantic parseado
        """
        # Limpar markdown code blocks
        cleaned = raw.strip()
        if cleaned.startswith('```'):
            # Remover ```json ou ``` no início
            lines = cleaned.split('\n')
            if lines[0].startswith('```'):
                lines = lines[1:]
            # Remover ``` no final
            if lines and lines[-1].startswith('```'):
                lines = lines[:-1]
            cleaned = '\n'.join(lines)

        cleaned = cleaned.strip()

        # Parsear JSON
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError as e:
            raise ValueError(
                f"Resposta não é JSON válido: {e}\n\nResposta bruta:\n{raw[:500]}"
            )

        # Validar com schema Pydantic
        schema = self.get_output_schema()
        try:
            return schema(**data)
        except Exception as e:
            raise ValueError(
                f"Resposta não valida com schema {schema.__name__}: {e}\n\n"
                f"Dados recebidos:\n{json.dumps(data, indent=2)[:500]}"
            )

    def run(self, **kwargs) -> AgentOutput:
        """
        Executa o agente.

        Args:
            **kwargs: Variáveis para o prompt

        Returns:
            AgentOutput com resultado ou erro
        """
        try:
            # Formatar prompt
            prompt = self.format_prompt(**kwargs)

            # Chamar modelo
            response = self.client.chat.completions.create(
                model=self.config.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                temperature=self.config.temperature
            )

            # Extrair resposta
            raw_output = response.choices[0].message.content

            # Parsear para schema
            parsed_output = self.parse_output(raw_output)

            # Token usage se disponível
            tokens_usados = None
            if hasattr(response, 'usage') and response.usage:
                tokens_usados = response.usage.total_tokens

            return AgentOutput(
                agente=self.config.nome,
                sucesso=True,
                output=parsed_output.model_dump(),
                raw_output=raw_output,
                erro=None,
                tokens_usados=tokens_usados
            )

        except Exception as e:
            return AgentOutput(
                agente=self.config.nome,
                sucesso=False,
                output=None,
                raw_output=None,
                erro=str(e),
                tokens_usados=None
            )

    def run_with_retry(
        self,
        max_retries: int = 3,
        **kwargs
    ) -> AgentOutput:
        """
        Executa o agente com retry em caso de falha.

        Args:
            max_retries: Número máximo de tentativas
            **kwargs: Variáveis para o prompt

        Returns:
            AgentOutput com resultado ou erro
        """
        last_error = None

        for attempt in range(max_retries):
            result = self.run(**kwargs)
            if result.sucesso:
                return result

            last_error = result.erro
            # Não retry em erros de validação (não vai mudar)
            if "JSON" in str(last_error) or "schema" in str(last_error):
                return result

        # Retornar última falha
        return AgentOutput(
            agente=self.config.nome,
            sucesso=False,
            output=None,
            raw_output=None,
            erro=f"Após {max_retries} tentativas: {last_error}",
            tokens_usados=None
        )
