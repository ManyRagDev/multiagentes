"""Base provider interface and registry for LLM backends."""

import os
from abc import ABC, abstractmethod
from typing import Dict, Optional

from openai import OpenAI


class BaseProvider(ABC):
    """Interface para todos os providers de LLM."""

    @abstractmethod
    def get_client(self) -> OpenAI:
        """Retorna um cliente OpenAI-compatível configurado."""
        pass

    @abstractmethod
    def is_available(self) -> bool:
        """Verifica se o provider está disponível e respondendo."""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Nome identificador do provider."""
        pass


class RemoteProvider(BaseProvider):
    """Provider para APIs remotas (DeepSeek, GLM, Groq).

    Configurado via variáveis de ambiente:
    - {PREFIX}_API_KEY
    - {PREFIX}_BASE_URL (opcional)
    """

    def __init__(self, name: str, env_prefix: str, default_model: str = ""):
        self._name = name
        self.env_prefix = env_prefix
        self.default_model = default_model

    @property
    def name(self) -> str:
        return self._name

    def is_available(self) -> bool:
        return bool(
            os.getenv(f"{self.env_prefix}_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )

    def get_client(self) -> OpenAI:
        api_key = os.getenv(f"{self.env_prefix}_API_KEY") or os.getenv("OPENAI_API_KEY")
        base_url = os.getenv(f"{self.env_prefix}_BASE_URL")
        if not api_key:
            raise RuntimeError(
                f"Provider '{self._name}' requer {self.env_prefix}_API_KEY "
                f"ou OPENAI_API_KEY no ambiente"
            )
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        return OpenAI(**kwargs)


class ProviderRegistry:
    """Registro central de providers.

    Permite registrar, recuperar e listar providers por nome.
    Usado pelo BaseAgent para resolver providers dinamicamente.
    """

    _providers: Dict[str, BaseProvider] = {}

    @classmethod
    def register(cls, name: str, provider: BaseProvider) -> None:
        """Registra um provider com um nome identificador."""
        cls._providers[name] = provider

    @classmethod
    def get(cls, name: str) -> BaseProvider:
        """Recupera um provider pelo nome.

        Raises:
            ValueError: Se o provider não estiver registrado.
        """
        if name not in cls._providers:
            available = list(cls._providers.keys())
            raise ValueError(
                f"Provider '{name}' não registrado. "
                f"Disponíveis: {available}"
            )
        return cls._providers[name]

    @classmethod
    def list_providers(cls) -> list[str]:
        """Lista todos os providers registrados."""
        return list(cls._providers.keys())

    @classmethod
    def has(cls, name: str) -> bool:
        """Verifica se um provider está registrado."""
        return name in cls._providers
