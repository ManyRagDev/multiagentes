"""Provider registry initialization.

Registra todos os providers disponíveis no sistema.
O BaseAgent usa o ProviderRegistry para resolver providers por nome.
"""

from .base import BaseProvider, ProviderRegistry, RemoteProvider
from .local_qwen import LocalQwenProvider

ProviderRegistry.register("local-qwen", LocalQwenProvider())

ProviderRegistry.register(
    "glm",
    RemoteProvider("glm", "ZAI", default_model="glm-5.2"),
)
ProviderRegistry.register(
    "deepseek",
    RemoteProvider("deepseek", "DEEPSEEK", default_model="deepseek-v4-pro"),
)
ProviderRegistry.register(
    "groq",
    RemoteProvider("groq", "GROQ", default_model="gpt-oss-120b"),
)

__all__ = ["BaseProvider", "ProviderRegistry", "LocalQwenProvider", "RemoteProvider"]
