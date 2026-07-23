# 🚀 INSTALAÇÃO COMPLETA - Use Multiagentes em Qualquer Projeto

## ✅ Status: INSTALADO E PRONTO!

O pacote `multiagentes` está instalado no seu Python.

---

## 📖 3 Formas de Usar

### Forma 1: Copiando o Script (Mais Simples)

**Copie o script `claude_skills.py` para qualquer projeto:**

```bash
# Copie do multiagentes para seu projeto
copy "C:\Users\emanu\Documents\Projetos\multiagentes\claude_skills.py" "C:\Users\emanu\Documents\Projetos\PostSpark 3\"

# No seu projeto
cd "C:\Users\emanu\Documents\Projetos\PostSpark 3"

# Use!
python claude_skills.py plano "Criar API de autenticação"
python claude_skills.py auditoria src/ bugs,security
```

---

### Forma 2: Chamando Direto do Multiagentes

```bash
# Em qualquer projeto, chame o script direto:
python "C:\Users\emanu\Documents\Projetos\multiagentes\claude_skills.py" plano "Criar função de validação"

# Ou para auditoria:
python "C:\Users\emanu\Documents\Projetos\multiagentes\claude_skills.py" auditoria "C:\Users\emanu\Documents\Projetos\PostSpark 3\src" bugs,security
```

---

### Forma 3: Integrando com Claude Code (Recomendado)

**1. Crie um alias no seu profile do PowerShell:**

```powershell
# Edite seu profile
notepad $PROFILE

# Adicione:
function multiagentes { & python "C:\Users\emanu\Documents\Projetos\multiagentes\claude_skills.py" $args }
```

**2. Agora em qualquer projeto:**

```bash
cd "C:\Users\emanu\Documents\Projetos\PostSpark 3"

# Use direto:
multiagentes plano "Criar sistema de autenticação"
multiagentes auditoria src/ bugs,security
```

---

## 🎯 Exemplo Prático - Fluxo Completo

### Você está no projeto "PostSpark 3":

```bash
# 1. Vá para o projeto
cd "C:\Users\emanu\Documents\Projetos\PostSpark 3"

# 2. Inicie o Claude Code
claude

# 3. No chat do Claude Code, peça um plano
Você: /plano Criar módulo de envio de emails

# 4. Use o script para gerar plano (se preferir)
# (Em outro terminal)
python claude_skills.py plano "Criar módulo de envio de emails"

# 5. Implemente com ajuda do Claude Code
Você: [Usa o plano gerado]

# 6. Audite quando terminar
Você: /auditoria src/email/ --dimensoes bugs,security

# Ou via script:
python claude_skills.py auditoria src/ bugs,security
```

---

## 💻 Comandos Disponíveis

### `/plano` - Gerar Planos

```bash
python claude_skills.py plano "Criar API REST em FastAPI"
```

**O que faz:**
- Gera plano estratégico
- Valida o plano
- Verifica dependências
- Retorna plano validado

---

### `/auditoria` - Auditar Código

```bash
python claude_skills.py auditoria <caminho> <dimensoes>
```

**Exemplos:**
```bash
# Auditoria completa
python claude_skills.py auditoria src/ bugs,security,performance

# Apenas bugs
python claude_skills.py auditoria main.py bugs

# Bugs e security
python claude_skills.py auditoria src/auth bugs,security
```

**O que faz:**
- Lê código do diretório
- Auditores trabalham em paralelo
- Verificadores contestam findings
- Meta-auditor verifica completude
- Retorna report consolidado

---

### `/implementar` - Implementar (Em Desenvolvimento)

```bash
python claude_skills.py implementar --plano plano.json
```

**Status:** Em desenvolvimento
**Workaround:** Implemente você mesmo com ajuda do Claude Code

---

## 🔧 Troubleshooting

### Erro: "No module named 'src'"

**Solução:** Use o script `claude_skills.py` - ele já configura o PATH corretamente.

### Erro: "API key inválida"

**Solução:** Verifique `.env` no multiagentes:
```bash
notepad "C:\Users\emanu\Documents\Projetos\multiagentes\.env"
```

### Erro: "Caminho não encontrado"

**Solução:** Use caminhos absolutos ou relativos corretos:
```bash
# Absoluto
python claude_skills.py auditoria "C:\Users\emanu\Documents\Projetos\PostSpark 3\src" bugs

# Relativo (estando dentro do projeto)
python claude_skills.py auditoria src/ bugs
```

---

## 📁 Arquivos Importantes

```
multiagentes/
├── claude_skills.py        ← USE ESTE em qualquer projeto!
├── .env                    ← Configurações de API
├── src/skills/            ← Implementação das skills
└── COMO_USAR_GLOBAL.md     ← Este guia
```

---

## ⚡ Comece Agora

No seu projeto "PostSpark 3":

```bash
cd "C:\Users\emanu\Documents\Projetos\PostSpark 3"

# Copie o script (primeira vez só)
copy "C:\Users\emanu\Documents\Projetos\multiagentes\claude_skills.py" .

# Teste
python claude_skills.py plano "Criar função que valida CPF"
```

**É só isso!** 🚀

---

## 🎓 Dicas Avançadas

### 1. Crie um atalho global (PowerShell)

```powershell
# No profile $PROFILE
function multiagentes { & python "C:\Users\emanu\Documents\Projetos\multiagentes\claude_skills.py" $args }

# Use em qualquer lugar
multiagentes plano "Criar feature X"
multiagentes auditoria src/ bugs,security
```

### 2. Integre com VS Code

Crie tasks no `.vscode/tasks.json`:
```json
{
  "version": "2.0.0",
  "tasks": [
    {
      "label": "Multiagentes: Plano",
      "type": "shell",
      "command": "python",
      "args": [
        "C:\\Users\\emanu\\Documents\\Projetos\\multiagentes\\claude_skills.py",
        "plano",
        "${input:tarefa}"
      ]
    }
  ]
}
```

### 3. Combine com Git Hooks

```bash
# Pre-commit hook
python claude_skills.py auditoria src/ bugs | grep "CRITICAL" && exit 1
```

---

**🎯 Sistema pronto para uso em todos os seus projetos!**
