"""Base provider interface and registry for LLM backends."""

from abc import ABC, abstractmethod
from typing import Dict, Optional

from openai import OpenAI


class BaseProvider(ABC):
    """Interface para todos os providers de LLM.

    Todo provider deve ser capaz de:
    - Retornar um cliente OpenAI-compatível
    - Informar se está disponível (health check)
    """

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
