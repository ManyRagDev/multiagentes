"""Auto-detection of project stack based on file markers."""
from __future__ import annotations

from pathlib import Path


# Marcadores de stack: arquivo -> stack
_STACK_MARKERS: dict[str, str] = {
    # Python
    "pyproject.toml": "python",
    "setup.py": "python",
    "requirements.txt": "python",
    "Pipfile": "python",
    "uv.lock": "python",
    ".python-version": "python",
    # TypeScript / JavaScript
    "tsconfig.json": "typescript",
    "package.json": "javascript",  # pode ser TS ou JS; refinado abaixo
    "vite.config.ts": "typescript",
    "vite.config.js": "javascript",
    "next.config.ts": "typescript",
    "next.config.mjs": "javascript",
    "angular.json": "typescript",
    ".eslintrc.json": "javascript",
}

# Extensões que refinam a detecção
_TS_EXTENSIONS = {".ts", ".tsx", ".mts", ".cts"}
_JS_EXTENSIONS = {".js", ".jsx", ".mjs", ".cjs"}


def detect_stack(project_root: str) -> str:
    """Detecta a stack principal do projeto.

    Retorna: "python", "typescript", "javascript" ou "unknown".
    Prioridade: marcadores explícitos > extensão dos arquivos alterados.
    """
    root = Path(project_root)

    if not root.exists():
        return "unknown"

    # 1. Verificar marcadores de arquivo na raiz
    for marker, stack in _STACK_MARKERS.items():
        if (root / marker).exists():
            # Refinar javascript -> typescript se tsconfig existir
            if stack == "javascript" and (root / "tsconfig.json").exists():
                return "typescript"
            return stack

    # 2. Fallback: verificar extensões dos arquivos no diretório src/ ou raiz
    search_dirs = [root / "src", root]
    ts_count = 0
    js_count = 0
    py_count = 0

    for search_dir in search_dirs:
        if not search_dir.exists():
            continue
        for f in search_dir.iterdir():
            if f.is_file():
                if f.suffix in _TS_EXTENSIONS:
                    ts_count += 1
                elif f.suffix in _JS_EXTENSIONS:
                    js_count += 1
                elif f.suffix == ".py":
                    py_count += 1

    if ts_count > 0:
        return "typescript"
    if py_count > js_count and py_count > 0:
        return "python"
    if js_count > 0:
        return "javascript"

    return "unknown"


def get_validation_commands(stack: str) -> dict[str, str]:
    """Retorna os comandos de validação padrão para cada stack.

    Os comandos são templates; o orquestrador substitui {files} se necessário.
    """
    commands_by_stack: dict[str, dict[str, str]] = {
        "python": {
            "lint": "ruff check {files}",
            "typecheck": "mypy {files}",
            "test": "pytest {files} -x -q",
            "format_check": "ruff format --check {files}",
        },
        "typescript": {
            "lint": "npx eslint {files} --no-error-on-unmatched-pattern",
            "typecheck": "npx tsc --noEmit",
            "test": "npx vitest run --reporter=verbose {files}",
            "build": "npx tsc --noEmit && npx vite build",
        },
        "javascript": {
            "lint": "npx eslint {files} --no-error-on-unmatched-pattern",
            "test": "npx vitest run --reporter=verbose {files}",
            "build": "npx vite build",
        },
    }

    return commands_by_stack.get(stack, {})
