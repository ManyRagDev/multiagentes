"""ContextManager - Gerencia contexto grande sem LLM."""

from pathlib import Path
from typing import Dict, List, Any
import ast


class ContextManager:
    """
    Gerencia contexto grande dividindo em chunks.

    Não usa LLM - apenas lógica pura.
    """

    def __init__(self, max_chunk_size: int = 8000):
        """
        Inicializa ContextManager.

        Args:
            max_chunk_size: Tamanho máximo de cada chunk em caracteres
        """
        self.max_chunk_size = max_chunk_size

    def prepare_chunks(self, files: Dict[str, str]) -> List[Dict[str, str]]:
        """
        Divide arquivos em chunks processáveis.

        Estratégia:
        - Arquivo pequeno: chunk único
        - Arquivo grande: não divide (mantém completo) → Worker lida
        - Múltiplos arquivos: agrupa em chunks por tamanho

        Args:
            files: Dict de {caminho_arquivo: conteúdo}

        Returns:
            Lista de chunks, cada chunk é {arquivo: conteúdo}
        """
        chunks = []
        current_chunk: Dict[str, str] = {}
        current_size = 0

        for file_path, content in files.items():
            file_size = len(content)

            # Se sozinho já excede, não divide (worker lida com isso)
            if file_size > self.max_chunk_size:
                # Fecha chunk atual se tiver algo
                if current_chunk:
                    chunks.append(current_chunk)
                    current_chunk = {}
                    current_size = 0

                # Arquivo grande como chunk próprio
                chunks.append({file_path: content})
                continue

            # Cabe no chunk atual?
            if current_size + file_size <= self.max_chunk_size:
                current_chunk[file_path] = content
                current_size += file_size
            else:
                # Fecha chunk atual, começa novo
                if current_chunk:
                    chunks.append(current_chunk)
                current_chunk = {file_path: content}
                current_size = file_size

        # Último chunk
        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def assign_workers(self, chunks: List[Dict[str, str]], num_workers: int = 3) -> Dict[int, List[Dict[str, str]]]:
        """
        Distribui chunks entre workers.

        Usa round-robin simples para balanceamento.

        Args:
            chunks: Lista de chunks
            num_workers: Número de workers

        Returns:
            Dict {worker_id: [chunks]}
        """
        assignment = {i: [] for i in range(num_workers)}

        for i, chunk in enumerate(chunks):
            worker_id = i % num_workers
            assignment[worker_id].append(chunk)

        return assignment

    def count_tokens_estimate(self, text: str) -> int:
        """
        Estima token count (aproximado: 4 chars ≈ 1 token).

        Args:
            text: Texto para estimar

        Returns:
            Estimativa de tokens
        """
        return len(text) // 4

    def get_context_summary(self, files: Dict[str, str]) -> Dict[str, Any]:
        """
        Retorna resumo do contexto sem processar.

        Args:
            files: Dict de arquivos

        Returns:
            Dict com metadados do contexto
        """
        total_chars = sum(len(content) for content in files.values())
        total_tokens_est = self.count_tokens_estimate(total_chars)

        return {
            "num_files": len(files),
            "total_chars": total_chars,
            "estimated_tokens": total_tokens_est,
            "needs_chunking": total_tokens_est > 10000,  # ~10K tokens
            "recommended_workers": 1 if total_tokens_est < 5000 else min(3, total_tokens_est // 5000)
        }

    def split_large_file(self, file_path: str, content: str, max_size: int) -> List[Dict[str, str]]:
        """
        Divide arquivo muito grande em partes.

        Tentativa simplificada: divide por funções/classes.

        Args:
            file_path: Caminho do arquivo
            content: Conteúdo
            max_size: Tamanho máximo por parte

        Returns:
            Lista de chunks
        """
        try:
            # Tenta parsear como Python
            tree = ast.parse(content)
            chunks = []

            # Divide por função/classe principal
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    start = node.lineno
                    end = getattr(node, "end_lineno", start)

                    # Extrai linhas
                    lines = content.split("\n")
                    chunk_content = "\n".join(lines[start-1:end])

                    if len(chunk_content) > 0:
                        chunks.append({
                            f"{file_path}::{node.name}": chunk_content
                        })

            if chunks:
                return chunks

        except (SyntaxError, Exception):
            pass

        # Fallback: divide por tamanho bruto
        return self._split_by_size(file_path, content, max_size)

    def _split_by_size(self, file_path: str, content: str, max_size: int) -> List[Dict[str, str]]:
        """Divide por tamanho bruto."""
        chunks = []
        for i in range(0, len(content), max_size):
            chunk_content = content[i:i + max_size]
            chunks.append({
                f"{file_path}::part{i//max_size + 1}": chunk_content
            })
        return chunks


# Instância singleton
context_manager = ContextManager()
