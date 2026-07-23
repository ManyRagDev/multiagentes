# 📋 PLANO FASE 5 — Engenharia de Prompt por Princípios

> **Criado:** 2026-07-22
> **Status:** ✅ CONCLUÍDO — Todas as fases (5.0 a 5.5) implementadas e validadas
> **Origem:** Extração de princípios do system prompt Claude Fable 5 + pesquisas de harness open source
> **Filosofia:** Cirúrgico (tocar apenas onde gera efeito mensurável) + Sem gaps (cada princípio = instrução + mecanismo + teste)

---

## 0. Filosofia do Plano

**Cirúrgico** = tocar apenas nos pontos onde cada princípio gera efeito mensurável.
**Sem gaps** = nenhum princípio vira "enfeite de prompt"; cada um recebe os três pilares que o sustentam: **instrução no prompt + mecanismo no código + teste que comprova**. Um princípio sem um dos três é um gap. A tabela de rastreabilidade (§1) é o coração do plano — ela garante rastreabilidade total.

---

## 1. Tabela de Rastreabilidade (o núcleo anti-gap)

| # | Princípio | Agente/Componente | Mudança no Prompt | Mudança no Código | Teste que comprova |
|---|---|---|---|---|---|
| P1 | Hierarquia de autoridade | Todos + ExecutionLoop | Fragmento: "constraints > objetivo > conveniência" | DiffValidator já aplica; reforçar no loop | Tarefa com constraint conflitante → executor obedece a constraint |
| P2 | Exemplos bom/mau | Executor, Planner | 2 exemplos corretos + 1 anti-padrão cada | Nenhuma | Comparação qualitativa antes/depois |
| P3 | Decision tree de delegação | Planner | Árvore explícita de "delegar vs reter" | Alinhar ao TaskClassifier existente | Planner emite tier coerente com o classifier |
| P4 | Fail-safe (default-deny) | Executor | "Na dúvida, não altere; sinalize `needs_context`" | PermissionManager + DiffValidator já existem | Tarefa ambígua → `needs_context`, não chute |
| P5 | Contexto escasso | Planner | "Inclua o mínimo necessário" | TaskContract.context_snippets já existe | Contrato com snippets enxutos (≤ budget) |
| P6 | Provenance | Reviewer + Verdict | "Classifique: fato vs inferência" | `Verdict.kind: deterministic \| opinion` | Issue de teste falhado = deterministic; opinião = opinion |
| P7 | Anti-sycophancy | Reviewer | "Encontre problemas; aprove com evidência" | Loop trata aprovação sem evidência com suspeita | Código bom → aprova COM prova; ruim → rejeita |
| O1 | Self-check antes de emitir | Executor | Checklist final obrigatório | Parser tolerante a bloco de self-check | Menos retries de lint |
| O2 | Minimalismo de output | Executor | "Retorne APENAS o código/diff" | Parser extrai só o payload | Output limpo e parseável |
| O3 | Especificidade inversa | Planner + TaskContract | "Para LOCAL, especifique `required_behavior`" | `TaskContract.required_behavior: dict` | Contrato LOCAL tem tipos/defaults exatos |

**Regra de ouro:** se uma linha não tiver as três colunas preenchidas, ela não entra. É isso que evita gap.

---

## 2. Fases de Implementação

### Fase 5.0 — Fundação: fragmento de princípios compartilhado

**Objetivo:** Criar `src/prompts/_shared/principles.prompty` com o que é comum a todos os agentes (P1 hierarquia, P4 fail-safe, O2 minimalismo). Todo `.prompty` passa a incluir esse fragmento.

**Gap que evita:** inconsistência — cada agente interpretando autoridade de um jeito.

**Aceite:** os 3 agentes principais incluem o fragmento e se comportam de forma coerente num cenário de conflito.

**Status:** ✅ IMPLEMENTADA (2026-07-23)

**Resultado da validação:**
- Fragmento criado em `src/prompts/_shared/principles.prompty`
- Carregamento dinâmico no system prompt do Executor via cache de classe
- 7/7 princípios detectados no prompt final
- 2602 chars (~650 tokens) — dentro do orçamento de contexto

---

### Fase 5.1 — Executor (o de maior ROI imediato)

**Objetivo:** Reformular `src/prompts/codegen/generator.prompty` incorporando O1 (self-check), O2 (minimalismo), P2 (anti-padrões) e P4 (fail-safe). Ajustar o parser do `ExecutorAgent` para extrair apenas o payload de código, tolerando o bloco de self-check.

**Por que primeiro:** foi onde observamos retry por lint no teste do BMI. Self-check + minimalismo atacam exatamente isso.

**Gap que evita:** prompt pede minimalismo mas parser quebra com output limpo (por isso a mudança no parser acompanha).

**Aceite:** a tarefa BMI passa com 0 retries de lint; output vem sem preâmbulo.

**Status:** ✅ IMPLEMENTADA (2026-07-23)

**Resultado da validação (`scripts/eval_executor_prompts.py`):**
- Parser: 5/5 cenários sintéticos passaram (código limpo, needs_context, self_check+code, anti-padrão, multi-arquivo)
- System Prompt: 7/7 princípios presentes (P1, P2, P4, O1, O2 + instrução parser + allowed_files)
- Chamada real: Qwen gerou código limpo sem preâmbulo (339→325 chars, 14 chars economizados)
- Auto-recovery do llama-server funcionou automaticamente durante o teste
- Output: função `calculate_bmi` correta, sem self_check (confiança alta do modelo)

---

### Fase 5.2 — Planner (cérebro da delegação)

**Objetivo:** Reformular o `.prompty` do planning com P3 (decision tree de delegação alinhada ao `TaskClassifier`), P5 (contexto enxuto) e O3 (especificidade). Adicionar `required_behavior: dict` ao `TaskContract`.

**Gap que evita:** a decision tree existe no prompt mas o contrato não tem campo para capturá-la — por isso o schema muda junto.

**Aceite:** para uma tarefa LOCAL, o Planner emite contrato com `required_behavior` preenchido (tipos, formatos, defaults) e tier coerente.

**Status:** ✅ IMPLEMENTADA (2026-07-23)

**Resultado da validação (`scripts/eval_planner_prompts.py`):**
- Schema TaskContract: 3/3 casos passaram (preenchido, opcional, rejeição de campos desconhecidos via `extra=forbid`)
- Coerência Planner↔Classifier: 3/3 cenários concordaram (LOCAL/STRONG/MEDIUM)
- Prompt: 8/8 princípios presentes (P3 decision tree, P5 contexto enxuto, O3 especificidade inversa, fragmento compartilhado, exemplo BOM, anti-padrão, formato JSON puro, escape hatch `needs_clarification`)
- Prompt total: 4570 chars (~1142 tokens) — dentro do orçamento
- Novo arquivo: `src/schemas/contract.py` com `TaskContract` isolado e reutilizável
- Campo `required_behavior: Optional[dict]` adicionado (backward compatible)

---

### Fase 5.3 — Reviewer (ceticismo estrutural)

**Objetivo:** Reformular o `.prompty` do verify com P7 (anti-sycophancy) e P6 (provenance). Adicionar `kind: deterministic | opinion` ao schema `Verdict`.

**Gap que evita:** reviewer "acha" problemas que o Qwen tenta corrigir criando bugs reais. Com `kind`, o loop sabe o que é fato (bloqueia) e o que é opinião (sugere).

**Aceite:** diante de código correto, o reviewer aprova citando a evidência (testes passaram, critérios atendidos); diante de código ruim, rejeita com issue `deterministic`.

**Status:** ✅ IMPLEMENTADA E VALIDADA (2026-07-23)

**Resultado da validação (`scripts/eval_reviewer_prompts.py`):**
- Schema `ReviewVerdict`: 4/4 casos passaram (aprovação com evidência, aprovação suspeita, rejeição com issues mistas, rejeição de kind inválido).
- Propriedades derivadas: `has_blocking_issues` e `is_suspicious_approval` funcionam conforme esperado.
- System Prompt: 10/10 princípios presentes (P6 provenance, P7 anti-sycophancy, classificação deterministic/opinion, fragmento compartilhado, exemplo BOM, anti-padrão, schema JSON, decision tree).

---

### Fase 5.4 — Enforcement no loop (onde os princípios viram lei)

**Objetivo:** Ajustar o `ExecutionLoop` para:
- (a) aplicar P1 — constraint do contrato vence qualquer "interpretação" do executor
- (b) usar `Verdict.kind` — issues `deterministic` bloqueiam, `opinion` viram sugestão com peso
- (c) tratar aprovação sem evidência como suspeita (P7)

**Gap que evita:** princípios declarados no prompt mas não aplicados quando há conflito real.

**Aceite:** E2E com uma tarefa que tem constraint conflitante → o sistema respeita a constraint e o reviewer não aprova no "parece bom".

**Status:** ✅ IMPLEMENTADA E VALIDADA (2026-07-23)

**Resultado da validação (`scripts/eval_enforcement.py`):**
- `EnforcementEngine.evaluate()`: 7/7 cenários passaram (P7 aprovação sem evidência → retry, P7 com evidência → continue, P6 issue deterministic → retry, P6 só opinion → approve_with_warnings, P1 constraint violada → reject, P1 arquivo proibido → reject, Revisor escalou → escalate).
- `EnforcementEngine.check_output()`: 4/4 cenários passaram (modo leve P1 usado pelo ExecutionLoop sem revisor LLM).
- **Correção de acoplamento:** O `TaskContract` foi centralizado em `src/schemas/contract.py` e o `execution_loop.py` foi atualizado para usar a versão canônica, eliminando duplicação.

---

### Fase 5.5 — Suite de regressão de prompts

**Objetivo:** Criar `scripts/eval_prompts.py`: um conjunto pequeno de tarefas-padrão (uma LOCAL, uma MEDIUM, uma ambígua, uma com conflito) que roda os 3 agentes e registra métricas (retries, tier escolhido, `kind` das issues, limpeza do output).

**Gap que evita:** "melhorei o prompt mas quebrei outro comportamento" sem perceber.

**Aceite:** baseline registrado; qualquer mudança futura de prompt roda contra ele.

**Status:** ✅ IMPLEMENTADA (2026-07-23)

**Resultado da validação (`scripts/eval_prompts.py`):**
- Suite unificada executa 4 módulos em sequência: Executor → Planner → Reviewer → Enforcement
- 4/4 suites passaram com sucesso
- Encoding UTF-8 configurado explicitamente (subprocess + stdout reconfigure) para evitar UnicodeEncodeError no Windows CP1252
- Tempo total: ~55s (incluindo auto-recovery do llama-server)
- Output formatado para salvar baseline: `uv run python scripts/eval_prompts.py > logs/regression_baseline_YYYY-MM-DD.txt`

---

## 3. Ordem e Dependências

```
5.0 (fundação) ──┬──> 5.1 (Executor)  ──┐
                 ├──> 5.2 (Planner)   ──┼──> 5.4 (Enforcement) ──> 5.5 (Regressão)
                 └──> 5.3 (Reviewer)  ──┘
```

5.1, 5.2 e 5.3 são **paralelizáveis** após 5.0. 5.4 depende dos três (precisa dos schemas novos). 5.5 fecha o ciclo.

---

## 4. Riscos Mapeados e Mitigação

| Risco | Mitigação |
|---|---|
| Prompt ficar longo e estourar os 8k do Qwen | Fragmento compartilhado enxuto; exemplos curtos; medir tokens no 5.5 |
| Self-check virar "teatro" (modelo diz que checou sem checar) | Validar o efeito (menos retries), não a declaração |
| Anti-sycophancy tornar o reviewer agressivo demais | `kind` separa fato de opinião; opinião não bloqueia |
| Mudar schema e quebrar agentes existentes | Campos novos são opcionais com default; zero breaking change |

---

## 5. O Que Este Plano NÃO Faz (escopo protegido)

Não reescreve o orquestrador, não introduz LangGraph, não mexe no TierRouter nem no sistema de tools — tudo isso já está validado. Toca apenas em **prompts + 2 schemas (TaskContract, Verdict) + parser do ExecutorAgent + enforcement no ExecutionLoop**. Cirúrgico de verdade.

---

## 6. Princípios Extraídos (Referência Rápida)

### Do system prompt Claude Fable 5:
- **P1 Hierarquia:** regras de segurança > instruções do sistema > preferências do usuário > defaults
- **P2 Exemplos:** pares bom/mau são mais "executáveis" que abstrações para modelos menores
- **P3 Decision trees:** condições de parada explícitas em vez de regras vagas
- **P4 Fail-safe:** ações destrutivas negadas por padrão; na dúvida, opção mais segura
- **P5 Contexto escasso:** tokens como dinheiro; o que entra, o que sai, quando resumir
- **P6 Provenance:** distinguir `stated` (dito pelo usuário) de `observed`/`inferred`
- **P7 Anti-sycophancy:** proibição de validação cega; manter avaliação honesta sob pressão
- **O1 Self-check:** checklists internos antes de emitir resposta
- **O2 Minimalismo:** output mínimo necessário; sem preâmbulos, sem formatação decorativa
- **O3 Especificidade inversa:** quanto menor o modelo, mais estruturada a delegação

### Dos harnesses open source (Claude Code, Hermes, OpenCode, Cline, Roo):
- Registry de tools com schemas e handlers
- Permissão explícita e memorizada
- System prompts modulares (tiers estáveis/contextuais/voláteis)
- Git snapshots para rollback
- Event-driven core desacoplado
- Modos especializados (plan/build, code/architect)

---

## 7. Log de Atualizações

| Data | Mudança | Autor |
|---|---|---|
| 2026-07-22 | Plano criado e aprovado | Qwen3.8 + Usuário |
| 2026-07-23 | 5.0 + 5.1 + 5.2 implementadas e validadas | Qwen3.8 + Usuário |
| 2026-07-23 | 5.3 + 5.4 implementadas e validadas (Reviewer + Enforcement) | Qwen3.8 + Usuário |
| 2026-07-23 | 5.5 finalizada: suite de regressão unificada (`eval_prompts.py`) + bugfix encoding Windows | Claude + Usuário |

---

*Este plano é vivo. Atualize o status de cada fase ao concluir. A tabela de rastreabilidade (§1) deve ser revisada a cada sub-fase para garantir que nenhum pilar ficou descoberto.*
