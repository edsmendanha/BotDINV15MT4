# 🤖 BotDINV15MT4 — Executor IQ Option via MT4

> **Bot executor puro** para [IQ Option](https://iqoption.com) integrado ao indicador **BOTDINVELAS V15** do MetaTrader 4.  
> O bot **não faz análise técnica** — ele lê os sinais já filtrados pelo indicador MT4 e executa as ordens automaticamente.

---

## 📐 Arquitetura

```
┌──────────────────────────────────────┐
│  MetaTrader 4                        │
│  ┌──────────────────────────────┐    │
│  │  BOTDINVELAS_V15.mq4         │    │
│  │  • Motor V15 Score (0-140)   │    │
│  │  • Filtros ATR/ADX/BBW/Slope │    │
│  │  • Confirmação 2 estágios    │    │
│  │  • Cooldown anti-cluster     │    │
│  └────────────┬─────────────────┘    │
│               │ grava CONFIRMED       │
│               ▼                      │
│   BOTDINVELAS_sinais.txt              │
└───────────────┬──────────────────────┘
                │ poll 2-3s
                ▼
┌──────────────────────────────────────┐
│  BotDINV15MT4.py (executor)          │
│  • Lê sinal do TXT                   │
│  • Verifica saldo / stops / limite   │
│  • Executa na IQ Option              │
│    (digital preferido → binária)     │
│  • Aguarda resultado                 │
│  • Loga CSV + state JSON             │
└──────┬────────────────────┬──────────┘
       │                    │
       ▼                    ▼
 IQ Option API       operacoes.csv
                     state.json
                          │
                          │ poll ~7s
                          ▼
              ┌───────────────────────┐
              │  bot_telegram.py      │
              │  • Notificações auto  │
              │  • /status /pausar    │
              │  • /retomar /limite   │
              └───────────┬───────────┘
                          │
                          ▼
                    📱 Telegram
```

---

## ✅ Features

| Feature | Status |
|---------|--------|
| Agendamento (imediato ou HH:MM) | ✅ |
| Limite de entradas (0 = ilimitado) | ✅ |
| Stop Win % do saldo | ✅ |
| Stop Loss % do saldo | ✅ |
| Valor fixo (ex: R$2,00) | ✅ |
| Valor percentual (ex: 5% do saldo) | ✅ |
| Recalcular % a cada entrada | ✅ |
| Conta DEMO / REAL | ✅ |
| Mercado OTC (`-op`) | ✅ |
| Digital preferido + binária fallback | ✅ |
| Reconexão automática | ✅ |
| Log CSV completo | ✅ |
| State JSON (compatível com Telegram bot) | ✅ |
| Bot Telegram (painel + notificações) | ✅ |
| Menu interativo com cores e emojis | ✅ |
| Gale / Martingale | ❌ Nunca |
| Análise técnica própria | ❌ MT4 faz tudo |
| Cooldown próprio | ❌ MT4 já tem |
| Score mínimo no bot | ❌ MT4 já filtrou |

---

## 🛠️ Pré-requisitos

- **Python 3.8+**
- **MetaTrader 4** com indicador `BOTDINVELAS_V15.mq4` aplicado no gráfico
- **Conta IQ Option** (Demo ou Real)
- Windows (recomendado para o MT4) ou Linux/Mac para o bot

---

## 📦 Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/edsmendanha/BotDINV15MT4.git
cd BotDINV15MT4

# 2. Instale as dependências Python
pip install iqoptionapi colorama
```

---

## ⚙️ Configuração do MT4

### 1. Instalar o indicador

1. Copie `BOTDINVELAS_V15.mq4` para a pasta de indicadores do MT4:
   ```
   C:\Users\<SEU_USUARIO>\AppData\Roaming\MetaQuotes\Terminal\<HASH>\MQL4\Indicators\
   ```
2. Abra o MetaEditor (F4 no MT4) e compile o arquivo (`F7`)
3. No MT4, aplique o indicador em um gráfico **M5** ou **M15**
4. Certifique-se de que a opção **Permitir DLL** está habilitada nas configurações do indicador

### 2. Verificar o arquivo TXT gerado

O indicador grava automaticamente os sinais confirmados em:
```
C:\Users\<SEU_USUARIO>\AppData\Roaming\MetaQuotes\Terminal\<HASH>\MQL4\Files\BOTDINVELAS_sinais.txt
```

Formato de cada linha:
```
[2026.04.10 09:15:26] EURUSD | 5m | CALL ^ | Score: 75 | Vela:09:10 | Entrada:09:15 | CONFIRMED
```

---

## 🔑 Configuração do config.txt

Edite o arquivo `config.txt` com suas credenciais da IQ Option e do Telegram:

```ini
[LOGIN]
email = seu_email@iqoption.com
senha = sua_senha_aqui

[TELEGRAM]
token = SEU_TOKEN_BOT_AQUI
admin_ids = 123456789,987654321
```

> **Segurança**: nunca compartilhe o `config.txt` com ninguém.

---

## 🚀 Como rodar o bot

```bash
python BotDINV15MT4.py
```

O bot vai exibir um menu interativo:

```
🤖 ═══════════════════════════════════════════════════
   BOTDINVELAS V15 - EXECUTOR IQ OPTION
   Bot de Automação para IQOPTION via MT4 — v1.0.0
═══════════════════════════════════════════════════════

📊 CONTA
   [1] DEMO (Prática — recomendado para testar)
   [2] REAL (Dinheiro real — cuidado!)
   Escolha [1/2]: 1

💰 VALOR DA ENTRADA
   Exemplos: 2.00 (fixo) | 5% (percentual do saldo)
   Valor: 2.00

📈 TIPO DE OPERAÇÃO
   [1] Digital  (recomendado — maior payout)
   [2] Binária  (fallback automático se digital indisponível)
   Tipo preferido [1/2]: 1

🛑 STOP LOSS %
   Stop Loss %: 10

🏆 STOP WIN %
   Stop Win %: 20

🎯 LIMITE DE ENTRADAS
   Limite de entradas (0=ilimitado): 0

⏰ INICIAR
   [1] Agora
   [2] Agendar horário (HH:MM)
   Opção [1/2]: 1

📂 CAMINHO DO ARQUIVO TXT (gerado pelo MT4)
   Caminho: C:\Users\Trader\AppData\Roaming\MetaQuotes\Terminal\...\BOTDINVELAS_sinais.txt
```

---

## 📊 Arquivos gerados pelo bot

| Arquivo | Conteúdo |
|---------|---------|
| `operacoes.csv` | Log completo de todas as entradas (timestamp, par, direção, resultado, lucro, saldo) |
| `state.json` | Estado atual da sessão (wins, losses, lucro total, saldo) — usado pelo futuro bot Telegram |

### Exemplo de `operacoes.csv`

```csv
timestamp,par,direcao,timeframe,score,tipo,valor,resultado,lucro_perda,saldo_apos
2026-04-10 09:15:30,EURUSD,call,M5,75,digital,2.00,win,1.82,102.82
2026-04-10 09:45:12,GBPUSD,put,M15,68,digital,2.00,loss,-2.00,100.82
```

---

## 🔄 Fluxo de operação

```
MT4 detecta sinal → grava CONFIRMED no TXT
         ↓
Bot detecta linha nova (poll 2-3 segundos)
         ↓
Parse: extrai par / direção / timeframe / score
         ↓
Verificações:
  • Ativo disponível na IQ?
  • Saldo suficiente?
  • Stop Win atingido?
  • Stop Loss atingido?
  • Limite de entradas atingido?
         ↓
Executa na IQ Option:
  1. Tenta ordem DIGITAL (maior payout)
  2. Se falhar → fallback para BINÁRIA
         ↓
Aguarda resultado (check_win_v4 ou check_win_digital_v2)
         ↓
WIN 🏆 ou LOSS 💔
         ↓
Loga no CSV + atualiza state.json
         ↓
Volta a monitorar o TXT
```

---

## 🎨 Cores no terminal

| Cor | Significado |
|-----|------------|
| 🟢 Verde | WIN, conexão OK, saldo positivo |
| 🔴 Vermelho | LOSS, erro, desconexão |
| 🟡 Amarelo | Aguardando, aviso |
| 🔵 Azul | Informação, status |
| 🟣 Magenta | Sinal detectado (CONFIRMED) |
| ⬜ Branco | Texto normal |

---

## ❓ FAQ

**Q: O bot faz análise técnica própria?**  
A: Não. O bot é um executor puro. Toda a análise é feita pelo indicador MT4.

**Q: O bot usa Gale / Martingale?**  
A: Jamais. O valor é sempre fixo ou percentual fixo do saldo.

**Q: O que acontece se a IQ Option cair ou desconectar?**  
A: O bot tenta reconectar automaticamente até 5 vezes com intervalo de 10 segundos.

**Q: Posso usar o bot sem o MT4 rodando?**  
A: Não. O bot depende do TXT gerado pelo indicador MT4 em tempo real.

**Q: O bot funciona no Linux/Mac?**  
A: O bot Python funciona em qualquer OS. Porém o MT4 só roda no Windows (ou via Wine no Linux).

**Q: Como ver meus resultados?**  
A: Abra o arquivo `operacoes.csv` em qualquer planilha (Excel, LibreOffice). O `state.json` tem o resumo atual.

**Q: E o bot do Telegram?**  
A: Está disponível! Veja a seção **📱 Bot Telegram** abaixo.

---

## 📱 Bot Telegram — Painel de Monitoramento

O `bot_telegram.py` funciona como painel de controle remoto do `BotDINV15MT4.py` via Telegram.

### Como funciona

- O `BotDINV15MT4.py` salva estado em `state.json` e loga operações em `operacoes.csv`
- O `bot_telegram.py` lê esses arquivos para exibir informações e enviar alertas
- Comandos remotos modificam o `state.json` para pausar/retomar/ajustar o bot

### Pré-requisitos adicionais

```bash
pip install python-telegram-bot
```

### 1. Criar o bot no @BotFather

1. Abra o Telegram e procure por `@BotFather`
2. Envie `/newbot`
3. Escolha um nome (ex: `Meu Bot Trader`)
4. Escolha um username (ex: `MeuBotTrader_bot`)
5. O BotFather vai te enviar o **token** — copie-o

### 2. Obter seu Chat ID

- Procure por `@userinfobot` ou `@getmyid_bot` no Telegram
- Envie `/start` para um desses bots
- Ele vai responder com o seu **Chat ID** — anote-o

### 3. Configurar o config.txt

```ini
[LOGIN]
email = seu_email@iqoption.com
senha = sua_senha_aqui

[TELEGRAM]
token = 123456789:AAFxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
admin_ids = 987654321
```

> Para múltiplos admins, separe por vírgula: `admin_ids = 111111111,222222222`

### 4. Rodar em dois terminais simultâneos

**Terminal 1 — Bot executor:**
```bash
python BotDINV15MT4.py
```

**Terminal 2 — Bot Telegram:**
```bash
python bot_telegram.py
```

> Os dois bots devem rodar ao mesmo tempo. O `bot_telegram.py` monitora os arquivos gerados pelo `BotDINV15MT4.py`.

### 📋 Comandos do Bot Telegram

| Comando | Função |
|---------|--------|
| `/start` | 👋 Boas-vindas + menu com todos os comandos |
| `/status` | 📊 Painel completo: saldo, wins, losses, winrate, limite, status |
| `/pausar` | ⏸️ Pausa operações (seta `ativo=false` no state.json) |
| `/retomar` | ▶️ Retoma operações (seta `ativo=true` no state.json) |
| `/limite X` | 🎯 Muda limite de entradas (ex: `/limite 10`) |
| `/ajuda` | ❓ Lista completa de comandos com descrições |

### 🔔 Notificações automáticas

O bot monitora o `operacoes.csv` a cada ~7 segundos e envia alertas:

**Nova entrada:**
```
🎯 NOVA ENTRADA
━━━━━━━━━━━━━━━━━━━━━━
📊 Par: EURUSD
📈 Direção: CALL
💰 Valor: R$ 2.00
⏱ Timeframe: M5
🔢 Score: 75
🕐 Horário: 09:15:26
```

**Resultado WIN:**
```
🏆 WIN! +R$ 1.56
━━━━━━━━━━━━━━━━━━━━━━
📊 Par: EURUSD
📈 Direção: CALL
💰 Lucro: +R$ 1.56
💳 Saldo: R$ 1,001.56
📊 Sessão: 3W / 1L (75%)
```

**Resultado LOSS:**
```
💔 LOSS -R$ 2.00
━━━━━━━━━━━━━━━━━━━━━━
📊 Par: EURUSD
📈 Direção: PUT
💰 Perda: -R$ 2.00
💳 Saldo: R$ 998.00
📊 Sessão: 2W / 2L (50%)
```

### 🔒 Segurança

- Apenas os `admin_ids` configurados no `config.txt` podem usar os comandos
- Qualquer usuário não autorizado recebe: *"⛔ Acesso negado. Você não está autorizado."*

---

## ⚠️ Aviso de Risco

> **TRADING EM OPÇÕES BINÁRIAS E DIGITAIS ENVOLVE ALTO RISCO DE PERDA DE CAPITAL.**
>
> - Nunca opere com dinheiro que não pode se dar ao luxo de perder.
> - Sempre teste em conta **DEMO** antes de usar em conta **REAL**.
> - Este software é fornecido "como está", sem garantias de lucro.
> - O desempenho passado não garante resultados futuros.
> - O autor não se responsabiliza por perdas financeiras.

---

## 📄 Licença

MIT — consulte o arquivo LICENSE para detalhes.

---

*Desenvolvido por [@edsmendanha](https://github.com/edsmendanha)*
