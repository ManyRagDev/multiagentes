"""Provider registry initialization.

Registra todos os providers disponíveis no sistema.
O BaseAgent usa o ProviderRegistry para resolver providers por nome.
"""

from .base import BaseProvider, ProviderRegistry
from .local_qwen import LocalQwenProvider

# Registra o provider local com configuração padrão
ProviderRegistry.register("local-qwen", LocalQwenProvider())

__all__ = ["BaseProvider", "ProviderRegistry", "LocalQwenProvider"]
