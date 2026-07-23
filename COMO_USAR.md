# 🚀 Guia Rápido - Como Usar no Claude Code

## Passo 1: Abra o Projeto no Claude Code

No Claude Code, abra este projeto:
```
Arquivo → Open Folder → c:\Users\emanu\Documents\Projetos\multiagentes
```

## Passo 2: Instale as Dependências

No terminal do Claude Code:
```bash
cd c:\Users\emanu\Documents\Projetos\multiagentes
pip install -e .
```

## Passo 3: Use as Skills

### ✨ Exemplo 1: Gerar um Plano

No chat do Claude Code, digite:
```
/plano Preciso criar um sistema de autenticação com JWT em FastAPI
```

**O que acontece:**
1. Agentes geram um plano estratégico
2. Outro agente valida o plano
3. Terceiro agente verifica dependências
4. Você recebe um plano validado

---

### ✨ Exemplo 2: Auditar Código

No chat do Claude Code:
```
/auditoria src/ --dimensoes bugs,security
```

**O que acontece:**
1. Sistema lê todo código do diretório `src/`
2. 3 auditores trabalham em paralelo (bugs + security)
3. 3 verificadores contestam cada finding (advogados do diabo)
4. Meta-auditor verifica se nada ficou de fora
5. Você recebe report completo

---

### ✨ Exemplo 3: Implementar Código

No chat do Claude Code:
```
/implementar --plano "plano_gerado.json"
```

**O que acontece:**
1. Agentes leem o plano
2. Geram código arquivo por arquivo
3. Verificam implementação
4. Você recebe código pronto

---

## 🎯 Fluxo de Trabalho Completo

```
1. Você: /plano Criar API de usuários
   ↓
2. [Agente gera plano validado]
   ↓
3. Você: Implementa você mesmo OU /implementar
   ↓
4. Você: /auditoria src/users/ --dimensoes bugs,security
   ↓
5. [Agentes auditem e contestam]
   ↓
6. Você recebe report com bugs confirmados
```

## 📋 Opções da /auditoria

```
/auditoria <caminho> --dimensoes <lista>

Caminho: 
  - "src/"           (diretório)
  - "src/auth.py"    (arquivo específico)

Dimensões (separadas por vírgula):
  - bugs             (encontra bugs de software)
  - security         (vulnerabilidades de segurança)
  - performance      (gargalos de performance)

Exemplo:
  /auditoria src/ --dimensoes bugs,security,performance
  /auditoria main.py --dimensoes security
```

## 💡 Dicas

- **Use /plano antes** de implementar coisas complexas
- **Use /auditoria depois** de implementar código crítico
- **Sempre revise** o código gerado por agentes
- **Combine com Claude Code:** Use agentes para planejar, você implementa

## 🔧 Troubleshooting

**Erro: API key inválida**
→ Verifique `.env` - as 3 APIs devem estar configuradas

**Erro: Módulo não encontrado**
→ Rode `pip install -e .` no projeto

**Erro: Caminho não existe**
→ Use caminhos relativos: `src/` ou `src/auth.py`

## ✅ Pronto para Começar!

Tente agora:
```
/plano Criar uma função Python que valida CPF
```

Depois:
```
/auditoria src/ --dimensoes bugs
```
