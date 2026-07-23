# Sistema Multiagentes - Guia Claude Code

## 🎯 O Que Este Sistema Faz

Sistema multiagentes especializado para:
- **Planejamento:** Gera e valida planos de implementação
- **Auditoria:** Revisa código com verificação adversarial (bugs, security, performance)
- **Implementação:** Gera código a partir de planos

## 📦 Skills Disponíveis

```
/plano        - Gera e refina planos estratégicos
/auditoria    - Audita código com contestação adversarial
/implementar  - Implementa código a partir de planos
```

## 🚀 Como Usar no Claude Code

### 1️⃣ Instalação (Primeira Vez)

```bash
# No terminal, dentro do projeto:
pip install -e .
```

### 2️⃣ Usando as Skills

#### Gerar um Plano
```
/plano Preciso criar uma API REST em FastAPI com autenticação JWT
```

O sistema irá:
1. Gerar um plano inicial
2. Validar o plano
3. Verificar dependências
4. Refinar se necessário
5. Retornar plano validado pronto para implementação

#### Auditar Código
```
/auditoria src/ --dimensoes bugs,security
```

O sistema irá:
1. Ler código do repositório
2. Dividir em chunks se necessário
3. Auditores trabalham em paralelo (bugs + security)
4. Verificadores adversariais contestam findings
5. Meta-auditor verifica completude
6. Retorna report consolidado

#### Implementar Código
```
/implementar --plano "dados_do_plano_ou_arquivo.json"
```

O sistema irá:
1. Ler o plano
2. Gerar código para cada passo
3. Verificar implementação
4. Retornar arquivos gerados

## 🏗️ Arquitetura

### Modelos Configurados
- **Auditores:** GLM-5.2 (contexto longo, análise profunda)
- **Verificadores:** DeepSeek v4-pro (reflexão adversarial)
- **Orquestrador:** GPT-OSS 120B via Groq (rápido, estratégico)

### Workflow de Auditoria
```
Código → ContextManager → [Auditores Paralelos] → [Verificadores Adversariais] → Meta-auditor → Report
```

## 💡 Fluxo de Trabalho Típico

### Opção 1: Claude Code Implementa
```
Você: /plano Criar sistema de autenticação
[Agente gera plano validado]

Você: /auditoria src/auth/ --dimensoes bugs,security
[Agentes auditam código existente]

Você: [Implementa você mesmo usando o plano]
Claude Code: Implementa com base no plano
```

### Opção 2: Agentes Implementam
```
Você: /plano Criar API de usuários
[Agente gera plano]

Você: /implementar --plano "plano_gerado.json"
[Agentes geram código]

Você: /auditoria src/users/ --dimensoes bugs,security,performance
[Agentes auditam código gerado]
```

## 🔧 Configuração

As APIs estão configuradas em `.env`:
- ✅ ZAI (GLM-5.2)
- ✅ Groq (GPT-OSS 120B)
- ✅ DeepSeek v4-pro

## 📁 Estrutura do Projeto

```
src/
├── agents/          # Agentes especializados
│   ├── audit/       # BugHunter, SecAudit, PerfAnalyst
│   ├── verify/      # BugRefuter, SecSkeptic, PerfDoubter, CompletenessCheck
│   ├── planning/    # PlanCreator, PlanValidator, DependencyChecker
│   └── codegen/     # CodeGen, CodeVerifier
├── orchestration/   # Router, ContextManager, HybridRouter
├── schemas/         # Pydantic outputs
├── prompts/         # Templates .prompty
└── skills/         # /plano, /auditoria, /implementar
```

## 🎯 Exemplos de Uso

### Auditoria Completa
```
/auditoria src/ --dimensoes bugs,security,performance
```

### Planejamento Estratégico
```
/plano Preciso refatorar o sistema de payments para suportar múltiplas gateways
```

### Iteração Rápida
```
/plano Adicionar logging estruturado
[Usa o plano para implementar]
/auditoria src/logging/ --dimensoes bugs
```

## 💪 Benefícios

- **Verificação Adversarial:** Dois modelos conferem cada finding
- **Contexto Grande:** Processa repositórios inteiros com chunking
- **Especialização:** Cada agente é expert em sua dimensão
- **Meta-auditoria:** Garante que nada foi deixado de fora

## 🔍 Quando Usar Cada Skill

| Skill | Quando Usar |
|-------|-------------|
| `/plano` | Antes de codificar, para estratégia |
| `/auditoria` | Após implementar, para qualidade |
| `/implementar` | Delegar geração de código repetitivo |

## 🚨 Importante

- As skills usam **modelos reais** (GLM-5.2, DeepSeek v4-pro), não Claude
- Orquestrador usa **Groq** para rapidez
- Sempre revise código gerado por agentes
- Use `/auditoria` antes de commit para código crítico
