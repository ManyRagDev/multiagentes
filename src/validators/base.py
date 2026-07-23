"""Base validator interface and result types."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class ValidationStatus(str, Enum):
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class ValidationResult:
    """Resultado de uma validação determinística."""

    validator_name: str
    status: ValidationStatus
    message: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    duration_ms: float = 0.0

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASSED

    def to_dict(self) -> dict[str, Any]:
        return {
            "validator": self.validator_name,
            "status": self.status.value,
            "message": self.message,
            "details": self.details,
            "duration_ms": round(self.duration_ms, 2),
        }


class BaseValidator(ABC):
    """Interface para todos os validadores determinísticos."""

    name: str = "base"

    @abstractmethod
    def validate(self, context: ValidationContext) -> ValidationResult:
        """Executa a validação e retorna o resultado."""
        ...

    def is_applicable(self, context: ValidationContext) -> bool:
        """Verifica se este validador se aplica ao contexto atual."""
        return True


@dataclass
class ValidationContext:
    """Contexto passado para cada validador."""

    # Arquivos alterados pelo patch
    changed_files: list[str] = field(default_factory=list)

    # Diretório raiz do projeto alvo
    project_root: str = ""

    # Stack detectada ou configurada
    stack: str = ""  # "python", "typescript", "javascript", "auto"

    # Comandos de validação customizados (override por projeto)
    custom_commands: dict[str, str] = field(default_factory=dict)

    # Diff gerado pelo executor
    diff: str = ""

    # Output schema esperado (para validação de estrutura)
    expected_schema: type | None = None

    # Dados produzidos pelo executor (para validação de schema)
    output_data: Any = None

    # Timeout máximo por comando (segundos)
    command_timeout: int = 60
