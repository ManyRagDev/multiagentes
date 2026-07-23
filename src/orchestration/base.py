"""Orquestrador base - coordena execução de múltiplos agentes."""

from typing import Dict, List, Any, Callable, Optional
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
import yaml

from src.schemas.agent import AgentConfig, AgentOutput
from src.agents.base import BaseAgent


@dataclass
class WorkflowResult:
    """Resultado de um workflow/orquestração."""

    sucesso: bool
    outputs: Dict[str, Any] = field(default_factory=dict)
    erros: List[str] = field(default_factory=list)
    tokens_totais: int = 0
    metadados: Dict[str, Any] = field(default_factory=dict)


class Orchestrator:
    """
    Orquestrador de agentes.

    Coordena execução de múltiplos agentes, em sequência ou paralelo.
    """

    def __init__(self, config_path: str | None = None):
        """
        Inicializa o orquestrador.

        Args:
            config_path: Caminho para arquivo de configuração YAML
        """
        self.config_path = config_path
        self.config: Dict[str, Any] = {}
        self._agentes: Dict[str, BaseAgent] = {}

        if config_path:
            self.load_config(config_path)

    def load_config(self, path: str) -> None:
        """
        Carrega configuração de arquivo YAML.

        Args:
            path: Caminho para o arquivo YAML
        """
        config_file = Path(path)
        if not config_file.exists():
            raise FileNotFoundError(f"Config não encontrada: {path}")

        with open(config_file, 'r', encoding='utf-8') as f:
            self.config = yaml.safe_load(f)

    def get_model_name(self, key: str) -> str:
        """
        Resolve nome do modelo a partir de chave.

        Args:
            key: Chave do modelo (opus, sonnet, haiku) ou ID direto

        Returns:
            ID do modelo
        """
        # Se já parece um ID de modelo, retorna
        if '/' in key or key.startswith('claude-'):
            return key

        # Resolve usando config
        models = self.config.get('models', {})
        return models.get(key, key)

    def register_agent(
        self,
        nome: str,
        agente: BaseAgent
    ) -> None:
        """
        Registra um agente para uso nos workflows.

        Args:
            nome: Nome identificador do agente
            agente: Instância do agente
        """
        self._agentes[nome] = agente

    def get_agent_config(
        self,
        dominio: str,
        nome_agente: str
    ) -> AgentConfig:
        """
        Extrai configuração de um agente do YAML.

        Args:
            dominio: Domínio (planning, audit, verify, codegen)
            nome_agente: Nome do agente

        Returns:
            AgentConfig com configuração do agente
        """
        agentes = self.config.get('agentes', {})
        dominio_config = agentes.get(dominio, {})
        agente_config = dominio_config.get(nome_agente, {})

        if not agente_config:
            raise ValueError(
                f"Agente {dominio}.{nome_agente} não encontrado na config"
            )

        # Resolve nome do modelo
        model_key = agente_config.get('model', 'sonnet')
        model_name = self.get_model_name(model_key)

        return AgentConfig(
            nome=agente_config['nome'],
            role=agente_config['role'],
            model=model_name,
            temperature=agente_config['temperature'],
            prompt_file=agente_config.get('prompt_file'),
            dominio=dominio,
            output_schema=agente_config.get('output_schema')
        )

    def run_sequential(
        self,
        steps: List[Dict[str, Any]]
    ) -> WorkflowResult:
        """
        Executa agentes em sequência.

        Cada step pode usar outputs dos steps anteriores.

        Args:
            steps: Lista de steps, cada um com:
                - agent: Config do agente ou nome registrado
                - inputs: Dict com variáveis para o prompt
                - output_name: Nome para salvar o output

        Returns:
            WorkflowResult com todos os outputs
        """
        result = WorkflowResult(sucesso=True)
        context: Dict[str, Any] = {}

        for step in steps:
            agent_config = step.get('agent')
            inputs = step.get('inputs', {})
            output_name = step.get('output_name', 'output')

            # Se inputs tem referências {{output}}, resolve do contexto
            resolved_inputs = self._resolve_inputs(inputs, context)

            # Executar agente
            if isinstance(agent_config, BaseAgent):
                output = agent_config.run(**resolved_inputs)
            else:
                raise NotImplementedError(
                    "Criar agente a partir de config não implementado ainda"
                )

            # Salvar no contexto e resultado
            context[output_name] = output.output
            result.outputs[output_name] = output.output

            if output.tokens_usados:
                result.tokens_totais += output.tokens_usados

            if not output.sucesso:
                result.sucesso = False
                result.erros.append(
                    f"Step {output_name}: {output.erro}"
                )
                break

        return result

    def run_parallel(
        self,
        tasks: List[Dict[str, Any]],
        max_workers: int | None = None
    ) -> WorkflowResult:
        """
        Executa agentes em paralelo.

        Args:
            tasks: Lista de tarefas, cada uma com:
                - agent: Config do agente
                - inputs: Dict com variáveis
                - output_name: Nome para salvar
            max_workers: Máximo de workers (None = padrão)

        Returns:
            WorkflowResult com todos os outputs
        """
        result = WorkflowResult(sucesso=True)

        def execute_task(task: Dict[str, Any]) -> tuple[str, AgentOutput]:
            agent = task.get('agent')
            inputs = task.get('inputs', {})
            output_name = task.get('output_name', 'output')

            if isinstance(agent, BaseAgent):
                output = agent.run(**inputs)
                return output_name, output
            raise NotImplementedError("Config agent not implemented")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(execute_task, task): task
                for task in tasks
            }

            for future in as_completed(futures):
                output_name, output = future.result()
                result.outputs[output_name] = output.output

                if output.tokens_usados:
                    result.tokens_totais += output.tokens_usados

                if not output.sucesso:
                    result.sucesso = False
                    result.erros.append(
                        f"Task {output_name}: {output.erro}"
                    )

        return result

    def _resolve_inputs(
        self,
        inputs: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Resolve referências no input.

        Se um valor começa com {{, tenta resolver do contexto.

        Args:
            inputs: Inputs com possíveis referências
            context: Contexto com outputs anteriores

        Returns:
            Inputs resolvidos
        """
        resolved = {}

        for key, value in inputs.items():
            if isinstance(value, str) and value.startswith('{{'):
                # Referência: {{output.campo}}
                ref = value[2:].rstrip('}')
                ref_parts = ref.split('.')
                if ref_parts[0] in context:
                    ref_value = context[ref_parts[0]]
                    for part in ref_parts[1:]:
                        if isinstance(ref_value, dict):
                            ref_value = ref_value.get(part)
                        else:
                            ref_value = getattr(ref_value, part, None)
                    resolved[key] = ref_value
                else:
                    resolved[key] = value  # Mantém se não encontrar
            else:
                resolved[key] = value

        return resolved
