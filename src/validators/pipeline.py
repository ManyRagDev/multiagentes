"""Validation pipeline: orchestrates multiple validators with budget awareness."""
from __future__ import annotations

import time
from typing import Any

from .base import BaseValidator, ValidationContext, ValidationResult, ValidationStatus
from .command_runner import CommandValidator
from .diff_validator import DiffValidator
from .schema_validator import SchemaValidator


class ValidationPipeline:
    """Pipeline de validação determinística.

    Executa validadores em ordem e para no primeiro FAILED (fail-fast).
    Validadores com status SKIPPED ou ERROR não interrompem o pipeline,
    mas são registrados no resultado final.

    A ordem padrão é:
    1. Schema (mais barato, valida estrutura)
    2. Diff (barato, valida limites)
    3. Lint (rápido, valida sintaxe/estilo)
    4. Typecheck (moderado, valida tipos)
    5. Test (mais caro, valida comportamento)
    6. Build (mais caro, valida compilação)
    """

    def __init__(
        self,
        validators: list[BaseValidator] | None = None,
        fail_fast: bool = True,
    ):
        self.validators = validators if validators is not None else self._default_validators()
        self.fail_fast = fail_fast

    @staticmethod
    def _default_validators() -> list[BaseValidator]:
        """Conjunto padrão de validadores para o MVP."""
        return [
            SchemaValidator(),
            DiffValidator(),
            CommandValidator("lint"),
            CommandValidator("typecheck"),
            CommandValidator("test"),
        ]

    def run(self, context: ValidationContext) -> PipelineResult:
        """Executa todos os validadores aplicáveis e retorna o resultado agregado."""
        start = time.monotonic()
        results: list[ValidationResult] = []
        overall_status = ValidationStatus.PASSED

        for validator in self.validators:
            # Pular validadores não aplicáveis
            if not validator.is_applicable(context):
                results.append(
                    ValidationResult(
                        validator_name=validator.name,
                        status=ValidationStatus.SKIPPED,
                        message="Validador não aplicável ao contexto",
                    )
                )
                continue

            result = validator.validate(context)
            results.append(result)

            # Fail-fast: parar no primeiro FAILED
            if result.status == ValidationStatus.FAILED and self.fail_fast:
                overall_status = ValidationStatus.FAILED
                break

            # ERROR não para o pipeline, mas marca como falha
            if result.status == ValidationStatus.ERROR:
                overall_status = ValidationStatus.ERROR

        duration_ms = (time.monotonic() - start) * 1000

        # Se nenhum validador falhou mas houve erro, status é ERROR
        if overall_status == ValidationStatus.PASSED:
            has_errors = any(r.status == ValidationStatus.ERROR for r in results)
            if has_errors:
                overall_status = ValidationStatus.ERROR

        return PipelineResult(
            status=overall_status,
            results=results,
            total_duration_ms=duration_ms,
        )


class PipelineResult:
    """Resultado agregado de uma execução do pipeline."""

    def __init__(
        self,
        status: ValidationStatus,
        results: list[ValidationResult],
        total_duration_ms: float,
    ):
        self.status = status
        self.results = results
        self.total_duration_ms = total_duration_ms

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASSED

    @property
    def failed_results(self) -> list[ValidationResult]:
        return [r for r in self.results if r.status == ValidationStatus.FAILED]

    @property
    def error_results(self) -> list[ValidationResult]:
        return [r for r in self.results if r.status == ValidationStatus.ERROR]

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status.value,
            "total_duration_ms": round(self.total_duration_ms, 2),
            "validators": [r.to_dict() for r in self.results],
            "failed_count": len(self.failed_results),
            "error_count": len(self.error_results),
        }

    def summary(self) -> str:
        """Resumo legível para logs e feedback ao executor."""
        lines = [f"Pipeline: {self.status.value} ({self.total_duration_ms:.0f}ms)"]
        for r in self.results:
            icon = {"passed": "✅", "failed": "❌", "skipped": "⏭️", "error": "⚠️"}
            lines.append(f"  {icon.get(r.status.value, '?')} {r.validator_name}: {r.message}")
        return "\n".join(lines)
