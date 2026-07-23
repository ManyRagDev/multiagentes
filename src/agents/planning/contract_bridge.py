"""PlanContractAgent — gera TaskContract a partir de objetivo usando Planner v2."""
import json

from openai import OpenAI

from src.agents.base import BaseAgent
from src.schemas.contract import TaskContract
from src.schemas.agent import AgentConfig


class PlanContractAgent(BaseAgent[TaskContract]):
    """Agente que transforma um objetivo em TaskContract usando Planner v2.

    Usa o prompt planner.prompty (Fase 5.2) que inclui:
    - P3: decision tree de delegacao (local/medium/strong)
    - P5: contexto enxuto
    - O3: especificidade inversa (required_behavior para tier=local)
    - Escape hatch: needs_clarification
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: OpenAI | None = None,
    ):
        if config is None:
            config = AgentConfig(
                nome="PlanContract",
                role="Planejador que transforma objetivos em contratos para o Executor",
                model="glm-5.2",
                temperature=0.3,
                prompt_file="prompts/planning/planner.prompty",
                dominio="planning",
                output_schema="TaskContract",
            )
        super().__init__(config, client=client)
        self._last_tokens = 0

    def get_output_schema(self) -> type[TaskContract]:
        return TaskContract

    def run_with_objective(self, objective: str, context: str = "") -> TaskContract:
        """Interface conveniente: recebe objetivo em NL, retorna TaskContract.

        Args:
            objective: Descricao do que precisa ser feito
            context: Contexto adicional do projeto

        Returns:
            TaskContract validado

        Raises:
            ValueError: se o modelo retornar needs_clarification
            RuntimeError: se a chamada API falhar
        """
        result = self.run(objetivo=objective, contexto=context)
        self._last_tokens = result.tokens_usados or 0

        if not result.sucesso:
            raw = result.raw_output or ""
            if "needs_clarification" in raw:
                try:
                    data = json.loads(raw.strip().lstrip("```json").rstrip("```").strip())
                    questions = data.get("questions", ["(detalhes nao fornecidos)"])
                    raise ValueError(
                        f"Planner precisa de mais contexto: {'; '.join(questions)}"
                    )
                except (json.JSONDecodeError, ValueError):
                    pass

            raise RuntimeError(f"PlanContractAgent falhou: {result.erro}")

        data = result.output
        if isinstance(data, dict):
            if data.get("status") == "needs_clarification":
                questions = data.get("questions", [])
                raise ValueError(
                    f"Planner precisa de mais contexto: {'; '.join(questions)}"
                )
            return TaskContract(**data)

        raise RuntimeError(f"Output inesperado: {type(data)}")
