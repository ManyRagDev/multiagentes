# Auditoria de Prontidão para Testes Multiagentes

## Missão do agente responsável

Verificar, com evidências reproduzíveis, se o projeto **Multiagentes** está seguro e suficientemente maduro para executar testes multiagentes com chamadas reais de LLM, concorrência, alterações de arquivos e eventual merge.

O trabalho não consiste apenas em ler o código ou confirmar que classes existem. Cada item deve ser rastreado desde a entrada pública até o efeito final, testado e classificado como:

- `APROVADO`: comportamento confirmado por teste automatizado.
- `REPROVADO`: defeito reproduzido ou requisito não atendido.
- `BLOQUEADO`: não foi possível verificar por uma dependência externa claramente identificada.
- `NÃO APLICÁVEL`: somente com justificativa objetiva.

Não tratar scripts que apenas imprimem `[OK]` como evidência suficiente. O processo deve verificar assertions, código de saída e efeitos no filesystem.

## Resultado esperado

Ao final, entregar:

1. Relatório atualizado de maturidade.
2. Matriz com todos os controles deste documento e seus estados.
3. Evidências dos comandos executados e testes criados.
4. Lista de bloqueadores por prioridade.
5. Recomendação explícita:
   - pronto para mocks;
   - pronto para LLM local em repositório descartável;
   - pronto para APIs remotas;
   - pronto ou não para merge autônomo.
6. Nota geral de maturidade de `0` a `10`, acompanhada de justificativa.

## Regras de segurança

- Não executar testes de escrita contra a home do usuário.
- Não utilizar `C:\Users\emanu` como raiz de projeto ou repositório de teste.
- Não usar chaves reais em testes automatizados.
- Não imprimir valores de variáveis de ambiente, tokens ou credenciais.
- Testes que alterem arquivos devem usar diretórios temporários ou repositórios descartáveis.
- Não habilitar merge autônomo enquanto os bloqueadores P0 deste documento existirem.
- Não aceitar uma falha de reviewer, validator ou enforcement como aprovação.
- Antes de copiar, escrever ou fazer merge, resolver o caminho absoluto e confirmar que ele permanece dentro de `project_root`.
- Preservar alterações preexistentes do usuário.

## Arquitetura que deve ser verificada

O repositório contém dois fluxos que precisam ser analisados separadamente.

### Fluxo de skills original

```text
/plano
  PlanCreator → PlanValidator → DependencyChecker

/auditoria
  ├─ BugHunter ─────── BugRefuter
  ├─ SecAudit ──────── SecSkeptic
  ├─ PerfAnalyst ───── PerfDoubter
  └─ CompletenessCheck

/implementar
  CodeGen → CodeVerifier
```

O fluxo de auditoria usa `Orchestrator.run_parallel()` e deve ser testado quanto a concorrência, isolamento, falhas parciais e agregação de resultados.

### Fluxo novo de execução

```text
Objetivo
  → PlanContractAgent
  → TaskContract
  → TierRouter
  → ExecutorAgent
  → WorktreeManager
  → ValidationPipeline
  → EnforcementEngine
  → ContractReviewerAgent
  → merge, retry, reject, block ou escalate
```

O comando público principal é:

```bash
python -m src run "<objetivo>" --project-root "<projeto>"
```

## Estado inicial observado

Os itens abaixo foram identificados em uma análise anterior. Eles são hipóteses de auditoria e devem ser reproduzidos novamente, não assumidos como verdade sem teste.

- O grafo existente possui aproximadamente 853 nós, 1.742 relações e 43 comunidades.
- Não foram detectados ciclos de importação no grafo.
- O projeto parece dividido entre o `Orchestrator` original e o `ExecutionLoop` mais novo.
- Apenas o provider `local-qwen` parece ser registrado no `ProviderRegistry`.
- O router referencia `deepseek`, `groq` e `glm`, embora esses providers aparentemente não estejam registrados.
- A suíte pytest não estava reproduzível no ambiente analisado.
- O projeto não possuía repositório Git próprio; o Git detectava `C:\Users\emanu` como raiz.
- Alguns scripts de avaliação retornavam código de saída zero mesmo registrando falhas.

## P0 — Bloqueadores de segurança e integridade

Nenhum teste multiagente com merge real pode ser aprovado enquanto um item P0 estiver reprovado.

### P0.1 — Validação determinística no fluxo principal

Arquivo principal:

```text
src/skills/run.py
```

Verificar se `skill_run()` instancia um pipeline com validadores reais. A construção abaixo representa falha crítica:

```python
ValidationPipeline(validators=[])
```

O fluxo principal deve executar, quando aplicável:

- validação de schema;
- validação de diff e limites de arquivos;
- lint;
- typecheck;
- testes;
- build ou comandos adicionais do contrato.

Critérios de aceite:

- Um teste deliberadamente quebrado impede o merge.
- Uma falha de lint impede o merge quando lint é requerido.
- Um erro interno do validator não é tratado como sucesso.
- Pipeline vazio não pode ser considerado aprovado.
- O resultado registra quais validadores rodaram, foram ignorados ou falharam.

### P0.2 — Contrato entre Reviewer e ExecutionLoop

Arquivos:

```text
src/agents/review/contract_reviewer.py
src/orchestration/execution_loop.py
src/schemas/verdict.py
```

Verificar o tipo retornado por:

```python
ContractReviewerAgent.review(...)
```

O método deve retornar uma instância de `ReviewVerdict`, e não um `dict`.

Critérios de aceite:

- `isinstance(verdict, ReviewVerdict)` é verdadeiro.
- O loop consegue acessar `status`, `confidence`, `issues` e propriedades derivadas.
- Resposta inválida do reviewer não chega ao merge.
- Timeout, exceção, JSON inválido ou schema inválido do reviewer resultam em `retry`, `escalate`, `blocked` ou `error`, nunca aprovação silenciosa.
- O comportamento é **fail-closed**.

Criar teste de integração usando cliente OpenAI fake, mas passando pela implementação real de `ContractReviewerAgent`.

### P0.3 — Contenção de caminhos

Arquivos:

```text
src/schemas/contract.py
src/tools/worktree.py
src/orchestration/enforcement.py
```

Validar todos os elementos de:

- `allowed_files`;
- `forbidden_files`;
- caminhos extraídos de unified diffs;
- caminhos usados em cópia, reset, coleta de diff e merge.

Casos que devem ser rejeitados:

```text
../arquivo.py
../../fora.txt
C:\Windows\arquivo.txt
\\servidor\share\arquivo.txt
/etc/passwd
src/../../fora.txt
```

Critérios de aceite:

- Todo caminho é normalizado e resolvido.
- O caminho final deve satisfazer `resolved_path.is_relative_to(project_root)`, ou equivalente seguro.
- Symlinks e junctions que escapem da raiz são rejeitados.
- O mesmo controle é aplicado no worktree temporário e no projeto real.
- Testes confirmam que nenhum arquivo externo é criado, lido ou alterado.

### P0.4 — Isolamento Git

Verificar:

```bash
git rev-parse --show-toplevel
git status --short
git log -1 --oneline
```

Critérios de aceite:

- A raiz retornada é exatamente a raiz deste projeto.
- Existe um repositório Git próprio.
- Existe pelo menos um commit-base conhecido.
- Testes nunca utilizam a home como repositório.
- O runtime rejeita `project_root` sem isolamento ou exige confirmação explícita.
- Deve existir uma estratégia de recuperação para merges parcialmente aplicados.

### P0.5 — Enforcement dos limites do contrato

Verificar se estes campos são efetivamente aplicados:

- `allowed_files`;
- `forbidden_files`;
- `max_files_changed`;
- `constraints`;
- `validation_commands`;
- `command_timeout`;
- `max_attempts`;
- `required_behavior` para tarefas locais;
- `output_format`.

Critérios de aceite:

- Não basta que o campo exista no Pydantic.
- Cada campo deve possuir ao menos um teste positivo e um negativo.
- Full-file output e unified diff devem receber controles equivalentes.
- Ausência de nome de arquivo em full-file output não pode contornar `allowed_files`.

## P1 — Confiabilidade das chamadas e do runtime

### P1.1 — Registro e configuração de providers

Arquivos:

```text
src/providers/base.py
src/providers/__init__.py
src/providers/local_qwen.py
src/routing/tier_router.py
config/agents.yaml
```

Verificar:

- Quais providers estão realmente registrados.
- Se a configuração YAML é carregada pelo registry.
- Se `glm`, `deepseek` e `groq` possuem implementação real.
- Se nomes de modelos e providers são coerentes em todos os arquivos.
- Se um provider não registrado é rejeitado com erro claro.

Critérios de aceite:

- Cada candidato do `TierRouter.TIER_PROVIDERS` está registrado ou é removido da lista.
- Configuração não deve estar duplicada e divergente entre Python, YAML e `.env`.
- Health check não deve expor credenciais.
- Testes usam providers fake registrados temporariamente.

### P1.2 — Bootstrap e recuperação do Qwen local

Verificar o ciclo:

```text
router → health check → seleção → ensure_ready → chamada
```

O sistema deve conseguir selecionar e iniciar o provider local quando ele estiver parado, se `auto_restart` estiver habilitado.

Critérios de aceite:

- Servidor saudável: seleciona sem reiniciar.
- Servidor parado + auto-restart: inicia uma única vez.
- Duas chamadas concorrentes não iniciam dois processos.
- Startup timeout encerra com estado claro.
- Processo que morre durante uma chamada pode ser recuperado conforme política.
- Handles de arquivo e processos são encerrados.
- O comando de startup não fica rigidamente preso a `C:\llama.cpp`.

### P1.3 — Timeout, retry e fallback

Mapear todas as chamadas:

- `BaseAgent.run()`;
- `BaseAgent.run_with_retry()`;
- `ExecutorAgent.execute_raw()`;
- `ContractReviewerAgent`;
- `PlanContractAgent`;
- `HybridRouter`;
- providers locais e remotos.

Critérios de aceite:

- Toda chamada externa possui timeout explícito.
- Retry distingue erro transitório de erro permanente.
- Existe backoff com limite e, preferencialmente, jitter.
- Erro de schema pode acionar reparo de output quando a política permitir.
- Rate limit, timeout, conexão recusada e resposta vazia têm testes separados.
- Fallback de provider respeita o tier de segurança.
- Tarefa `STRONG` nunca cai silenciosamente para provider local.
- Histórico registra tentativa, provider, modelo e motivo da troca.

### P1.4 — CostLedger e budgets

Arquivo:

```text
src/routing/cost_ledger.py
```

Verificar se cada chamada real registra:

- tokens de entrada;
- tokens de saída;
- custo;
- provider;
- quantidade de requests;
- timestamp;
- task ID ou run ID.

Critérios de aceite:

- `CostLedger.record()` é chamado no runtime real.
- Budget é verificado antes e depois da chamada.
- Concorrência não perde atualizações.
- Falha de persistência não é ignorada silenciosamente.
- Custos do planner e reviewer também são contabilizados.
- O custo exibido usa a mesma tabela do ledger.

### P1.5 — Carregamento de configuração e ambiente

Verificar:

- carregamento de `.env`;
- precedência entre argumento, YAML e ambiente;
- validação de chaves ausentes;
- mensagens de erro;
- ausência de segredos em logs.

Critérios de aceite:

- O CLI funciona em um shell limpo quando um `.env` válido é fornecido.
- Chave ausente falha antes da execução, com orientação clara.
- O arquivo `.env` permanece ignorado por Git e pelo worktree.
- Testes só verificam presença de variáveis, nunca seus valores.

### P1.6 — Sinal `needs_context`

O `ExecutorAgent` extrai `needs_context` do `<self_check>`.

Critérios de aceite:

- `needs_context=True` não pode ser tratado como código aprovado.
- O loop solicita contexto, bloqueia ou escala.
- O estado aparece no histórico e no resultado público.
- Há teste com output contendo apenas `<self_check>`.

## P1 — Testes, CI e reprodutibilidade

### P1.7 — Ambiente de desenvolvimento

Revisar:

```text
pyproject.toml
uv.lock
pytest.ini
```

Garantir a presença de:

- `pytest`;
- `pytest-asyncio`;
- `pytest-mock`, caso o fixture `mocker` continue sendo usado;
- `ruff`;
- `mypy`;
- ferramenta de coverage;
- build backend necessário.

Critérios de aceite:

```bash
uv sync --extra dev
uv run pytest
uv run ruff check src tests
uv run mypy src
```

Todos devem funcionar em um clone limpo.

### P1.8 — Conversão dos scripts de avaliação

Os arquivos em `scripts/test_*.py` e `scripts/eval_*.py` devem:

- migrar cenários relevantes para `tests/`;
- usar assertions reais;
- retornar exit code diferente de zero em qualquer falha;
- não depender da codificação CP1252;
- não depender de inspeção visual de `[OK]`.

Critérios de aceite:

- Um teste propositalmente quebrado faz o comando falhar.
- A suíte funciona com `PYTHONUTF8=1` e em CI.
- Scripts que fazem chamadas reais ficam separados e marcados como `integration` ou `live`.

### P1.9 — Cobertura mínima

Criar testes para:

- schemas e validações de campos;
- classifier e routing;
- registry;
- retries e fallback;
- worktree e path traversal;
- enforcement;
- reviewer real com cliente fake;
- loop completo sem mockar o próprio `ExecutionLoop`;
- falhas parciais dos agentes paralelos;
- agregação de findings e verdicts;
- CLI e códigos de saída.

Meta inicial sugerida:

- 80% de cobertura das camadas críticas;
- 100% dos branches de decisão de merge/reject/retry/escalate/block;
- nenhum P0 sem teste negativo.

### P1.10 — CI

Adicionar pipeline para:

- instalação limpa;
- lint;
- typecheck;
- testes unitários;
- testes de integração sem rede;
- coverage;
- build do pacote;
- smoke test do CLI.

Chamadas LLM reais devem ser opt-in, nunca requisito para PRs comuns.

## P2 — Prontidão multiagente

### P2.1 — Concorrência do Orchestrator

Testar `run_parallel()` com:

- três agentes bem-sucedidos;
- um agente que retorna falha;
- um agente que lança exceção;
- um agente que excede timeout;
- respostas em ordens diferentes;
- nomes de output duplicados;
- limite de workers menor que o número de tarefas;
- cancelamento do restante após falha crítica.

Critérios de aceite:

- Nenhuma exceção de future derruba o processo sem resultado estruturado.
- Resultados permanecem associados ao agente correto.
- O estado agregado representa falhas parciais.
- Contadores de tokens e custos são consistentes sob concorrência.
- Logs possuem `run_id`, `task_id` e `agent_id`.

### P2.2 — Independência e adversarialidade

Verificar se auditores e verificadores:

- usam prompts distintos;
- recebem o contexto necessário, mas não respostas ocultas indevidas;
- não compartilham estado mutável acidentalmente;
- não usam o mesmo output como “prova” sem validação;
- preservam provenance dos findings;
- diferenciam fato determinístico de opinião.

Criar cenários em que:

- auditor inventa um finding;
- verificador concorda sem evidência;
- dois agentes divergem;
- meta-auditor detecta dimensão não analisada;
- nenhum finding é produzido por falha de todos os agentes.

O último caso não pode ser reportado como “código limpo”.

### P2.3 — Contexto e chunking

Verificar:

- tamanho máximo de contexto;
- divisão por arquivos;
- sobreposição necessária;
- perda de relações entre chunks;
- deduplicação de findings;
- limites globais de tokens;
- tratamento de arquivos binários ou muito grandes.

Critérios de aceite:

- Findings duplicados entre chunks são consolidados.
- Cross-file issues possuem teste.
- Falha em um chunk aparece no resultado final.
- O meta-auditor conhece a cobertura efetivamente analisada.

### P2.4 — Observabilidade

Cada execução deve registrar de forma estruturada:

- `run_id`;
- `task_id`;
- agente;
- provider/modelo;
- início e duração;
- tentativa;
- tokens;
- custo;
- validator;
- decisão;
- motivo de retry/fallback/escalation;
- arquivos candidatos e realmente modificados.

Não registrar prompts completos ou código sensível por padrão.

### P2.5 — Reprodutibilidade

Para testes com mocks:

- outputs fixos;
- relógio controlável quando necessário;
- provider fake determinístico;
- diretório temporário;
- IDs previsíveis ou capturáveis.

Para testes com LLM real:

- registrar modelo e parâmetros;
- temperatura baixa;
- repetir o cenário várias vezes;
- medir taxa de sucesso, não apenas uma execução;
- definir limite de custo e duração.

## Cenários mínimos de teste end-to-end

### Cenário A — Caminho feliz controlado

1. Criar repositório temporário com commit-base.
2. Registrar provider fake.
3. Planner gera contrato válido.
4. Executor altera um único arquivo permitido.
5. Lint e testes passam.
6. Reviewer retorna `ReviewVerdict` aprovado com evidências.
7. Enforcement aprova.
8. Merge altera apenas o arquivo esperado.

### Cenário B — Teste falhando

O executor gera código inválido ou que quebra teste. O pipeline deve impedir merge e produzir feedback para retry.

### Cenário C — Reviewer indisponível

O reviewer lança timeout. O fluxo deve bloquear, escalar ou falhar fechado.

### Cenário D — Escape de diretório

Planner ou executor tenta usar `../../fora.py`. O contrato deve ser rejeitado antes de qualquer leitura ou escrita externa.

### Cenário E — Provider local parado

O Qwen local começa indisponível. A política de auto-restart deve iniciar uma única instância ou retornar falha estruturada.

### Cenário F — Budget excedido

O ledger indica budget esgotado. O router aplica fallback seguro ou bloqueia conforme tier.

### Cenário G — Auditoria com falha parcial

Dois auditores respondem e um falha. O relatório deve declarar cobertura parcial, não “código limpo”.

### Cenário H — Divergência adversarial

Auditor produz finding sem evidência e verificador o refuta. O resultado final deve preservar finding, verdict e provenance.

## Comandos de verificação sugeridos

Adaptar os comandos ao ambiente sem expor segredos.

```powershell
git rev-parse --show-toplevel
git status --short
git log -1 --oneline

uv sync --extra dev
uv run pytest
uv run pytest --cov=src --cov-report=term-missing
uv run ruff check src tests
uv run mypy src

uv run python -m compileall -q src
uv run python -m src
uv run python -m src run --help
```

Para localizar conexões incompletas:

```powershell
rg -n "ValidationPipeline|validators=\[\]|ledger\.record|ProviderRegistry\.register" src tests
rg -n "allowed_files|forbidden_files|max_files_changed|validation_commands|required_behavior" src tests
rg -n "except Exception|pass$|NotImplemented|TODO|FIXME" src tests
rg -n "chat\.completions\.create|httpx|subprocess|create_subprocess" src
```

## Matriz final de aprovação

O agente deve preencher esta tabela no relatório final.

| Controle | Estado | Evidência | Teste automatizado | Bloqueia execução real? |
|---|---|---|---|---|
| Pipeline determinístico ativo | PENDENTE | | | Sim |
| Reviewer retorna `ReviewVerdict` | PENDENTE | | | Sim |
| Reviewer é fail-closed | PENDENTE | | | Sim |
| Contenção de caminhos | PENDENTE | | | Sim |
| Git isolado na raiz correta | PENDENTE | | | Sim |
| Limites do contrato aplicados | PENDENTE | | | Sim |
| Providers registrados | PENDENTE | | | Sim |
| Qwen auto-recovery | PENDENTE | | | Para LLM local |
| Retry/timeout/fallback | PENDENTE | | | Sim |
| CostLedger conectado | PENDENTE | | | Para APIs pagas |
| Configuração e `.env` | PENDENTE | | | Sim |
| `needs_context` tratado | PENDENTE | | | Sim |
| Pytest reproduzível | PENDENTE | | | Sim |
| Scripts com exit code confiável | PENDENTE | | | Sim |
| CI configurada | PENDENTE | | | Para maturidade |
| Concorrência testada | PENDENTE | | | Para multiagentes |
| Falhas parciais representadas | PENDENTE | | | Sim |
| Provenance adversarial | PENDENTE | | | Sim |
| Chunking e cobertura | PENDENTE | | | Para auditoria ampla |
| Observabilidade estruturada | PENDENTE | | | Para operação |

## Regra de decisão

Classificar o projeto segundo estes níveis:

### Nível 0 — Não executável

Instalação, imports ou CLI não funcionam.

### Nível 1 — Protótipo

Componentes isolados funcionam, mas não existe suíte confiável ou integração segura.

### Nível 2 — Testável com mocks

Fluxos principais passam com providers fake, filesystem temporário e sem merge real.

### Nível 3 — Testável com LLM local

Todos os P0 estão aprovados, provider local é recuperável e testes rodam em repositório descartável.

### Nível 4 — Testável com APIs remotas

Budgets, retries, timeouts, secrets, observabilidade e fallback estão comprovados.

### Nível 5 — Pronto para autonomia limitada

CI, cobertura, fail-closed, rollback, contenção de filesystem e gates de merge estão comprovados em múltiplos cenários.

O agente não deve recomendar um nível superior ao menor nível imposto por qualquer bloqueador crítico.

## Formato obrigatório do relatório final

```markdown
# Resultado da Auditoria

## Veredito
- Nível alcançado:
- Nota de maturidade:
- Pronto para mocks:
- Pronto para LLM local:
- Pronto para APIs remotas:
- Pronto para merge autônomo:

## Evidências executadas
| Comando/Teste | Resultado | Observação |

## P0 — Bloqueadores
| Item | Estado | Evidência | Correção necessária |

## P1 — Confiabilidade
| Item | Estado | Evidência | Correção necessária |

## P2 — Multiagentes
| Item | Estado | Evidência | Correção necessária |

## Defeitos encontrados
1. Severidade, arquivo/linha, reprodução, impacto e correção sugerida.

## Testes adicionados
- Arquivo:
- Cenário:
- O que comprova:

## Próximos passos priorizados
1. ...

## Riscos residuais
- ...
```

## Definição de concluído

Esta auditoria só está concluída quando:

- todos os itens da matriz possuírem estado e evidência;
- os comandos relevantes tiverem código de saída registrado;
- todo bloqueador P0 tiver teste de reprodução;
- qualquer correção implementada possuir teste de regressão;
- a recomendação de prontidão distinguir mocks, LLM local, APIs remotas e merge autônomo;
- nenhuma conclusão depender apenas de documentação, comentários ou mensagens impressas por scripts.
