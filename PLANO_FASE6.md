# 📋 PLANO FASE 6 — Integração Ponta a Ponta: Pipeline Completo

> **Criado:** 2026-07-23
> **Status:** ⏳ Planejado — aguardando início
> **Origem:** Fase 5 concluiu todos os componentes isolados; falta o fluxo unificado que os conecta
> **Meta:** `python -m src run "objetivo"` executa Planner → ExecutionLoop → Reviewer → Merge/Reject em um único comando

---

## 0. Diagnóstico do Estado Atual

### O que funciona (5 componentes isolados):

| Componente | Entrada | Saída | Validado |
|---|---|---|---|
| **Skill /plano** | Objetivo em NL | `Plan` (steps textuais) | ✅ E2E tests |
| **Skill /auditoria** | Caminho de código | `CodeReport` (findings) | ✅ E2E tests |
| **Skill /implementar** | `Plan` JSON | Arquivos escritos | ✅ E2E tests |
| **Planner v2 (prompt)** | Objetivo em NL | `TaskContract` JSON | ✅ eval |
| **ExecutionLoop** | `TaskContract` | Código gerado + status | ✅ eval + test_e2e |
| **Reviewer v2 (prompt)** | Código + critérios | `ReviewVerdict` (P6+P7) | ✅ eval |
| **EnforcementEngine** | Output + Verdict | Ação (retry/merge/reject) | ✅ eval |

### O que NÃO funciona (gap de integração):

```
Planner (cloud) ──??──> ExecutionLoop (local) ──??──> Reviewer (cloud) ──??──> Merge
                     ↑                                    ↑
                Fala Plan (steps)                    Nunca chamado pós-execução
                Loop espera TaskContract             EnforcementEngine usa só check_output()
```

**Raiz do problema:** O Planner cloud gera um `Plan` com steps narrativos (pra skill `/implementar` antiga), mas o ExecutionLoop espera um `TaskContract` com `allowed_files`, `constraints`, `required_behavior`. O Reviewer cloud nunca é invocado pelo loop — o `enforcement.evaluate()` existe mas ninguém chama ele com um Verdict real.

---

## 1. Fases de Implementação

### Fase 6.0 — Worktree: Execução Isolada

**Objetivo:** Toda execução do ExecutionLoop roda em diretório temporário. Só faz merge no projeto real se passar em todos os gates.

**Gap que evita:** Qwen gerar código quebrado e poluir o repositório real sem rollback.

**Implementação:**
- `src/tools/worktree.py` — novo módulo: clona repositório em temp dir, executa lá, copia diff de volta
- `GitTool` já tem base para snapshot; worktree usa `git worktree add` ou cópia simples
- Hooks: `pre_execute` (cria worktree) / `post_success` (copia diff) / `post_failure` (descarta)

**Aceite:** Execução com arquivo proibido alterado → worktree descartado, repositório original intocado.

---

### Fase 6.1 — Bridge: Plan → TaskContract

**Objetivo:** Converter o output do Planner (cloud API) no formato que o ExecutionLoop consome.

**Gap que evita:** O Planner v2 já sabe emitir `TaskContract` via prompt, mas a skill `/plano` chama `PlanCreatorAgent` que emite `Plan` (schema antigo). O prompt `.prompty` do Planner nunca é usado por nenhuma skill.

**Implementação:**
- Novo agente `ContractBridge` ou adaptar o skill `/plano` para modo "contrato"
- Duas estratégias (a escolher):
  - **A) Novo skill:** `skill_contrato(objetivo)` → chama Planner v2 via API cloud → retorna `TaskContract` validado
  - **B) Adaptar skill existente:** `/plano --modo contrato` adiciona flag que usa Planner v2 em vez de PlanCreator
- Prefiro **A**: skill novo, focado, sem mexer no que já funciona

**Aceite:** `python -m src contrato "Adicionar validação de email no signup"` → `TaskContract` com tier=local, required_behavior preenchido, pronto para o ExecutionLoop.

---

### Fase 6.2 — Bridge: ExecutionLoop → Reviewer

**Objetivo:** Após execução local passar na validação determinística, invocar Reviewer cloud para auditar o output e alimentar o EnforcementEngine com um `ReviewVerdict` real.

**Gap que evita:** Hoje o loop só faz `check_output()` (P1 determinístico) — nunca usa o Reviewer cloud com P6 (provenance) e P7 (anti-sycophancy) contra código real.

**Implementação:**
- `ExecutionLoop` ganha parâmetro opcional `reviewer: ReviewerAgent`
- Após `pipeline_result.passed == True`, chama `reviewer.review(output, contract)` → obtém `ReviewVerdict`
- Passa o Verdict real para `enforcement.evaluate()` (que já existe e está testado!)
- O loop decide: retry (corrigir com feedback do reviewer), approve (merge no worktree), escalate (chamar humano)

**Aceite:** E2E: Planner gera contrato → Qwen implementa → validação passa → Reviewer cloud audita → Enforcement decide merge/reject.

---

### Fase 6.3 — CLI Unificada: `multiagentes run`

**Objetivo:** Um único comando que executa o ciclo completo.

**Gap que evita:** Hoje o usuário precisa orquestrar manualmente: rodar `/plano`, inspecionar output, montar contrato na mão, rodar script de teste, auditar separadamente.

**Implementação:**
- `src/skills/run.py` — novo skill que orquestra o pipeline:
  1. `skill_contrato(objetivo)` → `TaskContract`
  2. `ExecutionLoop.execute(contract)` com worktree + reviewer
  3. Se aprovado → merge no projeto real
  4. Se rejeitado → report com issues
- Registrado em `pyproject.toml`: `multiagentes-run = "src.skills.run:main"`
- `src/__main__.py` ganha entrada `run`

**Aceite:** `python -m src run "Adicionar função soma_pares em src/math.py"` → código aparece em `src/math.py` com diff limpo e revisão aprovada.

---

### Fase 6.4 — Suite de Integração

**Objetivo:** Testes end-to-end do pipeline completo (com mocks para APIs cloud, Qwen real para execução).

**Gap que evita:** Cada componente tem teste isolado, mas ninguém testa o fluxo completo com os schemas reais trafegando entre componentes.

**Implementação:**
- `scripts/test_pipeline.py` — cenários E2E:
  - LOCAL feliz: contrato bem especificado → Qwen implementa → reviewer aprova → merge
  - LOCAL falha + retry: Qwen erra → reviewer aponta → Qwen corrige → aprova
  - STRONG: contrato crítico → escala pra API → código gerado → reviewer audita
  - AMBÍGUO: Planner retorna `needs_clarification` → sistema para e pergunta
- Adicionar ao `eval_prompts.py` como nova entrada na suite de regressão

**Aceite:** 4/4 cenários passam com mocks de API + Qwen real.

---

## 2. Ordem e Dependências

```
6.0 (Worktree) ──┐
                 ├──> 6.1 (Plan→Contract) ──┐
                 │                          ├──> 6.3 (CLI unificada) ──> 6.4 (Suite)
                 └──> 6.2 (Loop→Reviewer) ──┘
```

6.0 é pré-requisito porque a integração real mexe em arquivos. 6.1 e 6.2 são paralelizáveis. 6.3 depende de ambos. 6.4 fecha o ciclo.

---

## 3. Tabela de Rastreabilidade

| # | Princípio | Componente | Mudança no Código | Teste |
|---|---|---|---|---|
| W1 | Worktree isolado | `src/tools/worktree.py` | Novo módulo: clone + exec + merge/descarte | Execução com erro → repo original intacto |
| B1 | Bridge Plan→Contract | `src/skills/contrato.py` | Novo skill que chama Planner v2 cloud → TaskContract | Contrato LOCAL tem required_behavior |
| B2 | Bridge Loop→Reviewer | `src/orchestration/execution_loop.py` | Loop chama Reviewer cloud pós-validação + enforcement.evaluate() | Reviewer detecta bug → loop dá retry |
| C1 | CLI run | `src/skills/run.py` + `__main__.py` | Pipeline completo em um comando | `python -m src run "obj"` funciona |
| T1 | Suite integração | `scripts/test_pipeline.py` | 4 cenários E2E com mocks | 4/4 passam |

---

## 4. Riscos e Mitigação

| Risco | Mitigação |
|---|---|
| Planner v2 via API cloud custar caro em testes | Mockar resposta do Planner nos testes; só chamada real em smoke test |
| Worktree conflitar com arquivos abertos no Windows | Usar `tempfile.mkdtemp()` + cópia simples (não git worktree) no Windows |
| Reviewer cloud rejeitar código correto (alucinação) | P7 já mitiga isso; `kind=opinion` não bloqueia merge |
| Qwen local offline durante teste E2E | Suite detecta e pula com warn, não falha |

---

## 5. O Que Este Plano NÃO Faz

- Não reescreve skills existentes (`/plano`, `/auditoria`, `/implementar`)
- Não mexe em schemas (TaskContract e ReviewVerdict estão prontos)
- Não adiciona LangGraph nem troca de orquestrador
- Não implementa modo iterativo multi-agente (é Fase 7)

---

## 6. Estimativa de Esforço

| Sub-fase | Complexidade | Arquivos Novos | Arquivos Modificados |
|---|---|---|---|
| 6.0 Worktree | Média | 1 (`worktree.py`) | 1 (`execution_loop.py`) |
| 6.1 Bridge Plan→Contract | Baixa | 1 (`skills/contrato.py`) | 0 |
| 6.2 Bridge Loop→Reviewer | Média | 0 | 2 (`execution_loop.py`, `enforcement.py`) |
| 6.3 CLI Unificada | Baixa | 1 (`skills/run.py`) | 1 (`__main__.py`) |
| 6.4 Suite Integração | Média | 1 (`test_pipeline.py`) | 1 (`eval_prompts.py`) |

---

## 7. Log de Atualizações

| Data | Mudança | Autor |
|---|---|---|
| 2026-07-23 | Plano criado | Claude + Usuário |

---

*Após a Fase 6, o sistema estará pronto para uso real: um comando, execução segura, auditoria automática.*
