#!/usr/bin/env python3
"""
🤖 Bot Telegram — Painel de Monitoramento do BotDINV15MT4
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Monitora state.json e operacoes.csv gerados pelo BotDINV15MT4.py
e envia notificações / recebe comandos via Telegram.

Comandos:
  /start   — 👋 Boas-vindas + menu
  /status  — 📊 Painel completo da sessão
  /pausar  — ⏸️  Pausa operações (ativo=false no state.json)
  /retomar — ▶️  Retoma operações (ativo=true no state.json)
  /limite X — 🎯 Muda limite de entradas em tempo real
  /ajuda   — ❓ Lista de comandos

Segurança: somente admin_ids lidos do config.txt [TELEGRAM] podem usar.
"""

import os
import csv
import json
import asyncio
import configparser
from datetime import datetime

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════

VERSION = "1.0.0"
CONFIG_FILE = "config.txt"
STATE_JSON = "state.json"
LOG_CSV = "operacoes.csv"
POLL_INTERVAL = 7  # segundos entre verificações do CSV

# ═══════════════════════════════════════════════════════════════
# LEITURA DE CONFIG
# ═══════════════════════════════════════════════════════════════

def ler_config() -> dict:
    """Lê config.txt e retorna token e admin_ids."""
    cfg = configparser.ConfigParser()
    if not os.path.exists(CONFIG_FILE):
        raise FileNotFoundError(
            f"❌ Arquivo '{CONFIG_FILE}' não encontrado.\n"
            "Crie o config.txt com as seções [LOGIN] e [TELEGRAM]."
        )
    cfg.read(CONFIG_FILE, encoding="utf-8")

    if "TELEGRAM" not in cfg:
        raise KeyError(
            "❌ Seção [TELEGRAM] não encontrada no config.txt.\n"
            "Adicione:\n  [TELEGRAM]\n  token = SEU_TOKEN\n  admin_ids = 123456789"
        )

    token = cfg["TELEGRAM"].get("token", "").strip()
    if not token or token == "SEU_TOKEN_BOT_AQUI":
        raise ValueError(
            "❌ Token do Telegram não configurado.\n"
            "Edite config.txt e preencha: token = SEU_TOKEN_BOT_AQUI"
        )

    raw_ids = cfg["TELEGRAM"].get("admin_ids", "").strip()
    admin_ids: list[int] = []
    for parte in raw_ids.split(","):
        parte = parte.strip()
        if parte.isdigit():
            admin_ids.append(int(parte))

    if not admin_ids:
        raise ValueError(
            "❌ Nenhum admin_id configurado.\n"
            "Edite config.txt e preencha: admin_ids = SEU_CHAT_ID"
        )

    return {"token": token, "admin_ids": admin_ids}


# ═══════════════════════════════════════════════════════════════
# STATE JSON — LEITURA / ESCRITA
# ═══════════════════════════════════════════════════════════════

def carregar_state() -> dict:
    """Carrega state.json ou retorna estado padrão."""
    if os.path.exists(STATE_JSON):
        try:
            with open(STATE_JSON, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "wins": 0,
        "losses": 0,
        "entradas": 0,
        "lucro_total": 0.0,
        "saldo_inicial": 0.0,
        "saldo_atual": 0.0,
        "ultima_atualizacao": "",
        "ativo": True,
    }


def salvar_state(state: dict):
    """Salva state.json com timestamp atualizado."""
    state["ultima_atualizacao"] = datetime.now().isoformat()
    with open(STATE_JSON, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ═══════════════════════════════════════════════════════════════
# SEGURANÇA — VERIFICAÇÃO DE ADMIN
# ═══════════════════════════════════════════════════════════════

def is_admin(update: Update, admin_ids: list[int]) -> bool:
    """Retorna True se o usuário é um admin autorizado."""
    return update.effective_user.id in admin_ids


async def negar_acesso(update: Update):
    """Responde com mensagem de acesso negado."""
    await update.message.reply_text(
        "⛔ *Acesso negado.* Você não está autorizado.",
        parse_mode="Markdown",
    )


# ═══════════════════════════════════════════════════════════════
# FORMATAÇÃO DE MENSAGENS
# ═══════════════════════════════════════════════════════════════

def formatar_status(state: dict) -> str:
    """Monta a mensagem do painel /status."""
    wins = state.get("wins", 0)
    losses = state.get("losses", 0)
    entradas = state.get("entradas", 0)
    lucro = state.get("lucro_total", 0.0)
    saldo_ini = state.get("saldo_inicial", 0.0)
    saldo_atual = state.get("saldo_atual", 0.0)
    ativo = state.get("ativo", True)
    limite = state.get("limite_entradas", 0)
    ultima = state.get("ultima_atualizacao", "—")

    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0.0
    status_emoji = "▶️ Ativo" if ativo else "⏸️ Pausado"
    lucro_emoji = "📈" if lucro >= 0 else "📉"
    limite_str = str(limite) if limite else "Ilimitado"

    # Formata a última atualização de forma legível
    try:
        dt = datetime.fromisoformat(ultima)
        ultima_fmt = dt.strftime("%d/%m/%Y %H:%M:%S")
    except Exception:
        ultima_fmt = ultima or "—"

    return (
        "📊 *PAINEL DA SESSÃO*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"💳 *Saldo inicial:* R$ {saldo_ini:,.2f}\n"
        f"💰 *Saldo atual:*   R$ {saldo_atual:,.2f}\n"
        f"{lucro_emoji} *Lucro/Perda:*    R$ {lucro:+,.2f}\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🏆 *Wins:*    {wins}\n"
        f"💔 *Losses:*  {losses}\n"
        f"📊 *Entradas:* {entradas}\n"
        f"📈 *Winrate:* {winrate:.1f}%\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"🎯 *Limite de entradas:* {limite_str}\n"
        f"🔄 *Status:* {status_emoji}\n"
        f"🕐 *Última atualização:* {ultima_fmt}"
    )


def formatar_notificacao_entrada(row: dict) -> str:
    """Monta notificação de nova entrada detectada no CSV."""
    par = row.get("par", "—").upper()
    direcao = row.get("direcao", "—").upper()
    valor = row.get("valor", "0")
    timeframe = row.get("timeframe", "—").upper()
    score = row.get("score", "—")
    ts = row.get("timestamp", "—")

    # Extrai só o horário do timestamp
    try:
        horario = datetime.fromisoformat(ts).strftime("%H:%M:%S")
    except Exception:
        try:
            horario = ts.split(" ")[1] if " " in ts else ts
        except Exception:
            horario = ts

    dir_emoji = "📈" if direcao == "CALL" else "📉"

    return (
        "🎯 *NOVA ENTRADA*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📊 *Par:* {par}\n"
        f"{dir_emoji} *Direção:* {direcao}\n"
        f"💰 *Valor:* R$ {float(valor):.2f}\n"
        f"⏱ *Timeframe:* {timeframe}\n"
        f"🔢 *Score:* {score}\n"
        f"🕐 *Horário:* {horario}"
    )


def formatar_notificacao_resultado(row: dict, state: dict) -> str:
    """Monta notificação de resultado (WIN/LOSS) detectado no CSV."""
    par = row.get("par", "—").upper()
    direcao = row.get("direcao", "—").upper()
    resultado = row.get("resultado", "—").lower()
    lucro_perda = float(row.get("lucro_perda", 0))
    saldo_apos = float(row.get("saldo_apos", 0))

    wins = state.get("wins", 0)
    losses = state.get("losses", 0)
    total = wins + losses
    winrate = (wins / total * 100) if total > 0 else 0.0

    dir_emoji = "📈" if direcao == "CALL" else "📉"

    if resultado == "win":
        return (
            f"🏆 *WIN! +R$ {abs(lucro_perda):.2f}*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Par:* {par}\n"
            f"{dir_emoji} *Direção:* {direcao}\n"
            f"💰 *Lucro:* +R$ {abs(lucro_perda):.2f}\n"
            f"💳 *Saldo:* R$ {saldo_apos:,.2f}\n"
            f"📊 *Sessão:* {wins}W / {losses}L ({winrate:.0f}%)"
        )
    else:
        return (
            f"💔 *LOSS -R$ {abs(lucro_perda):.2f}*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            f"📊 *Par:* {par}\n"
            f"{dir_emoji} *Direção:* {direcao}\n"
            f"💰 *Perda:* -R$ {abs(lucro_perda):.2f}\n"
            f"💳 *Saldo:* R$ {saldo_apos:,.2f}\n"
            f"📊 *Sessão:* {wins}W / {losses}L ({winrate:.0f}%)"
        )


# ═══════════════════════════════════════════════════════════════
# HANDLERS DE COMANDOS
# ═══════════════════════════════════════════════════════════════

async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /start."""
    admin_ids: list[int] = context.bot_data["admin_ids"]
    if not is_admin(update, admin_ids):
        await negar_acesso(update)
        return

    nome = update.effective_user.first_name or "Trader"
    msg = (
        f"👋 *Olá, {nome}!*\n\n"
        "🤖 *BotDINV15MT4 — Painel Telegram*\n"
        f"_Versão {VERSION}_\n\n"
        "📋 *Comandos disponíveis:*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📊 /status — Painel completo da sessão\n"
        "⏸️ /pausar — Pausa as operações\n"
        "▶️ /retomar — Retoma as operações\n"
        "🎯 /limite X — Muda o limite de entradas\n"
        "❓ /ajuda — Lista completa de comandos\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📡 Monitorando `operacoes.csv` em tempo real...\n"
        "🔔 Notificações automáticas ativadas!"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


async def cmd_status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /status."""
    admin_ids: list[int] = context.bot_data["admin_ids"]
    if not is_admin(update, admin_ids):
        await negar_acesso(update)
        return

    state = carregar_state()
    await update.message.reply_text(formatar_status(state), parse_mode="Markdown")


async def cmd_pausar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /pausar."""
    admin_ids: list[int] = context.bot_data["admin_ids"]
    if not is_admin(update, admin_ids):
        await negar_acesso(update)
        return

    state = carregar_state()
    if not state.get("ativo", True):
        await update.message.reply_text(
            "⏸️ O bot *já está pausado*.", parse_mode="Markdown"
        )
        return

    state["ativo"] = False
    salvar_state(state)
    await update.message.reply_text(
        "⏸️ *Operações pausadas!*\n"
        "_O BotDINV15MT4.py irá ignorar novos sinais do MT4._",
        parse_mode="Markdown",
    )


async def cmd_retomar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /retomar."""
    admin_ids: list[int] = context.bot_data["admin_ids"]
    if not is_admin(update, admin_ids):
        await negar_acesso(update)
        return

    state = carregar_state()
    if state.get("ativo", True):
        await update.message.reply_text(
            "▶️ O bot *já está ativo*.", parse_mode="Markdown"
        )
        return

    state["ativo"] = True
    salvar_state(state)
    await update.message.reply_text(
        "▶️ *Operações retomadas!*\n"
        "_O BotDINV15MT4.py voltará a executar os sinais do MT4._",
        parse_mode="Markdown",
    )


async def cmd_limite(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /limite X."""
    admin_ids: list[int] = context.bot_data["admin_ids"]
    if not is_admin(update, admin_ids):
        await negar_acesso(update)
        return

    args = context.args
    if not args or len(args) < 1:
        await update.message.reply_text(
            "❌ *Uso:* `/limite X`\n"
            "_Exemplo: `/limite 10` define máximo 10 entradas._\n"
            "_Use `/limite 0` para ilimitado._",
            parse_mode="Markdown",
        )
        return

    try:
        novo_limite = int(args[0])
        if novo_limite < 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Valor inválido. Use um número inteiro ≥ 0.",
            parse_mode="Markdown",
        )
        return

    state = carregar_state()
    state["limite_entradas"] = novo_limite
    salvar_state(state)

    limite_str = str(novo_limite) if novo_limite > 0 else "ilimitado"
    await update.message.reply_text(
        f"🎯 *Limite de entradas atualizado!*\n"
        f"Novo limite: *{limite_str}*",
        parse_mode="Markdown",
    )


async def cmd_ajuda(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler para /ajuda."""
    admin_ids: list[int] = context.bot_data["admin_ids"]
    if not is_admin(update, admin_ids):
        await negar_acesso(update)
        return

    msg = (
        "❓ *AJUDA — BotDINV15MT4 Telegram*\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n\n"
        "📊 */status*\n"
        "  Exibe painel completo: saldo, wins, losses,\n"
        "  winrate, entradas, limite e status atual.\n\n"
        "⏸️ */pausar*\n"
        "  Pausa as operações. O bot executor para\n"
        "  de aceitar novos sinais do MT4.\n\n"
        "▶️ */retomar*\n"
        "  Retoma as operações após uma pausa.\n\n"
        "🎯 */limite X*\n"
        "  Define o limite máximo de entradas.\n"
        "  Use `0` para ilimitado.\n"
        "  Exemplo: `/limite 10`\n\n"
        "🔔 *Notificações automáticas:*\n"
        "  • Nova entrada detectada no CSV\n"
        "  • Resultado WIN ou LOSS de cada operação\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        f"_Bot Telegram v{VERSION} — BotDINV15MT4_"
    )
    await update.message.reply_text(msg, parse_mode="Markdown")


# ═══════════════════════════════════════════════════════════════
# MONITOR DO CSV — BACKGROUND TASK
# ═══════════════════════════════════════════════════════════════

def contar_linhas_csv() -> int:
    """Retorna número de linhas de dados no CSV (sem o header)."""
    if not os.path.exists(LOG_CSV):
        return 0
    try:
        with open(LOG_CSV, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            return sum(1 for _ in reader)
    except Exception:
        return 0


def ler_linhas_csv(desde_linha: int) -> list[dict]:
    """Lê linhas do CSV a partir de `desde_linha` (0-indexed, sem header)."""
    if not os.path.exists(LOG_CSV):
        return []
    try:
        with open(LOG_CSV, "r", encoding="utf-8", newline="") as f:
            reader = csv.DictReader(f)
            todas = list(reader)
        return todas[desde_linha:]
    except Exception:
        return []


async def monitor_csv(app: Application, admin_ids: list[int]):
    """
    Loop de monitoramento do operacoes.csv.
    Detecta novas linhas e envia notificações para todos os admins.
    """
    linhas_anteriores = contar_linhas_csv()

    while True:
        await asyncio.sleep(POLL_INTERVAL)

        linhas_atuais = contar_linhas_csv()
        if linhas_atuais <= linhas_anteriores:
            continue

        # Há linhas novas — processar cada uma
        novas = ler_linhas_csv(linhas_anteriores)
        state = carregar_state()

        for row in novas:
            resultado = row.get("resultado", "").lower()

            if resultado in ("win", "loss"):
                # Notificação de resultado
                texto = formatar_notificacao_resultado(row, state)
            else:
                # Notificação de nova entrada (sem resultado ainda)
                texto = formatar_notificacao_entrada(row)

            for admin_id in admin_ids:
                try:
                    await app.bot.send_message(
                        chat_id=admin_id,
                        text=texto,
                        parse_mode="Markdown",
                    )
                except Exception as e:
                    print(f"⚠️  Erro ao enviar para {admin_id}: {e}")

        linhas_anteriores = linhas_atuais


# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    """Ponto de entrada principal."""
    print()
    print("🤖 ═══════════════════════════════════════════════════")
    print("   BOT TELEGRAM — BotDINV15MT4")
    print("   Painel de Monitoramento e Controle Remoto")
    print(f"   Versão {VERSION}")
    print("═══════════════════════════════════════════════════════")
    print()

    # Lê configurações
    try:
        cfg = ler_config()
    except (FileNotFoundError, KeyError, ValueError) as e:
        print(f"❌ ERRO DE CONFIGURAÇÃO:\n{e}")
        return

    token = cfg["token"]
    admin_ids = cfg["admin_ids"]

    print(f"✅ Token carregado com sucesso.")
    print(f"👥 Admins autorizados: {admin_ids}")
    print(f"📂 Monitorando: {LOG_CSV}")
    print(f"📋 State: {STATE_JSON}")
    print()

    # Cria a aplicação
    app = Application.builder().token(token).build()

    # Armazena admin_ids no bot_data para uso nos handlers
    app.bot_data["admin_ids"] = admin_ids

    # Registra handlers
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("status", cmd_status))
    app.add_handler(CommandHandler("pausar", cmd_pausar))
    app.add_handler(CommandHandler("retomar", cmd_retomar))
    app.add_handler(CommandHandler("limite", cmd_limite))
    app.add_handler(CommandHandler("ajuda", cmd_ajuda))

    # Inicia o monitor do CSV como job recorrente
    async def iniciar_monitor(app: Application):
        asyncio.create_task(monitor_csv(app, admin_ids))

    app.post_init = iniciar_monitor

    print("🚀 Bot Telegram iniciado! Aguardando comandos...")
    print("   Pressione Ctrl+C para parar.")
    print()

    # Inicia polling
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
