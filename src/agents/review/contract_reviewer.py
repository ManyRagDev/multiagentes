"""ContractReviewerAgent — revisa output do executor contra o TaskContract.

Fase 6.2: Usa o prompt reviewer.prompty (Fase 5.3) com P6 (provenance)
e P7 (anti-sycophancy) para avaliar o codigo gerado pelo ExecutorAgent.
"""
from openai import OpenAI

from src.agents.base import BaseAgent
from src.schemas.verdict import ReviewVerdict
from src.schemas.agent import AgentConfig


class ContractReviewerAgent(BaseAgent[ReviewVerdict]):
    """Revisor que avalia o output do executor contra o contrato.

    Usa o prompt reviewer.prompty que inclui:
    - P6: provenance (deterministic vs opinion)
    - P7: anti-sycophancy (aprovação exige evidência)
    - Decision tree de classificação
    - Exemplos BOM e anti-padrão
    """

    def __init__(
        self,
        config: AgentConfig | None = None,
        client: OpenAI | None = None,
    ):
        if config is None:
            config = AgentConfig(
                nome="ContractReviewer",
                role="Revisor cético que avalia código contra contrato",
                model="deepseek-v4-pro",
                temperature=0.2,
                prompt_file="prompts/verify/reviewer.prompty",
                dominio="verify",
                output_schema="ReviewVerdict",
            )
        super().__init__(config, client=client)

    def get_output_schema(self) -> type[ReviewVerdict]:
        return ReviewVerdict

    def review(
        self,
        contract,
        executor_output: str,
        validation_summary: str = "",
    ) -> ReviewVerdict:
        """Avalia o output do executor contra o contrato.

        Args:
            contract: TaskContract com objective, constraints, acceptance_criteria
            executor_output: Código/diff gerado pelo executor
            validation_summary: Resumo da validação determinística

        Returns:
            ReviewVerdict com status, issues e approval_evidence
        """
        prompt = self._build_review_prompt(
            contract=contract,
            executor_output=executor_output,
            validation_summary=validation_summary,
        )
        result = self.run(prompt=prompt)

        if not result.sucesso:
            raise RuntimeError(f"Reviewer falhou: {result.erro}")

        return result.output

    @staticmethod
    def _build_review_prompt(
        contract,
        executor_output: str,
        validation_summary: str = "",
    ) -> str:
        """Constrói o prompt de revisão com dados do contrato e output."""
        parts = [
            "---",
            f"## Objetivo\n{contract.objective}",
        ]

        if getattr(contract, "constraints", None):
            parts.append(
                "## Constraints do Contrato\n"
                + "\n".join(f"- {c}" for c in contract.constraints)
            )

        if getattr(contract, "acceptance_criteria", None):
            parts.append(
                "## Critérios de Aceite\n"
                + "\n".join(f"- {a}" for a in contract.acceptance_criteria)
            )

        if getattr(contract, "allowed_files", None):
            parts.append(
                "## Arquivos Permitidos\n"
                + ", ".join(contract.allowed_files)
            )

        if getattr(contract, "forbidden_files", None):
            parts.append(
                "## Arquivos Proibidos\n"
                + ", ".join(contract.forbidden_files)
            )

        if validation_summary:
            parts.append(f"## Validação Determinística\n{validation_summary}")

        parts.append(f"## Código Proposto\n```\n{executor_output[:4000]}\n```")

        if len(executor_output) > 4000:
            parts.append(
                f"\n_(output truncado, {len(executor_output)} chars total)_"
            )

        return "\n\n".join(parts)
