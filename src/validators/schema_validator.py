"""Schema validation for agent outputs using Pydantic."""
from __future__ import annotations

import time
from typing import Any

from pydantic import BaseModel, ValidationError

from .base import BaseValidator, ValidationContext, ValidationResult, ValidationStatus


class SchemaValidator(BaseValidator):
    """Valida que a saída do executor conforma ao schema Pydantic esperado.

    Este validador é crucial para garantir que o Qwen local produziu
    uma resposta estruturada correta antes de gastar tokens com revisão.
    """

    name = "schema"

    def validate(self, context: ValidationContext) -> ValidationResult:
        start = time.monotonic()

        if context.expected_schema is None:
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.SKIPPED,
                message="Nenhum schema esperado definido",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        if context.output_data is None:
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.FAILED,
                message="Nenhum dado de saída fornecido para validação de schema",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        try:
            # Se já é instância do modelo, validar via model_validate
            if isinstance(context.output_data, BaseModel):
                validated = context.expected_schema.model_validate(
                    context.output_data.model_dump()
                )
            elif isinstance(context.output_data, dict):
                validated = context.expected_schema.model_validate(context.output_data)
            else:
                return ValidationResult(
                    validator_name=self.name,
                    status=ValidationStatus.FAILED,
                    message=f"Tipo de dado não suportado: {type(context.output_data).__name__}",
                    duration_ms=(time.monotonic() - start) * 1000,
                )

            duration_ms = (time.monotonic() - start) * 1000
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.PASSED,
                message=f"Schema '{context.expected_schema.__name__}' válido",
                details={"schema": context.expected_schema.__name__},
                duration_ms=duration_ms,
            )

        except ValidationError as e:
            duration_ms = (time.monotonic() - start) * 1000
            errors = [
                {"field": ".".join(str(loc) for loc in err["loc"]), "message": err["msg"]}
                for err in e.errors()[:10]  # Limitar a 10 erros
            ]
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.FAILED,
                message=f"Validação de schema falhou: {len(e.errors())} erro(s)",
                details={
                    "schema": context.expected_schema.__name__,
                    "errors": errors,
                },
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.ERROR,
                message=f"Erro na validação de schema: {e}",
                details={"error": str(e)},
                duration_ms=duration_ms,
            )
