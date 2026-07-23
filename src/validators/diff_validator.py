"""Diff sanity checker: validates that changes are within allowed boundaries."""
from __future__ import annotations

import re
import time

from .base import BaseValidator, ValidationContext, ValidationResult, ValidationStatus


class DiffValidator(BaseValidator):
    """Valida que o diff gerado pelo executor está dentro dos limites esperados.

    Verificações:
    1. Apenas arquivos permitidos foram alterados
    2. Nenhum arquivo proibido foi modificado
    3. Tamanho do diff está dentro de limites razoáveis
    4. Não há padrões suspeitos (ex: credentials hardcoded, rm -rf)
    """

    name = "diff"

    # Padrões suspeitos que devem gerar warning ou falha
    SUSPICIOUS_PATTERNS = [
        (r"(?i)(api[_-]?key|secret|password|token)\s*[:=]\s*['\"][^'\"]{8,}", "Possível credencial hardcoded"),
        (r"rm\s+-rf\s+/", "Comando destrutivo detectado"),
        (r"(?i)DROP\s+(TABLE|DATABASE)", "Operação destrutiva de banco de dados"),
        (r"eval\s*\(", "Uso de eval() — risco de injeção"),
        (r"exec\s*\(", "Uso de exec() — risco de injeção"),
    ]

    def __init__(
        self,
        allowed_files: list[str] | None = None,
        forbidden_files: list[str] | None = None,
        max_diff_lines: int = 500,
    ):
        self.allowed_files = allowed_files
        self.forbidden_files = forbidden_files or []
        self.max_diff_lines = max_diff_lines

    def validate(self, context: ValidationContext) -> ValidationResult:
        start = time.monotonic()
        issues: list[str] = []

        if not context.diff:
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.SKIPPED,
                message="Nenhum diff fornecido para validação",
                duration_ms=(time.monotonic() - start) * 1000,
            )

        # 1. Extrair arquivos alterados do diff
        changed_in_diff = self._extract_changed_files(context.diff)

        # 2. Verificar arquivos permitidos
        if self.allowed_files is not None:
            allowed_set = set(self.allowed_files)
            unexpected = [f for f in changed_in_diff if f not in allowed_set]
            if unexpected:
                issues.append(f"Arquivos não permitidos alterados: {unexpected}")

        # 3. Verificar arquivos proibidos
        if self.forbidden_files:
            forbidden_set = set(self.forbidden_files)
            violated = [f for f in changed_in_diff if f in forbidden_set]
            if violated:
                issues.append(f"Arquivos proibidos modificados: {violated}")

        # 4. Verificar tamanho do diff
        diff_lines = context.diff.splitlines()
        if len(diff_lines) > self.max_diff_lines:
            issues.append(
                f"Diff muito grande ({len(diff_lines)} linhas > máximo {self.max_diff_lines})"
            )

        # 5. Verificar padrões suspeitos
        suspicious_found: list[str] = []
        for pattern, description in self.SUSPICIOUS_PATTERNS:
            if re.search(pattern, context.diff):
                suspicious_found.append(description)
        if suspicious_found:
            issues.append(f"Padrões suspeitos detectados: {suspicious_found}")

        duration_ms = (time.monotonic() - start) * 1000

        if issues:
            return ValidationResult(
                validator_name=self.name,
                status=ValidationStatus.FAILED,
                message="; ".join(issues),
                details={
                    "changed_files": changed_in_diff,
                    "diff_line_count": len(diff_lines),
                    "issues": issues,
                },
                duration_ms=duration_ms,
            )

        return ValidationResult(
            validator_name=self.name,
            status=ValidationStatus.PASSED,
            message=f"Diff válido: {len(changed_in_diff)} arquivo(s), {len(diff_lines)} linha(s)",
            details={
                "changed_files": changed_in_diff,
                "diff_line_count": len(diff_lines),
            },
            duration_ms=duration_ms,
        )

    @staticmethod
    def _extract_changed_files(diff: str) -> list[str]:
        """Extrai nomes de arquivos de um unified diff."""
        files = set()
        for line in diff.splitlines():
            # Unified diff: +++ b/path/to/file ou --- a/path/to/file
            if line.startswith("+++ b/") or line.startswith("--- a/"):
                path = line[6:] if line.startswith("+++ b/") else line[6:]
                # Remover prefixo a/ ou b/
                if path.startswith(("a/", "b/")):
                    path = path[2:]
                if path and path != "/dev/null":
                    files.add(path)
        return sorted(files)
