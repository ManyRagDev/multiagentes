"""Teste Fase 6.0: WorktreeManager com cenarios reais.

Valida:
1. Criacao e descarte de worktree
2. Aplicacao de output (full_file e diff)
3. Coleta de diff entre worktree e original
4. Merge de alteracoes
5. Reset de arquivos para retry
6. Integracao com ExecutionLoop
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.schemas.contract import TaskContract
from src.tools.worktree import WorktreeManager


TEMPDIR = Path(__file__).parent.parent / "logs" / "worktree_test"
TEMPDIR.mkdir(parents=True, exist_ok=True)


def banner(title: str):
    print(f"\n{'='*60}")
    print(f"  {title}")
    print('='*60)


def setup_test_project():
    """Cria um mini-projeto para teste de worktree."""
    project = TEMPDIR / "testproject"
    if project.exists():
        import shutil
        shutil.rmtree(project, ignore_errors=True)

    (project / "src").mkdir(parents=True)
    (project / "src" / "math.py").write_text(
        "def add(a, b):\n    return a + b\n\n"
        "def subtract(a, b):\n    return a - b\n",
        encoding="utf-8",
    )
    (project / "src" / "__init__.py").write_text("", encoding="utf-8")
    return project


def test_lifecycle():
    """Teste 1: Criar worktree, aplicar output, coletar diff, merge, descartar."""
    banner("TESTE 1: Ciclo de vida completo")

    project = setup_test_project()
    wm = WorktreeManager(project)

    code = "def add(a, b):\n    \"\"\"Soma dois numeros.\"\"\"\n    return a + b\n"
    allowed = ["src/math.py"]

    try:
        wm._create(allowed)
        assert wm.active
        assert wm.worktree_path is not None
        print(f"  [OK] Worktree criado: {wm.worktree_path}")

        wm.apply_output(code, allowed)

        wt_file = wm.worktree_path / "src/math.py"
        content = wt_file.read_text(encoding="utf-8")
        assert "Soma dois numeros" in content
        print("  [OK] Output aplicado ao worktree")

        diff = wm.collect_diff(allowed)
        assert "Soma dois numeros" in diff
        print(f"  [OK] Diff coletado ({len(diff)} chars)")

        modified = wm.merge(allowed)
        assert "src/math.py" in modified
        print(f"  [OK] Merge: {modified}")

        real_content = (project / "src/math.py").read_text(encoding="utf-8")
        assert "Soma dois numeros" in real_content
        print("  [OK] Arquivo real modificado")

        wm._session_active = False
        wm._worktree = None

        return True
    except AssertionError as e:
        print(f"  [ERRO] {e}")
        wm.discard()
        return False
    except Exception as e:
        print(f"  [ERRO] Excecao: {e}")
        wm.discard()
        return False


def test_diff_output():
    """Teste 2: Aplicar output em formato diff."""
    banner("TESTE 2: Output em formato diff")

    project = setup_test_project()
    wm = WorktreeManager(project)

    diff_output = (
        "--- a/src/math.py\n"
        "+++ b/src/math.py\n"
        "@@ -1,2 +1,4 @@\n"
        " def add(a, b):\n"
        "+    \"\"\"Soma dois numeros.\"\"\"\n"
        "     return a + b\n"
        "+    \n"
    )
    allowed = ["src/math.py"]

    try:
        wm._create(allowed)
        wm.apply_output(diff_output, allowed)

        wt_file = wm.worktree_path / "src/math.py"
        content = wt_file.read_text(encoding="utf-8")
        assert "Soma dois numeros" in content
        print("  [OK] Diff aplicado corretamente")

        wm.discard()
        assert not wm.active
        print("  [OK] Worktree descartado sem afetar original")

        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        wm.discard()
        return False


def test_multiple_files():
    """Teste 3: Worktree com multiplos arquivos."""
    banner("TESTE 3: Multiplos arquivos")

    project = setup_test_project()
    (project / "src" / "utils.py").write_text(
        "def helper():\n    return True\n", encoding="utf-8"
    )

    wm = WorktreeManager(project)
    allowed = ["src/math.py", "src/utils.py"]

    try:
        wm._create(allowed)

        wm.apply_output(
            "def add(a, b):\n    return a + b + 1\n", ["src/math.py"]
        )
        wm.apply_output(
            "def helper():\n    return False\n", ["src/utils.py"]
        )

        diff = wm.collect_diff(allowed)
        assert "src/math.py" in diff
        assert "src/utils.py" in diff
        print(f"  [OK] Diff inclui {diff.count('---') // 2} arquivos")

        modified = wm.merge(allowed)
        assert len(modified) == 2
        print(f"  [OK] {len(modified)} arquivos merged")

        wm._session_active = False
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        wm.discard()
        return False


def test_reset_on_retry():
    """Teste 4: Reset de arquivos no worktree entre retries."""
    banner("TESTE 4: Reset para retry")

    project = setup_test_project()
    wm = WorktreeManager(project)
    allowed = ["src/math.py"]

    try:
        wm._create(allowed)

        bad_code = "def add(a, b):\n    BUG_AQUI\n    return a + b\n"
        wm.apply_output(bad_code, allowed)

        wt_file = wm.worktree_path / "src/math.py"
        assert "BUG_AQUI" in wt_file.read_text(encoding="utf-8")
        print("  [OK] Output buggy aplicado")

        wm._reset_files(allowed)
        restored = wt_file.read_text(encoding="utf-8")
        assert "BUG_AQUI" not in restored
        assert "return a + b" in restored
        print("  [OK] Arquivos resetados para original")

        wm.discard()
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        wm.discard()
        return False


def test_unchanged_no_merge():
    """Teste 5: Merge nao deve ocorrer se nada mudou."""
    banner("TESTE 5: Merge sem alteracoes")

    project = setup_test_project()
    wm = WorktreeManager(project)
    allowed = ["src/math.py"]

    try:
        wm._create(allowed)
        modified = wm.merge(allowed)
        assert len(modified) == 0
        print("  [OK] Nenhum merge para arquivos nao alterados")

        diff = wm.collect_diff(allowed)
        assert diff == "" or "return a + b" not in diff  # sem diff real
        print("  [OK] Diff vazio para arquivos nao alterados")

        wm._session_active = False
        return True
    except Exception as e:
        print(f"  [ERRO] {e}")
        wm.discard()
        return False


def test_execution_loop_integration():
    """Teste 6: ExecutionLoop com worktree (sem LLM, usando mock executor)."""
    banner("TESTE 6: ExecutionLoop + Worktree (mock)")

    project = setup_test_project()
    wm = WorktreeManager(project)

    from unittest.mock import MagicMock
    from src.orchestration.execution_loop import (
        ExecutionLoop, ExecutionStatus
    )
    from src.validators.pipeline import ValidationPipeline

    mock_router = MagicMock()
    mock_classification = MagicMock()
    mock_classification.risk_score = 0
    mock_classification.complexity_score = 1
    mock_classification.tier = "local"
    mock_router.route.return_value = ("local-qwen", mock_classification)

    # Pipeline sem command validators (worktree nao tem linter/testes)
    silent_pipeline = ValidationPipeline(validators=[])

    loop = ExecutionLoop(
        router=mock_router,
        worktree=wm,
        project_root=str(project),
        validation_pipeline=silent_pipeline,
        max_attempts_default=2,
        max_cost_per_task=10.0,
    )

    contract = TaskContract(
        task_id="wt-001",
        objective="Adicionar docstring na funcao add em src/math.py",
        tier="local",
        allowed_files=["src/math.py"],
        constraints=[],
        acceptance_criteria=[],
        risk="low",
        max_attempts=2,
    )

    mock_executor = MagicMock()
    mock_executor.provider_name = "local-qwen"
    mock_result = MagicMock()
    mock_result.success = True
    mock_result.output = (
        "def add(a, b):\n"
        "    \"\"\"Soma dois numeros.\"\"\"\n"
        "    return a + b\n"
    )
    mock_result.tokens_used = 50
    mock_result.cost = 0.0
    mock_result.model = "qwen-local"
    mock_result.error = None
    mock_result.metadata = {"raw_output_length": 100, "clean_output_length": 80}
    mock_executor.execute_raw.return_value = mock_result

    loop._default_executor = mock_executor

    try:
        result = loop.execute(contract)

        print(f"  Status: {result.status.value}")
        print(f"  Modified: {result.modified_files}")
        print(f"  Attempts: {result.attempts_used}")
        print(f"  Tokens: {result.total_tokens}")

        if result.status == ExecutionStatus.MERGED:
            real_content = (project / "src/math.py").read_text(encoding="utf-8")
            assert "Soma dois numeros" in real_content
            print("  [OK] Codigo merged no projeto real")
            return True
        else:
            print(f"  [ERRO] Status esperado=merged, obtido={result.status.value}")
            return False

    except Exception as e:
        print(f"  [ERRO] {e}")
        if wm.active:
            wm.discard()
        return False
    finally:
        if wm.active:
            wm._session_active = False
            wm._worktree = None


def main():
    print("=" * 60)
    print("  WORKTREE — Fase 6.0: Execucao Isolada")
    print("=" * 60)

    results = {
        "lifecycle": test_lifecycle(),
        "diff_output": test_diff_output(),
        "multiple_files": test_multiple_files(),
        "reset_on_retry": test_reset_on_retry(),
        "unchanged_no_merge": test_unchanged_no_merge(),
        "loop_integration": test_execution_loop_integration(),
    }

    banner("RESUMO")
    passed = sum(1 for v in results.values() if v)
    for name, ok in results.items():
        print(f"  {'[OK]' if ok else '[FALHA]'} {name}")

    print(f"\n  Total: {passed}/{len(results)}")

    # Limpeza
    import shutil
    shutil.rmtree(TEMPDIR, ignore_errors=True)

    if passed == len(results):
        print("\n  Fase 6.0 validada!")
        sys.exit(0)
    else:
        print("\n  Alguns testes falharam.")
        sys.exit(1)


if __name__ == "__main__":
    main()
