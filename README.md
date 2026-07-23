# Multiagentes

Sistema multiagentes para perícia/auditoria de código com verificação adversarial.

## Visão Geral

Sistema de agentes especializados que trabalham em conjunto para:

- **Planejar**: Criar planos de implementação validados
- **Auditar**: Analisar código em múltiplas dimensões (bugs, segurança, performance)
- **Verificar**: Verificação adversarial para confirmar findings
- **Implementar**: Gerar código a partir de planos

## Arquitetura

```
┌─────────────────────────────────────────────────────────────┐
│                    Skills (Interface)                       │
│  /plano | /auditoria | /implementar                        │
└──────────────────────┬──────────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
┌──────────────────┐         ┌──────────────────┐
│   Planejamento   │         │    Auditoria     │
│  PlanCreator     │         │  BugHunter       │
│  PlanValidator   │         │  SecAudit        │
│  DependencyCheck │         │  PerfAnalyst     │
└──────────────────┘         └──────────────────┘
                                       │
                              ┌────────┴────────┐
                              ▼                 ▼
                       ┌──────────┐      ┌──────────┐
                       │Verifiers │      │ Completeness│
                       │Adversarial│      │   Check    │
                       └──────────┘      └──────────┘
```

## Instalação

```bash
# Criar venv
python -m venv venv
source venv/bin/activate  # Linux/Mac
# ou
venv\Scripts\activate  # Windows

# Instalar dependências
pip install -e .
```

## Configuração

Criar arquivo `.env`:

```env
ZAI_API_KEY=your_key_here
ZAI_BASE_URL=https://api.z.ai/v1
ZAI_MODEL=claude-sonnet-4-6
```

## Uso

### Via Skills (Claude Code)

```bash
/plano "Adicionar autenticação JWT"
/auditoria
/implementar <plano>
```

### Via Python

```python
from src.skills.plano import skill_plano

resultado = skill_plano(
    objetivo="Adicionar autenticação JWT",
    contexto="API em FastAPI"
)

print(resultado["plano"])
```

## Estrutura

```
multiagentes/
├── src/
│   ├── schemas/          # Tipos Pydantic
│   ├── agents/           # Implementação dos agentes
│   ├── skills/           # Skills expostas
│   ├── orchestration/    # Orquestrador
│   └── prompts/          # Prompts versionados
├── config/
│   └── agents.yaml       # Catálogo de agentes
└── tests/
    └── e2e/              # Testes
```

## Documentação

- [IMPLEMENTACAO.md](IMPLEMENTACAO.md) - Detalhes da implementação
- [src/prompts/](src/prompts/) - Prompts dos agentes

## License

MIT
