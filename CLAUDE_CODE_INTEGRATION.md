# Integração com Claude Code

## Visão Geral

O sistema multiagentes expõe **skills** que podem ser usadas diretamente do Claude Code ou OpenCode.

## Skills Disponíveis

### /plano
Gera plano de implementação validado.

```bash
# Via CLI
python -m src plano "Adicionar autenticação JWT"

# Via Python
from src.skills import skill_plano
resultado = skill_plano(objetivo="Adicionar autenticação JWT")
```

### /auditoria
Audita código com verificação adversarial.

```bash
# Via CLI
python -m src auditoria src/ bugs,security

# Via Python
from src.skills import skill_auditoria
resultado = skill_auditoria(caminho_codigo="src/", dimensoes=["bugs", "security"])
```

### /implementar
Implementa plano com geração de código.

```bash
# Via CLI
python -m src implementar plano.json src/

# Via Python
from src.skills import skill_implementar
resultado = skill_implementar(plano=plano_dict, output_dir="src/")
```

## Workflows Compostos

### Planejar e Implementar

```
/plano "Adicionar feature X"
    ↓ (plano gerado e validado)
/implementar <plano>
    ↓ (código gerado e verificado)
(resultado pronto para revisão)
```

### Auditoria Completa

```
/auditoria src/
    ↓ (findings + verdicts + completude)
(corrigir manualmente ou com Claude Code)
```

## Integração via Skills Manifest

O arquivo [`skills/manifest.yaml`](skills/manifest.yaml) descreve as skills para integração automática.

### Estrutura do Manifest

```yaml
skills:
  - name: "plano"
    displayName: "/plano"
    description: "Gera plano de implementação validado"
    handler: "src.skills.plano:skill_plano"
    parameters: [...]
    examples: [...]
```

## Uso Típico com Claude Code

### Fluxo 1: Planejamento + Manual

```
Você: /plano "Adicionar autenticação JWT"

Sistema: Retorna plano validado
Você: Revisa o plano
Você: Implementa manualmente (com assistência do Claude Code)
```

### Fluxo 2: Planejamento + Delegação

```
Você: /plano "Adicionar autenticação JWT"

Sistema: Retorna plano validado
Você: /implementar <plano>

Sistema: Gera código verificado
Você: Revisa e aprova
```

### Fluxo 3: Auditoria Pontual

```
Você: /auditoria src/

Sistema: Retorna findings + verdicts
Você: Corrige problemas com assistência do Claude Code
```

## Padrões de Uso

| Situação | Skill | Sequência |
|----------|-------|-----------|
| Nova feature | /plano | → revisa → implementa manual |
| Refatoração complexa | /plano | → /implementar |
| Code review | /auditoria | → corrige |
| Bug hunting | /auditoria bugs | → corrige |
| Security audit | /auditoria security | → corrige |

## Output das Skills

Todas as skills retornam um dict com:

```python
{
    "sucesso": bool,
    "...": ...,  # Dados específicos da skill
    "tokens_totais": int  # Tokens consumidos
}
```

## Configuração

### Variáveis de Ambiente

```env
# .env
ZAI_API_KEY=your_key_here
ZAI_BASE_URL=https://api.z.ai/v1
ZAI_MODEL=claude-sonnet-4-6
```

### Modelos

O sistema usa **Sonnet 4.6** por padrão para economia de tokens, mas pode ser configurado por agente em [`config/agents.yaml`](config/agents.yaml).

## Próximos Passos

- [ ] Testar skills com casos reais
- [ ] Otimizar prompts baseado em resultados
- [ ] Adicionar mais dimensões de auditoria
- [ ] Implementar workflows mais complexos
