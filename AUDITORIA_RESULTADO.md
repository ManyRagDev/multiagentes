# Resultado da Auditoria — Multiagentes Harness

**Data:** 2026-07-23
**Auditor:** Execução automatizada conforme AUDITORIA_PRONTIDAO_MULTIAGENTE.md

---

## Veredito

- **Nível alcançado:** 1 (Protótipo), limiar do Nível 2 (Testável com mocks)
- **Nota de maturidade:** 4/10
- **Pronto para mocks:** ✅ Sim — `scripts/eval_*.py` e `scripts/test_*.py` passam com providers/APIs mockados (24/24 testes)
- **Pronto para LLM local:** ❌ Não — provider local Qwen funciona isoladamente, mas pipeline principal tem P0s não resolvidos
- **Pronto para APIs remotas:** ❌ Não — STRONG/MEDIUM tiers sem providers registrados; qualquer tarefa acima de local falha
- **Pronto para merge autônomo:** ❌ Não — 6 bloqueadores P0, sem Git isolado, sem contenção de paths

---

## Evidências Executadas

| Comando/Teste | Resultado | Observação |
|---|---|---|
| `git rev-parse --show-toplevel` | `C:/Users/emanu` | ❌ Raiz é a home, não o projeto |
| `git log -1 --oneline` | `fatal: no commits` | ❌ Sem commits base |
| `uv sync --extra dev` | OK | ✅ Dependências instaladas |
| `uv run pytest` | 0/8 passaram | ❌ `mocker` fixture ausente, API key ausente |
| `scripts/eval_prompts.py` | 4/4 | ✅ Suite de regressão Fase 5 funciona |
| `scripts/test_worktree.py` | 6/6 | ✅ Worktree funciona com mocks |
| `scripts/eval_reviewer_loop.py` | 7/7 | ✅ Reviewer integrado com mocks |
| `scripts/eval_contrato.py` | 6/6 | ✅ Bridge Plan→TaskContract com mocks |
| `scripts/eval_run_pipeline.py` | 5/5 | ✅ Pipeline run com mocks |
| `scripts/audit_checks.py` | N/A | ✅ Executado, evidências abaixo |

---

## P0 — Bloqueadores

| Item | Estado | Evidência | Correção Necessária |
|---|---|---|---|
| **P0.1** Pipeline determinístico | ❌ REPROVADO | `skill_run()` usa `ValidationPipeline(validators=[])` — zero validadores | Adicionar `CommandValidator` e `DiffValidator` ao pipeline de run; pipeline vazio ≠ aprovado |
| **P0.2** Reviewer retorna `ReviewVerdict` | ✅ APROVADO | `ContractReviewerAgent.review()` tem tipo de retorno `ReviewVerdict` | Verificar `isinstance` no loop para fail-closed |
| **P0.2b** Reviewer fail-closed | ⚠️ PARCIAL | `EnforcementEngine.evaluate()` trata falhas; mas loop não verifica `isinstance` do retorno | Adicionar `isinstance(verdict, ReviewVerdict)` no ExecutionLoop antes de usar |
| **P0.3** Contenção de caminhos | ❌ REPROVADO | `WorktreeManager.merge()` não tem checagem de `../`, `is_relative_to()`, `resolve()`, nem path absoluto | Adicionar validação de path: `resolved.is_relative_to(project_root)` + rejeitar `..` |
| **P0.4** Git isolado | ❌ REPROVADO | Raiz Git = `C:/Users/emanu` (home); zero commits | Criar `git init` no projeto; fazer commit-base; rejeitar `project_root` sem Git |
| **P0.5** Limites do contrato | ⚠️ PARCIAL (3/10) | `allowed_files` ✅, `forbidden_files` ✅, `constraints` ✅; os outros 7 NÃO são aplicados | Aplicar `max_files_changed`, `validation_commands`, `command_timeout`, `max_attempts`, `required_behavior`, `output_format` |

---

## P1 — Confiabilidade

| Item | Estado | Evidência |
|---|---|---|
| **P1.1** Providers registrados | ❌ REPROVADO | Apenas `local-qwen` registrado. `TierRouter.TIER_PROVIDERS` referencia `deepseek`, `groq`, `glm` — nenhum registrado. STRONG tier tem **zero** providers disponíveis |
| **P1.2** Qwen auto-recovery | ✅ APROVADO | `LocalQwenProvider` tem `ensure_ready()` com health check + auto-start; confirmado em teste Fase 5.1 |
| **P1.3** Timeout/retry/fallback | ⚠️ PARCIAL | `BaseAgent` e `ExecutorAgent` têm timeout; `TierRouter` tem fallback em lista. Mas falta backoff com jitter, e STRONG nunca pode cair pra local (ok, isso é respeitado pois não há provider strong) |
| **P1.4** CostLedger | ❌ REPROVADO | `skill_run()` nunca importa ou chama `CostLedger`. Tokens são somados manualmente mas sem registro estruturado nem budget enforcement |
| **P1.5** Configuração/ambiente | ⚠️ PARCIAL | `.env` existe, `ProviderRegistry` carrega, mas config YAML não é usado pelo registry; providers remotos não estão mapeados |
| **P1.6** `needs_context` | ❌ REPROVADO | `ExecutorAgent.extract_payload()` detecta corretamente, mas `ExecutionLoop` **nunca verifica** `needs_context` no output |
| **P1.7** Pytest reproduzível | ❌ REPROVADO | `uv run pytest` → 0/8 passam. Falta `pytest-mock`; `BaseAgent.__init__` exige API key mesmo em testes |
| **P1.8** Scripts de avaliação | ⚠️ PARCIAL | Scripts funcionam com Unicode fixado via `PYTHONUTF8=1`, mas usam apenas `print("[OK]")`, não assertions pytest. Exit codes OK nos que corrigimos |
| **P1.9** Cobertura | ❌ NÃO AVALIADA | Sem `pytest-cov`; cobertura ~0% em teste formal |
| **P1.10** CI | ❌ NÃO EXISTE | Sem GitHub Actions ou pipeline CI |

---

## P2 — Multiagentes

| Item | Estado | Evidência |
|---|---|---|
| **P2.1** Concorrência Orchestrator | ❌ NÃO TESTADO | `Orchestrator.run_parallel()` existe mas nunca testado com falhas parciais, timeouts ou concorrência real |
| **P2.2** Independência adversarial | ⚠️ PARCIAL | Auditores e verificadores têm prompts distintos. `ReviewVerdict` tem `kind: deterministic|opinion`. Mas não há teste de divergência adversarial |
| **P2.3** Contexto e chunking | ⚠️ PARCIAL | `ContextManager` existe com chunking. Mas não testado com cross-file issues, deduplicação |
| **P2.4** Observabilidade | ⚠️ PARCIAL | `ExecutionLoop.history` registra steps. Mas sem `run_id` único, sem structured logging para cada agente |
| **P2.5** Reprodutibilidade | ✅ PARCIAL | Mocks bem definidos nos scripts de teste; diretórios temporários; provider fake determinístico |

---

## Defeitos Encontrados

### Críticos (bloqueiam execução real)

1. **P0.3 — Path traversal no WorktreeManager**
   - `src/tools/worktree.py:merge()` — sem validação de `..`, `resolve()`, ou `is_relative_to()`
   - Um contrato com `allowed_files=["../../fora.txt"]` escreveria fora do projeto

2. **P0.4 — Git raiz na home do usuário**
   - `git rev-parse --show-toplevel` → `C:/Users/emanu`
   - Worktree poderia acessar qualquer arquivo da home

3. **P0.1 — Pipeline de validação vazio**
   - `src/skills/run.py:68` — `ValidationPipeline(validators=[])`
   - Lint, typecheck, testes NUNCA rodam no fluxo principal

4. **P1.1 — STRONG tier sem providers**
   - `TierRouter.TIER_PROVIDERS[STRONG]` = `["glm", "deepseek"]` — nenhum registrado
   - Qualquer tarefa de auth/crypto/pagamento falha com "Nenhum provider disponível"

### Altos (comprometem confiabilidade)

5. **P1.6 — needs_context ignorado no loop**
   - Executor detecta `needs_context=True`, mas `ExecutionLoop` nunca verifica
   - Output ambíguo poderia ser tratado como código válido

6. **P1.4 — CostLedger desconectado**
   - `skill_run()` não registra tokens/custos no ledger
   - Sem budget enforcement no fluxo principal

7. **P0.5 — 7/10 campos do contrato não aplicados**
   - `max_files_changed`, `validation_commands`, `command_timeout`, `max_attempts`, `required_behavior`, `output_format` são aceitos pelo Pydantic mas ignorados pela enforcement

### Médios

8. **P1.7 — Suite pytest quebrada**
   - `mocker` fixture requer `pytest-mock` não instalado
   - `BaseAgent.__init__` exige `OPENAI_API_KEY` mesmo em testes

---

## O Que Já Funciona

- **24/24 testes com mocks passando** (scripts/eval_*.py, scripts/test_*.py)
- WorktreeManager: criar, aplicar, resetar, merge (com mocks)
- ContractReviewerAgent: carrega prompt, parseia ReviewVerdict
- EnforcementEngine: P1, P6, P7 com 11/11 cenários
- ExecutorAgent: parser extract_payload(), self_check, needs_context
- PlanContractAgent: carrega planner.prompty, parseia TaskContract
- ExecutionLoop com reviewer integrado: approve, retry, escalate, feedback
- `python -m src run --help` funcional
- `python -m src contrato --help` funcional
- Graphify: 853 nós, 1742 arestas, 43 comunidades

---

## Próximos Passos Priorizados

1. **P0.3** — Adicionar validação de path no WorktreeManager (1h)
2. **P0.4** — Inicializar Git no projeto + commit-base (5min)
3. **P0.1** — Substituir `ValidationPipeline(validators=[])` por pipeline com DiffValidator + SchemaValidator reais (1h)
4. **P1.1** — Registrar providers `glm`, `deepseek` no ProviderRegistry via `.env` (1h)
5. **P1.6** — Adicionar check de `needs_context` no ExecutionLoop após executor (30min)
6. **P1.7** — Instalar `pytest-mock`, adicionar mock client para BaseAgent em testes (1h)

---

## Riscos Residuais

- O Qwen local é o único provider funcional — sem ele, o sistema inteiro falha
- A integração Planner→TaskContract nunca foi testada com API real (apenas mocks)
- O Reviewer nunca foi testado com API real (apenas mocks)
- Sem Git isolado, um merge mal-sucedido pode corromper o projeto
