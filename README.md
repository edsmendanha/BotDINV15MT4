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
│  BotDINV15MT4.py (este bot)          │
│  • Lê sinal do TXT                   │
│  • Verifica saldo / stops / limite   │
│  • Executa na IQ Option              │
│    (digital preferido → binária)     │
│  • Aguarda resultado                 │
│  • Loga CSV + state JSON             │
└───────────────┬──────────────────────┘
                │
                ▼
        IQ Option API
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

Edite o arquivo `config.txt` com suas credenciais da IQ Option:

```ini
[LOGIN]
email = seu_email@iqoption.com
senha = sua_senha_aqui
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
A: Será desenvolvido na Fase 2, lendo o `state.json` gerado por este bot.

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
