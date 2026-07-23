"""
Suite de regressao unificada — Fase 5.5.

Roda todas as avaliacoes de prompts + enforcement em sequencia e produz um
relatorio consolidado. Serve como baseline para detectar regressoes futuras:
qualquer mudanca em prompts/schemas/enforcement deve rodar contra esta suite.

Uso:
    uv run python scripts/eval_prompts.py

Para salvar um baseline:
    uv run python scripts/eval_prompts.py > logs/regression_baseline_YYYY-MM-DD.txt
"""
import os
import subprocess
import sys
import time
from pathlib import Path


if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass



SCRIPTS = [
    ("Fase 5.1 — Executor", "scripts/eval_executor_prompts.py"),
    ("Fase 5.2 — Planner", "scripts/eval_planner_prompts.py"),
    ("Fase 5.3 — Reviewer", "scripts/eval_reviewer_prompts.py"),
    ("Fase 5.4 — Enforcement", "scripts/eval_enforcement.py"),
    ("Fase 6.4 — Pipeline E2E", "scripts/test_pipeline_e2e.py"),
]


def run_script(label: str, path: str) -> tuple[bool, float]:
    print(f"\n{'='*78}")
    print(f"  > {label}")
    print(f"  {path}")
    print('='*78)

    if not Path(path).exists():
        print(f"  [ERRO] Script nao encontrado: {path}")
        return False, 0.0

    start = time.time()
    try:
        env = os.environ.copy()
        env['PYTHONIOENCODING'] = 'utf-8'
        env['PYTHONUTF8'] = '1'
        result = subprocess.run(
            [sys.executable, path],
            capture_output=False,
            text=True,
            env=env,
        )
        elapsed = time.time() - start
        return result.returncode == 0, elapsed
    except Exception as e:
        elapsed = time.time() - start
        print(f"  [ERRO] Erro ao executar: {e}")
        return False, elapsed


def main():
    print("=" * 78)
    print("  SUITE DE REGRESSAO — Multi-Agentes Harness")
    print("  Fase 5.5 — Baseline para deteccao de regressoes")
    print("=" * 78)

    results = []
    total_time = 0.0

    for label, path in SCRIPTS:
        ok, elapsed = run_script(label, path)
        results.append((label, ok, elapsed))
        total_time += elapsed

    # Relatorio final
    print(f"\n{'='*78}")
    print("  RELATORIO DE REGRESSAO")
    print('='*78)

    all_ok = True
    for label, ok, elapsed in results:
        icon = "[OK]" if ok else "[FALHA]"
        print(f"  {icon} {label:<35} ({elapsed:.2f}s)")
        if not ok:
            all_ok = False

    passed_count = sum(1 for _, ok, _ in results if ok)
    print(f"\n  {'-'*70}")
    print(f"  Total: {passed_count}/{len(results)} suites passaram")
    print(f"  Tempo total: {total_time:.2f}s")

    if all_ok:
        print("\n  Nenhuma regressao detectada. Baseline saudavel.")
        print("\n  Para usar como baseline futura, salve este output em:")
        print("     logs/regression_baseline_YYYY-MM-DD.txt")
        sys.exit(0)
    else:
        print("\n  ATENCAO: Regressao detectada! Verifique suites com falha acima.")
        sys.exit(1)


if __name__ == "__main__":
    main()
