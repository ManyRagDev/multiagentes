# 🚀 Usar Multiagentes em Qualquer Projeto

## ✅ Instalação Concluída!

O pacote `multiagentes` já está instalado globalmente no seu ambiente Python.

---

## 📖 Como Usar em Seus Projetos

### Método 1: Via Claude Code CLI

**1. Abra seu projeto no terminal:**
```bash
cd "C:\Users\emanu\Documents\Projetos\PostSpark 3"
claude
```

**2. No chat do Claude Code, use as skills:**

```
/plano Criar sistema de autenticação com JWT
```

```
/auditoria src/ --dimensoes bugs,security
```

```
/implementar --plano <dados_do_plano>
```

---

### Método 2: Via Python (Direto no Código)

Você também pode importar e usar as skills diretamente no seu código:

```python
from multiagentes import skill_plano, skill_auditoria, skill_implementar

# Gerar um plano
resultado_plano = skill_plano(
    tarefa="Criar API REST em FastAPI",
    contexto="Projeto e-commerce"
)

# Auditar código
resultado_auditoria = skill_auditoria(
    caminho_codigo="src/",
    dimensoes=["bugs", "security"],
    linguagem="python"
)

# Implementar
resultado_implementar = skill_implementar(
    plano=resultado_plano["plano"],
    diretorio_saida="src/generated"
)
```

---

### Método 3: Via Terminal (Scripts CLI)

**Para gerar um plano:**
```bash
cd "C:\Users\emanu\Documents\Projetos\PostSpark 3"
python -m multiagentes.skills.plano
```

**Para auditar código:**
```bash
python -m multiagentes.skills.auditoria src/ --dimensoes bugs,security
```

**Para implementar:**
```bash
python -m multiagentes.skills.implementar --plano plano.json
```

---

## 🎯 Exemplo Completo de Fluxo de Trabalho

### Cenário: Você está no projeto "PostSpark 3"

```bash
# 1. Abra o projeto
cd "C:\Users\emanu\Documents\Projetos\PostSpark 3"
claude

# 2. No chat do Claude Code, peça um plano
Você: /plano Preciso criar um módulo de envio de emails

# 3. Sistema gera plano validado
[Agentes geram e validam plano]

# 4. Você implementa (com ajuda do Claude Code)
Você: Implementa o plano acima
[Claude Code ajuda na implementação]

# 5. Audite o código
Você: /auditoria src/email/ --dimensoes bugs,security

# 6. Sistema retorna findings confirmados
[Agentes auditan, contestam, verificam completude]
```

---

## 🔧 Configuração de Ambiente

Se as skills não forem reconhecidas, adicione ao PYTHONPATH:

```bash
# Windows (PowerShell)
$env:PYTHONPATH += ";C:\Users\emanu\Documents\Projetos\multiagentes\src"

# Windows (CMD)
set PYTHONPATH=%PYTHONPATH%;C:\Users\emanu\Documents\Projetos\multiagentes\src

# Adicione ao seu profile do PowerShell para persistir:
# Notepad $PROFILE
# Adicione: $env:PYTHONPATH += ";C:\Users\emanu\Documents\Projetos\multiagentes\src"
```

---

## 📁 Estrutura de Skills

```
multiagentes/
├── skills/
│   ├── plano.py         → /plano
│   ├── auditoria.py     → /auditoria
│   └── implementar.py   → /implementar
```

---

## 💡 Dicas de Uso

1. **Planeje antes de codificar**: Use `/plano` para tarefas complexas
2. **Audite antes de commit**: Use `/auditoria` em código crítico
3. **Combine com Claude Code**: Use agentes para estratégia, Claude para implementação
4. **Itere rapidamente**: Plano → Implementação → Auditoria → Refinamento

---

## 🎮 Comandos Disponíveis

| Comando | Uso | Exemplo |
|---------|-----|---------|
| `/plano` | Gerar planos estratégicos | `/plano Criar API de pagamentos` |
| `/auditoria` | Auditar código | `/auditoria src/ --dimensoes bugs,security` |
| `/implementar` | Implementar código | `/implementar --plano dados.json` |

---

## ⚡ Comece Agora Mesmo

No seu projeto "PostSpark 3":

```bash
cd "C:\Users\emanu\Documents\Projetos\PostSpark 3"
claude
```

E no chat:
```
/plano Criar uma função que valida e formatam CPF
```

**É só isso!** 🚀
