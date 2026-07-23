"""Deterministic command-based validator (lint, typecheck, test, build)."""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .base import BaseValidator, ValidationContext, ValidationResult, ValidationStatus
from .stack_detector import detect_stack, get_validation_commands


class CommandValidator(BaseValidator):
    """Executa comandos de validação determinísticos baseados na stack.

    Suporta:
    - Comandos padrão por stack (auto-detectada)
    - Override via custom_commands no contexto
    - Timeout configurável por comando
    - Captura de stdout/stderr para feedback ao executor
    """

    name = "command"

    def __init__(self, command_type: str = "lint"):
        """
        Args:
            command_type: "lint", "typecheck", "test", "build", "format_check"
        """
        self.command_type = command_type

    def validate(self, context: ValidationContext) -> ValidationResult:
        start = time.monotonic()

        # Determinar stack
        stack = context.stack or detect_stack(context.project_root)

        # Obter comando: custom override > padrão da stack
        cmd_template = context.custom_commands.get(
            self.command_type,
            get_validation_commands(stack).get(self.command_type, ""),
        )

        if not cmd_template:
            return ValidationResult(
                validator_name=f"{self.name}:{self.command_type}",
                status=ValidationStatus.SKIPPED,
                message=f"Nenhum comando '{self.command_type}' definido para stack '{stack}'",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        # Substituir {files} pelos arquivos alterados
        # Filtrar apenas arquivos que EXISTEM no disco para evitar hangs
        existing_files = []
        root = Path(context.project_root) if context.project_root else Path.cwd()
        for f in context.changed_files:
            full_path = root / f
            if full_path.exists():
                existing_files.append(f)

        if not existing_files and context.changed_files:
            # Nenhum arquivo existe → skip validação de comando
            return ValidationResult(
                validator_name=f"{self.name}:{self.command_type}",
                status=ValidationStatus.SKIPPED,
                message=f"Arquivos não encontrados no disco: {context.changed_files[:3]}",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        files_str = " ".join(existing_files) if existing_files else "."
        cmd = cmd_template.replace("{files}", files_str)

        # Executar comando
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=context.command_timeout,
                cwd=str(root),
            )

            duration_ms = (time.monotonic() - start) * 1000

            if result.returncode == 0:
                return ValidationResult(
                    validator_name=f"{self.name}:{self.command_type}",
                    status=ValidationStatus.PASSED,
                    message=f"'{self.command_type}' passou",
                    details={
                        "command": cmd,
                        "stdout_lines": len(result.stdout.splitlines()),
                    },
                    duration_ms=duration_ms,
                )
            else:
                # Capturar últimas N linhas do stderr/stdout para feedback útil
                stderr_tail = "\n".join(result.stderr.strip().splitlines()[-20:])
                stdout_tail = "\n".join(result.stdout.strip().splitlines()[-10:])
                error_output = stderr_tail or stdout_tail

                return ValidationResult(
                    validator_name=f"{self.name}:{self.command_type}",
                    status=ValidationStatus.FAILED,
                    message=f"'{self.command_type}' falhou (exit code {result.returncode})",
                    details={
                        "command": cmd,
                        "exit_code": result.returncode,
                        "error_output": error_output[:2000],  # Limitar tamanho
                    },
                    duration_ms=duration_ms,
                )

        except subprocess.TimeoutExpired:
            duration_ms = (time.monotonic() - start) * 1000
            return ValidationResult(
                validator_name=f"{self.name}:{self.command_type}",
                status=ValidationStatus.ERROR,
                message=f"'{self.command_type}' excedeu timeout de {context.command_timeout}s",
                details={"command": cmd, "timeout": context.command_timeout},
                duration_ms=duration_ms,
            )
        except Exception as e:
            duration_ms = (time.monotonic() - start) * 1000
            return ValidationResult(
                validator_name=f"{self.name}:{self.command_type}",
                status=ValidationStatus.ERROR,
                message=f"Erro ao executar '{self.command_type}': {e}",
                details={"command": cmd, "error": str(e)},
                duration_ms=duration_ms,
            )
