"""
Contrato de delegação estruturado para o Executor.
Define a interface entre Planner (cérebro) e Executor (braço).
"""
from typing import Any
from pydantic import BaseModel, Field


class TaskContract(BaseModel):
    """Contrato preciso que o Planner entrega ao Executor."""
    
    task_id: str = Field(..., description="ID único da tarefa")
    objective: str = Field(..., description="O que deve ser feito, em 1-2 frases")
    tier: str | None = Field(None, description="Sugestão de tier: local|medium|strong")
    
    allowed_files: list[str] = Field(default_factory=list, description="Arquivos que podem ser alterados")
    forbidden_files: list[str] = Field(default_factory=list, description="Arquivos intocáveis")
    context_snippets: list[str] = Field(
        default_factory=list,
        description="Trechos selecionados de contexto (máx ~2k tokens total)"
    )
    
    constraints: list[str] = Field(default_factory=list, description="Restrições duras")
    acceptance_criteria: list[str] = Field(default_factory=list, description="Critérios de aceite objetivos")
    validation_commands: list[str] = Field(
        default_factory=list,
        description="Comandos: 'lint', 'typecheck', 'test', 'build' ou comandos custom"
    )
    
    # O3 — Especificidade Inversa: para LOCAL, preencha com tipos/defaults/formatos exatos
    required_behavior: dict[str, Any] | None = Field(
        None,
        description=(
            "Especificação estruturada do comportamento esperado (parâmetros, tipos, "
            "defaults, formato de retorno, casos de borda). Obrigatório para tier=local."
        )
    )
    
    # Anti-padrão: steps textuais demais. Use só quando a ordem importa.
    steps: list[str] = Field(default_factory=list, description="Passos ordenados (use com parcimônia)")
    
    # Metadados de contexto para o orquestrador
    output_format: str = "full_file"
    stack: str = ""
    command_timeout: int = 30
    max_files_changed: int = Field(3, description="Máximo de arquivos alterados permitidos")
    max_attempts: int = Field(3, description="Máximo de tentativas de execução")
    risk: str | None = Field(None, description="low|medium|high")
    
    model_config = {"extra": "forbid"}