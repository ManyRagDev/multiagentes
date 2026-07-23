"""GitRollback — snapshot e rollback seguro via Git.

Fase 6.0 complemento: garante que alteracoes mal-sucedidas
possam ser revertidas atomicamente.
"""
from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


class GitRollback:
    """Gerencia snapshot e rollback usando Git."""

    def __init__(self, project_root: str | Path):
        self.project_root = Path(project_root).resolve()
        self._head_before: str = ""
        self._has_stash: bool = False
        self._available: bool = self._check_git()

    def _check_git(self) -> bool:
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--show-toplevel"],
                capture_output=True, text=True,
                cwd=str(self.project_root),
            )
            if result.returncode != 0:
                return False
            repo_root = Path(result.stdout.strip()).resolve()
            return repo_root == self.project_root
        except Exception:
            return False

    @property
    def available(self) -> bool:
        return self._available

    def snapshot(self) -> bool:
        if not self._available:
            return False
        try:
            head = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                capture_output=True, text=True,
                cwd=str(self.project_root),
            )
            if head.returncode != 0:
                return False
            self._head_before = head.stdout.strip()
            stash = subprocess.run(
                ["git", "stash", "push", "-m", "multiagentes-safety-snapshot"],
                capture_output=True, text=True,
                cwd=str(self.project_root),
            )
            self._has_stash = "Saved working directory" in stash.stdout
            logger.info("GitRollback: snapshot HEAD=%s", self._head_before[:8])
            return True
        except Exception as e:
            logger.warning("GitRollback snapshot error: %s", e)
            return False

    def rollback(self) -> bool:
        if not self._available or not self._head_before:
            return False
        try:
            subprocess.run(
                ["git", "reset", "--hard", self._head_before],
                capture_output=True, text=True,
                cwd=str(self.project_root),
            )
            subprocess.run(
                ["git", "clean", "-fd"],
                capture_output=True, text=True,
                cwd=str(self.project_root),
            )
            if self._has_stash:
                subprocess.run(
                    ["git", "stash", "pop"],
                    capture_output=True, text=True,
                    cwd=str(self.project_root),
                )
                self._has_stash = False
            logger.info("GitRollback: restored to %s", self._head_before[:8])
            return True
        except Exception as e:
            logger.error("GitRollback error: %s", e)
            return False

    def commit_safety(self, task_id: str) -> bool:
        if not self._available:
            return False
        try:
            subprocess.run(
                ["git", "add", "-A"],
                capture_output=True, text=True,
                cwd=str(self.project_root),
            )
            result = subprocess.run(
                ["git", "commit", "-m", f"multiagentes: {task_id}"],
                capture_output=True, text=True,
                cwd=str(self.project_root),
            )
            ok = result.returncode == 0
            if ok and self._has_stash:
                subprocess.run(
                    ["git", "stash", "drop"],
                    capture_output=True, text=True,
                    cwd=str(self.project_root),
                )
                self._has_stash = False
            return ok
        except Exception as e:
            logger.warning("GitRollback commit error: %s", e)
            return False
