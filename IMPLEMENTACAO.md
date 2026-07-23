# Documentação de Implementação - Sistema Multiagentes

> Data de início: 2025-06-30
> Status: Em andamento

## Visão Geral

Sistema multiagentes para perícia/auditoria de código e planejamento, com verificação adversarial e integração via skills com Claude Code.

---

## Estrutura do Projeto

```
multiagentes/
├── src/
│   ├── schemas/              # Schemas Pydantic (tipos de dados)
│   │   ├── __init__.py
│   │   ├── plano.py          # Plan, Step, PlanProblem, PlanValidation
│   │   ├── findings.py       # Finding, Severity, Verdict, CodeReport, CompletenessReport
│   │   └── agent.py          # AgentConfig, AgentOutput
│   ├── agents/               # Implementação dos agentes
│   │   ├── base/             # BaseAgent (a implementar)
│   │   ├── planning/         # PlanCreator, PlanValidator, DependencyChecker
│   │   ├── audit/            # BugHunter, SecAudit, PerfAnalyst
│   │   ├── verify/           # BugRefuter, SecSkeptic, PerfDoubter, CompletenessCheck
│   │   └── codegen/          # CodeGen, CodeVerifier
│   ├── skills/               # Skills expostas ao Claude Code
│   │   ├── plano.py          # Skill /plano
│   │   ├── auditoria.py      # Skill /auditoria
│   │   └── implementar.py    # Skill /implementar
│   ├── orchestration/        # Orquestrador com LangGraph
│   │   └── base.py
│   └── prompts/              # Prompts versionados
│       ├── planning/
│       ├── audit/
│       ├── verify/
│       └── codegen/
├── config/
│   └── agents.yaml           # Catálogo de agentes
├── tests/
│   └── e2e/                  # Testes end-to-end
├── pyproject.toml            # Dependências
├── .env                      # Variáveis de ambiente
└── IMPLEMENTACAO.md          # Este arquivo
```

---

## Fase 1: Fundação ✅ (Completa)

### 1.1 Estrutura de Diretórios ✅
Criados todos os diretórios necessários para o projeto.

### 1.2 Schemas Pydantic ✅

#### `plano.py`
- **Step**: Passo individual de um plano
  - `id`: ordinal
  - `descricao`: o que fazer
  - `depende_de`: IDs de passos anteriores
  - `riscos`: o que pode dar errado
  - `rollback`: como desfazer

- **Plan**: Plano completo
  - `objetivo`: qual o objetivo
  - `pre_condicoes`: o que é necessário antes
  - `passos`: lista de Step
  - `pos_condicoes`: como saber que terminou

- **PlanProblem**: Problema encontrado em validação
  - `tipo`: categoria (ordem, falta_passo, dependencia, etc)
  - `passo`: ID do passo (opcional)
  - `descricao`: descrição do problema

- **PlanValidation**: Resultado da validação
  - `aprovado`: true se sem problemas críticos
  - `problemas`: lista de PlanProblem
  - `passos_faltando`: passos que deveriam estar
  - `sugestoes`: melhorias opcionais

#### `findings.py`
- **Severity**: Enum (CRITICAL, HIGH, MEDIUM, LOW, INFO)

- **Finding**: Problema/observação em código
  - `tipo`: bug, security, performance, architecture
  - `arquivo`, `linha`: localização
  - `titulo`, `descricao`: o que é
  - `severidade`: Severity
  - `evidencia`: snippet ou explicação

- **Verdict**: Veredito adversarial
  - `finding`: o finding original
  - `confirmado`: true se real
  - `refutacao`: por que foi refutado

- **CodeReport**: Report consolidado
  - `findings`: todos encontrados
  - `verdicts`: vereditos adversariais
  - `resumo`: executivo

- **CompletenessReport**: Meta-auditoria
  - `cobertura_arquivos`: cobertura por arquivo
  - `cobertura_dimensoes`: cobertura por dimensão
  - `faltando`: gaps identificados
  - `conclusao`: completa? justificativa

#### `agent.py`
- **AgentConfig**: Configuração de agente
  - `nome`, `role`: identificação
  - `model`, `temperature`: config de modelo
  - `prompt_file`/`prompt_template`: prompt
  - `dominio`: planning, audit, verify, codegen
  - `output_schema`: schema Pydantic

- **AgentOutput**: Output de agente
  - `agente`: nome
  - `sucesso`: bool
  - `output`: dados estruturados
  - `raw_output`: bruto do modelo
  - `erro`: mensagem se falhou
  - `tokens_usados`: consumo

### 1.3 Catálogo YAML ✅

#### `config/agents.yaml`
- **models**: Mapeamento de nomes para IDs de modelo
- **defaults**: Configurações padrão
- **agentes**: Catálogo completo por domínio
  - `planning`: PlanCreator, PlanValidator, DependencyChecker
  - `audit`: BugHunter, SecAudit, PerfAnalyst
  - `verify`: BugRefuter, SecSkeptic, PerfDoubter, CompletenessCheck
  - `codegen`: CodeGen, CodeVerifier
- **workflows**: Grupos predefinidos de agentes

**Modelos escolhidos (economia de tokens):**
- Criativos: Sonnet 4.6 (temp 0.3-0.4)
- Precisão: Sonnet 4.6 (temp 0.2)
- Mecânicos: Haiku 4.5 (temp 0.1)

---

## Fase 2: Core ✅ (Completa)

### 2.1 BaseAgent ✅
Classe base para todos os agentes:
- Carregar configuração (AgentConfig)
- Carregar prompt de arquivo
- Formatar prompt com variáveis {{var}}
- Fazer chamada à API OpenAI-compatível
- Parsear output para schema Pydantic
- Tratamento de erros com retry

**Arquivo**: `src/agents/base/agent.py`

### 2.2 Orquestrador Base ✅
Coordena execução de múltiplos agentes:
- Execução sequencial (com contexto entre steps)
- Execução paralela (ThreadPoolExecutor)
- Resolução de referências {{output.campo}}
- Agregação de resultados e erros
- Contagem de tokens

**Arquivo**: `src/orchestration/base.py`

---

## Fase 3-7: Skills e Integração

### Skill /plano ✅ (Completa)
- PlanCreator + PlanValidator + DependencyChecker
- Loop de refinamento (max 3x)
- Arquivo: `src/skills/plano.py`
- Uso: `python -m src plano "objetivo"`

**Workflow:**
```
┌──────────────┐     ┌──────────────┐     ┌──────────────┐
│ PlanCreator  │ ──→ │PlanValidator │ ──→ │DependencyCheck│
└──────┬───────┘     └──────┬───────┘     └──────┬───────┘
       │                    │                    │
       └────────────────────┴────────────────────┘
                              │
                    ┌─────────┴─────────┐
                    │ Aprovado?        │
                    │ Se não:          │
                    │ Refinar com      │
                    │ feedback (loop)  │
                    └──────────────────┘
```

### Skill /auditoria ✅ (Completa)
- Auditores em paralelo (BugHunter, SecAudit, PerfAnalyst)
- Verificadores adversariais (BugRefuter, SecSkeptic, PerfDoubter)
- Meta-check (CompletenessCheck)
- Arquivo: `src/skills/auditoria.py`
- Uso: `python -m src auditoria <caminho> [dimensoes]`

**Workflow:**
```
┌─────────────────────────────────────────────────────────────┐
│                    Código Alvo                               │
└────────────────────────┬────────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        ▼                ▼                ▼
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│  BugHunter   │  │   SecAudit   │  │  PerfAnalyst │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                  ┌───────────────┐
                  │  Findings     │
                  └───────┬───────┘
                          │
        ┌─────────────────┼─────────────────┐
        ▼                 ▼                 ▼
┌──────────────┐  ┌──────────────┐  ┌───────────┐
│ BugRefuter   │  │ SecSkeptic   │  │ Completeness│
│(adversarial) │  │(adversarial) │  │ Check      │
└──────┬───────┘  └──────┬───────┘  └──────┬─────┘
       │                 │                 │
       └─────────────────┼─────────────────┘
                         ▼
                  ┌───────────────┐
                  │  Verdicts     │
                  │  Confirmados  │
                  └───────────────┘
```

### Skill /implementar (Pendente)

### Skill /auditoria (Pendente)
- Auditores em paralelo (BugHunter, SecAudit, PerfAnalyst)
- Verificadores adversariais
- Meta-check (CompletenessCheck)

### Skill /implementar (Pendente)
- CodeGen + CodeVerifier
- Validação vs plano original

---

## Dependências

```toml
[project]
name = "multiagentes"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "openai>=1.0",           # Cliente da API
    "pydantic>=2.0",         # Schemas e validação
    "pydantic-settings>=2.0",
    "langgraph>=0.2",        # Orquestração
    "python-dotenv>=1.0",    # Variáveis de ambiente
    "rich>=13.0",            # Logging bonito
    "pyyaml>=6.0",           # Config
]
```

---

## Variáveis de Ambiente

```env
# .env
ZAI_API_KEY=your_key_here
ZAI_BASE_URL=https://api.z.ai/v1
ZAI_MODEL=claude-sonnet-4-6
```

---

## Histórico de Mudanças

| Data | Fase | Status |
|------|------|--------|
| 2025-06-30 | Fase 1: Fundação | ✅ Completa |
| 2025-06-30 | Fase 2: Core | ✅ Completa |
| 2025-06-30 | Fase 3: Skill /plano | ✅ Completa |
| 2025-06-30 | Fase 4: Skill /auditoria | ✅ Completa |
| 2025-06-30 | Fase 5: Skill /implementar | ✅ Completa |
| 2025-06-30 | Fase 6: Integração | ✅ Completa |
| 2025-06-30 | Fase 7: Testes | ✅ Completa |

---

## Próximos Passos Imediatos

1. ✅ Criar estrutura de diretórios
2. ✅ Criar schemas Pydantic
3. ✅ Criar catálogo YAML
4. ✅ Criar BaseAgent
5. ✅ Criar Orquestrador Base
6. ✅ Implementar skill /plano
7. ✅ Implementar skill /auditoria
8. ✅ Implementar skill /implementar
9. ✅ Testes end-to-end

## 🎉 Projeto Completo!

Todas as 7 fases foram implementadas. O sistema multiagentes está funcional e pronto para uso.

---

## Detalhes da Skill /plano

### Arquivos Criados
- `src/agents/planning/creator.py` - PlanCreatorAgent
- `src/agents/planning/validator.py` - PlanValidatorAgent
- `src/agents/planning/dependency_check.py` - DependencyCheckerAgent
- `src/skills/plano.py` - Skill orquestradora

### Uso

```python
from src.skills import skill_plano

# Gerar plano simples
resultado = skill_plano(
    objetivo="Adicionar autenticação JWT",
    contexto="API em FastAPI"
)

if resultado["sucesso"]:
    print(resultado["plano"])
else:
    print(f"Erro: {resultado['erro']}")
```

```bash
# Via CLI
python -m src plano "Adicionar autenticação JWT"
```

### Output

```python
{
    "sucesso": True,
    "plano": {
        "objetivo": "Adicionar autenticação JWT",
        "pre_condicoes": ["JWT secret configurado"],
        "passos": [
            {
                "id": 1,
                "descricao": "Instalar dependências",
                "depende_de": [],
                "riscos": ["Conflito de versões"],
                "rollback": "requirements.txt backup"
            },
            # ...
        ],
        "pos_condicoes": ["Testes passando"]
    },
    "validacao": {
        "aprovado": True,
        "problemas": [],
        "passos_faltando": [],
        "sugestoes": []
    },
    "tentativas": 1,
    "tokens_totais": 1234
}
```

---

## Detalhes da Skill /auditoria

### Arquivos Criados
- `src/agents/audit/bug_hunter.py` - BugHunterAgent
- `src/agents/audit/security.py` - SecAuditAgent
- `src/agents/audit/performance.py` - PerfAnalystAgent
- `src/agents/verify/bug_refuter.py` - BugRefuterAgent
- `src/agents/verify/security_skeptic.py` - SecSkepticAgent
- `src/agents/verify/performance_doubter.py` - PerfDoubterAgent
- `src/agents/verify/completeness_check.py` - CompletenessCheckAgent
- `src/skills/auditoria.py` - Skill orquestradora

### Uso

```python
from src.skills import skill_auditoria

# Auditar projeto
resultado = skill_auditoria(
    caminho_codigo="src/",
    dimensoes=["bugs", "security", "performance"],
    linguagem="python"
)

if resultado["sucesso"]:
    print(resultado["resumo"])
    print(f"Findings confirmados: {len(resultado['verdicts'])}")
else:
    print(f"Erro: {resultado['erro']}")
```

```bash
# Via CLI - todas as dimensões
python -m src auditoria src/

# Via CLI - apenas bugs e security
python -m src auditoria src/ bugs,security
```

### Output

```python
{
    "sucesso": True,
    "findings": [
        {
            "tipo": "bug",
            "arquivo": "src/handlers/auth.py",
            "linha": 42,
            "titulo": "Off-by-one em loop",
            "descricao": "Loop acessa items[i] onde i pode ser len(items)",
            "severidade": "high",
            "evidencia": "for i in range(len(items)):"
        }
    ],
    "verdicts": [
        {
            "finding": {...},
            "confirmado": True,
            "refutacao": null
        }
    ],
    "completude": {
        "cobertura_arquivos": {
            "total_arquivos": 10,
            "arquivos_analisados": ["src/handlers/auth.py", ...],
            "arquivos_ignorados": [],
            "arquivos_relevantes_nao_analisados": []
        },
        "cobertura_dimensoes": {
            "bugs": "completa",
            "security": "completa",
            "performance": "parcial"
        },
        "faltando": [],
        "conclusao": {
            "completa": True,
            "justificativa": "Todas as dimensões foram analisadas adequadamente"
        }
    },
    "tokens_totais": 4567,
    "resumo": "📊 Auditoria de Código\n\n• 5 findings encontrados\n• 3 confirmados após verificação adversarial\n..."
}
```

---

## Detalhes da Skill /implementar

### Arquivos Criados
- `src/agents/codegen/generator.py` - CodeGenAgent
- `src/agents/codegen/verifier.py` - CodeVerifierAgent
- `src/skills/implementar.py` - Skill orquestradora
- `src/schemas/findings.py` - Adicionados: CodeOutput, CodeVerification

### Uso

```python
from src.skills import skill_implementar
from src.schemas import Plan

# Criar ou carregar um plano
plano = Plan(
    objetivo="Adicionar autenticação JWT",
    pre_condicoes=["JWT secret configurado"],
    passos=[
        {
            "id": 1,
            "descricao": "Instalar dependências",
            "depende_de": [],
            "riscos": ["Conflito de versões"],
            "rollback": "requirements.txt backup"
        },
        {
            "id": 2,
            "descricao": "Criar módulo de autenticação",
            "depende_de": [1],
            "riscos": ["Breaking changes"],
            "rollback": "Reverter commit"
        }
    ],
    pos_condicoes=["Testes passando"]
)

# Implementar plano
resultado = skill_implementar(
    plano=plano,
    output_dir="src/auth/",
    linguagem="python"
)

if resultado["sucesso"]:
    print(f"✅ {len(resultado['arquivos'])} arquivos gerados")
else:
    print(f"❌ {resultado['erro']}")
```

```bash
# Via CLI - implementar a partir de arquivo JSON
python -m src implementar plano.json src/

# plano.json exemplo:
{
    "objetivo": "Adicionar autenticação JWT",
    "pre_condicoes": ["JWT secret configurado"],
    "passos": [...],
    "pos_condicoes": ["Testes passando"]
}
```

### Output

```python
{
    "sucesso": True,
    "arquivos": [
        {
            "caminho": "src/auth/jwt.py",
            "conteudo": "def verify_token(token): ...",
            "passo_implementado": 2
        },
        {
            "caminho": "requirements.txt",
            "conteudo": "pyjwt==2.8.0...",
            "passo_implementado": 1
        }
    ],
    "resumo": "Implementada autenticação JWT com verificação de token e middleware",
    "verificacao": {
        "aprovado": True,
        "arquivos_verificados": [
            {
                "caminho": "src/auth/jwt.py",
                "passo_correspondente": 2,
                "correspondencia": "completa",
                "problemas": []
            }
        ],
        "passos_faltando": [],
        "problemas_codigo": [],
        "sugestoes": []
    },
    "tentativas": 1,
    "tokens_totais": 2345
}
```

### Workflow

```
┌─────────┐     ┌──────────┐     ┌─────────────┐     ┌─────────┐
│  Plano  │ ──→ │ CodeGen  │ ──→ │CodeVerifier │ ──→ │ Output  │
└─────────┘     └──────────┘     └─────────────┘     └─────────┘
                           │                           │
                      não aprovado              código
                           │                   validado
                    ┌──────┴──────┐
                    │  Refinar    │
                    └─────────────┘
```
