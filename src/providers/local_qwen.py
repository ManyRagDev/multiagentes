"""Local Qwen provider via llama.cpp with auto-recovery.

Conecta-se ao llama-server rodando localmente e garante que ele esteja
operacional antes de cada chamada. Se o servidor não estiver respondendo,
inicia automaticamente o processo em background.
"""

import logging
import subprocess
import threading
import time
from pathlib import Path
from typing import Optional

import httpx
from openai import OpenAI

from .base import BaseProvider

logger = logging.getLogger(__name__)


class LocalQwenProvider(BaseProvider):
    """Provider para Qwen2.5-Coder-7B rodando em llama.cpp.

    Configuração padrão aponta para http://127.0.0.1:8080/v1.
    Suporta auto-recovery: se o servidor cair, reinicia automaticamente.
    """

    DEFAULT_CONFIG = {
        "base_url": "http://127.0.0.1:8080/v1",
        "health_endpoint": "http://127.0.0.1:8080/health",
        "startup_command": (
            r"cd c:\llama.cpp && llama-server.exe "
            r"-m models\qwen2.5-coder-7b-instruct-q4_k_m.gguf "
            r"-ngl 99 -c 8192 --port 8080"
        ),
        "startup_timeout": 45,
        "auto_restart": True,
        "api_key": "not-needed",
        "model_name": "qwen2.5-coder-7b-instruct",
    }

    def __init__(self, config: Optional[dict] = None):
        self.config = {**self.DEFAULT_CONFIG, **(config or {})}
        self._client: Optional[OpenAI] = None
        self._process: Optional[subprocess.Popen] = None
        self._lock = threading.Lock()
        self._starting = False

    @property
    def name(self) -> str:
        return "local-qwen"

    def get_client(self) -> OpenAI:
        """Retorna cliente OpenAI apontando para o llama-server local."""
        if self._client is None:
            self._client = OpenAI(
                api_key=self.config["api_key"],
                base_url=self.config["base_url"],
            )
        return self._client

    def is_available(self) -> bool:
        """Verifica se o llama-server está respondendo no health endpoint."""
        try:
            resp = httpx.get(self.config["health_endpoint"], timeout=2)
            return resp.status_code == 200
        except Exception:
            return False

    def ensure_ready(self) -> bool:
        """Garante que o servidor está pronto. Inicia se necessário.

        Returns:
            True se o servidor está operacional.

        Raises:
            RuntimeError: Se auto_restart está desativado e servidor está down.
            TimeoutError: Se o servidor não iniciou dentro do timeout.
        """
        if self.is_available():
            return True

        if not self.config["auto_restart"]:
            raise RuntimeError(
                f"Qwen local indisponível e auto_restart desativado. "
                f"Endpoint: {self.config['health_endpoint']}"
            )

        # Lock para evitar múltiplos starts simultâneos
        with self._lock:
            if self._starting:
                # Outro thread já está iniciando; aguarda
                start = time.time()
                while time.time() - start < self.config["startup_timeout"]:
                    if self.is_available():
                        return True
                    time.sleep(0.5)
                return False

            self._starting = True

        try:
            logger.warning("⚠️ Qwen local não respondendo. Iniciando llama-server...")

            # Extrair cwd do comando (parte antes do &&)
            cmd = self.config["startup_command"]
            cwd = None
            if "&&" in cmd:
                cd_part = cmd.split("&&")[0].strip()
                if cd_part.startswith("cd "):
                    cwd = cd_part[3:].strip()

            # Preparar log file
            log_path = Path("logs/qwen-local.log")
            log_path.parent.mkdir(parents=True, exist_ok=True)

            # Iniciar processo em background
            self._process = subprocess.Popen(
                cmd,
                shell=True,
                stdout=open(log_path, "w", encoding="utf-8"),
                stderr=subprocess.STDOUT,
                cwd=cwd,
            )

            # Aguardar o server ficar pronto
            start = time.time()
            timeout = self.config["startup_timeout"]
            while time.time() - start < timeout:
                if self.is_available():
                    logger.info("✅ Qwen local pronto!")
                    return True
                time.sleep(1)

            raise TimeoutError(
                f"Qwen local não iniciou em {timeout}s. "
                f"Verifique logs em {log_path}"
            )
        finally:
            self._starting = False

    def shutdown(self) -> None:
        """Encerra o processo do llama-server se foi iniciado por nós."""
        if self._process is not None:
            logger.info("Encerrando llama-server...")
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
            self._process = None
            self._client = None
