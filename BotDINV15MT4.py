#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════╗
║         BOTDINVELAS V15 - EXECUTOR IQ OPTION                 ║
║   Bot de Automação para IQOPTION via MT4 (Executor Puro)     ║
║   GitHub: edsmendanha/BotDINV15MT4                           ║
╚══════════════════════════════════════════════════════════════╝

DESCRIÇÃO:
  Este bot é um EXECUTOR PURO. Ele NÃO faz análise técnica.
  Ele lê os sinais CONFIRMED gerados pelo indicador MT4
  (BOTDINVELAS_V15.mq4) e executa as ordens na IQ Option.

FLUXO:
  MT4 grava CONFIRMED no TXT
    → Bot detecta (poll 2-3s)
    → Parse: par, direção, timeframe
    → Verifica: ativo aberto? saldo OK? stops OK? limite OK?
    → Executa na IQ (digital preferido, binária fallback)
    → Aguarda resultado → loga WIN/LOSS no CSV
    → Atualiza state JSON → volta a monitorar
"""

import os
import sys
import csv
import json
import time
import configparser
from datetime import datetime

# ── Colorama (cores no Windows e terminal) ──────────────────────
try:
    from colorama import init as colorama_init, Fore, Back, Style
    colorama_init(autoreset=True)
    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

    class _Dummy:
        def __getattr__(self, name):
            return ""

    Fore = _Dummy()
    Back = _Dummy()
    Style = _Dummy()

# ── IQ Option API ───────────────────────────────────────────────
try:
    from iqoptionapi.stable_api import IQ_Option
    HAS_IQ = True
except ImportError:
    HAS_IQ = False

# ═══════════════════════════════════════════════════════════════
# CONSTANTES
# ═══════════════════════════════════════════════════════════════

VERSION = "1.0.0"
CONFIG_FILE = "config.txt"
LOG_CSV = "operacoes.csv"
STATE_JSON = "state.json"

# Mapeamento timeframe → expiração em minutos
TF_EXPIRY = {
    "M1": 1,
    "M5": 5,
    "M15": 15,
    "M30": 30,
    "H1": 60,
}

# Mapeamento de pares MT4 → IQ Option (remove -op para OTC)
# Ex: EURUSD → EURUSD, EURUSD-op → EURUSD-OTC
def normalizar_par(par_mt4: str) -> str:
    """
    Converte par MT4 para formato IQ Option.

    Regras:
      - Par normal (EURUSD) → EURUSD-op  (mercado aberto, -op minúsculo)
      - Par OTCi (EURJPY-OTCi) → EURJPY-OTC  (mercado OTC, -OTC maiúsculo)
    """
    par = par_mt4.strip()
    # OTCi → OTC (mercado OTC, sempre maiúsculo)
    if par.upper().endswith("-OTCI"):
        return par[:-5].upper() + "-OTC"  # remove "-OTCi" e garante -OTC maiúsculo
    # Par normal sem sufixo → adiciona -op (mercado aberto)
    if "-" not in par:
        return par + "-op"
    return par

# ═══════════════════════════════════════════════════════════════
# FUNÇÕES DE IMPRESSÃO COLORIDA
# ═══════════════════════════════════════════════════════════════

def agora() -> str:
    return datetime.now().strftime("%H:%M:%S")

def print_header():
    print()
    print(Fore.CYAN + Style.BRIGHT + "🤖 ═══════════════════════════════════════════════════")
    print(Fore.CYAN + Style.BRIGHT + "   BOTDINVELAS V15 - EXECUTOR IQ OPTION")
    print(Fore.WHITE + "   Bot de Automação para IQOPTION via MT4 — v" + VERSION)
    print(Fore.CYAN + Style.BRIGHT + "═══════════════════════════════════════════════════════")
    print()

def info(msg: str):
    print(Fore.BLUE + f"[{agora()}] ℹ️  {msg}" + Style.RESET_ALL)

def ok(msg: str):
    print(Fore.GREEN + Style.BRIGHT + f"[{agora()}] ✅ {msg}" + Style.RESET_ALL)

def erro(msg: str):
    print(Fore.RED + Style.BRIGHT + f"[{agora()}] ❌ {msg}" + Style.RESET_ALL)

def aviso(msg: str):
    print(Fore.YELLOW + f"[{agora()}] ⚠️  {msg}" + Style.RESET_ALL)

def sinal(msg: str):
    print(Fore.MAGENTA + Style.BRIGHT + f"[{agora()}] 🎯 {msg}" + Style.RESET_ALL)

def win_msg(msg: str):
    print(Fore.GREEN + Style.BRIGHT + f"[{agora()}] 🏆 WIN  — {msg}" + Style.RESET_ALL)

def loss_msg(msg: str):
    print(Fore.RED + Style.BRIGHT + f"[{agora()}] 💔 LOSS — {msg}" + Style.RESET_ALL)

def aguardando(msg: str):
    print(Fore.YELLOW + f"[{agora()}] ⏳ {msg}" + Style.RESET_ALL)

def separador():
    print(Fore.CYAN + "─" * 54 + Style.RESET_ALL)

# ═══════════════════════════════════════════════════════════════
# LEITURA DE CONFIG.TXT
# ═══════════════════════════════════════════════════════════════

def ler_config() -> dict:
    """Lê config.txt e retorna email/senha e caminho do TXT."""
    cfg = {"email": "", "senha": "", "txt_path": ""}
    if not os.path.exists(CONFIG_FILE):
        aviso(f"config.txt não encontrado — será necessário digitar o login manualmente.")
        return cfg
    parser = configparser.ConfigParser()
    parser.read(CONFIG_FILE, encoding="utf-8")
    if parser.has_section("LOGIN"):
        cfg["email"] = parser.get("LOGIN", "email", fallback="")
        cfg["senha"] = parser.get("LOGIN", "senha", fallback="")
    if parser.has_section("CAMINHOS"):
        cfg["txt_path"] = parser.get("CAMINHOS", "txt_path", fallback="")
    return cfg


def salvar_caminho_config(txt_path: str):
    """Salva o caminho do TXT no config.txt na seção [CAMINHOS]."""
    parser = configparser.ConfigParser()
    if os.path.exists(CONFIG_FILE):
        parser.read(CONFIG_FILE, encoding="utf-8")
    if not parser.has_section("CAMINHOS"):
        parser.add_section("CAMINHOS")
    parser.set("CAMINHOS", "txt_path", txt_path)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        parser.write(f)

# ═══════════════════════════════════════════════════════════════
# MENU INTERATIVO
# ═══════════════════════════════════════════════════════════════

def input_colored(prompt: str) -> str:
    """Input com prompt colorido."""
    return input(Fore.WHITE + Style.BRIGHT + prompt + Style.RESET_ALL).strip()

def menu_interativo(cfg: dict) -> dict:
    """Exibe menu interativo e coleta configurações do usuário."""
    print_header()

    config_sessao = {}

    # ── Conta DEMO/REAL ──────────────────────────────────────────
    separador()
    print(Fore.CYAN + "📊 CONTA")
    print("   [1] DEMO (Prática — recomendado para testar)")
    print("   [2] REAL (Dinheiro real — cuidado!)")
    while True:
        escolha = input_colored("   Escolha [1/2]: ")
        if escolha in ("1", "2"):
            config_sessao["conta"] = "PRACTICE" if escolha == "1" else "REAL"
            break
        aviso("Digite 1 ou 2.")

    # ── Login ─────────────────────────────────────────────────────
    separador()
    print(Fore.CYAN + "🔑 LOGIN IQ OPTION")
    if cfg.get("email") and cfg.get("senha"):
        ok("Login carregado do config.txt.")
        email = cfg["email"]
        senha = cfg["senha"]
    else:
        if cfg.get("email"):
            email = cfg["email"]
        else:
            email = input_colored("   Email: ")
        if cfg.get("senha"):
            senha = cfg["senha"]
        else:
            import getpass
            senha = getpass.getpass(Fore.WHITE + Style.BRIGHT + "   Senha: " + Style.RESET_ALL)
    config_sessao["email"] = email
    config_sessao["senha"] = senha

    # ── Valor de entrada ─────────────────────────────────────────
    separador()
    print(Fore.CYAN + "💰 VALOR DA ENTRADA")
    print("   [1] Valor fixo (ex: R$ 2.00)")
    print("   [2] Percentual do saldo (ex: 5%)")
    while True:
        escolha_val = input_colored("   Escolha [1/2]: ")
        if escolha_val in ("1", "2"):
            break
        aviso("Digite 1 ou 2.")

    if escolha_val == "1":
        config_sessao["valor_tipo"] = "fixo"
        while True:
            val = input_colored("   Digite o valor (ex: 2.00): ").replace(",", ".")
            try:
                v = float(val)
                if v > 0:
                    config_sessao["valor"] = v
                    break
            except ValueError:
                pass
            aviso("Valor inválido. Exemplo: 2.00")
    else:
        config_sessao["valor_tipo"] = "percent"
        while True:
            val = input_colored("   Digite a porcentagem (ex: 5): ").replace(",", ".")
            try:
                pct = float(val)
                if pct > 0:
                    config_sessao["valor"] = pct
                    break
            except ValueError:
                pass
            aviso("Valor inválido. Exemplo: 5")

    config_sessao["recalcular"] = False
    if config_sessao["valor_tipo"] == "percent":
        r = input_colored("   🔄 Recalcular valor a cada entrada com base no saldo atual? [S/N]: ").upper()
        config_sessao["recalcular"] = r == "S"

    # ── Tipo preferido ────────────────────────────────────────────
    separador()
    config_sessao["tipo_preferido"] = "digital"
    info("📈 Modo: Digital (fallback binária automático)")

    # ── Stop Loss % ───────────────────────────────────────────────
    separador()
    print(Fore.CYAN + "🛑 STOP LOSS %")
    print("   Para se a PERDA acumulada atingir X% do saldo inicial.")
    print("   Exemplo: 10 = para se perder 10% do saldo. 0 = desativado.")
    while True:
        sl = input_colored("   Stop Loss %: ").replace(",", ".")
        try:
            config_sessao["stop_loss_pct"] = float(sl)
            break
        except ValueError:
            aviso("Digite um número. Exemplo: 10")

    # ── Stop Win % ────────────────────────────────────────────────
    separador()
    print(Fore.CYAN + "🏆 STOP WIN %")
    print("   Para se o LUCRO acumulado atingir X% do saldo inicial.")
    print("   Exemplo: 20 = para ao ganhar 20%. 0 = desativado.")
    while True:
        sw = input_colored("   Stop Win %: ").replace(",", ".")
        try:
            config_sessao["stop_win_pct"] = float(sw)
            break
        except ValueError:
            aviso("Digite um número. Exemplo: 20")

    # ── Limite de entradas ────────────────────────────────────────
    separador()
    print(Fore.CYAN + "🎯 LIMITE DE ENTRADAS")
    print("   0 = ilimitado")
    while True:
        lim = input_colored("   Limite de entradas (0=ilimitado): ")
        try:
            config_sessao["limite_entradas"] = int(lim)
            break
        except ValueError:
            aviso("Digite um número inteiro. Exemplo: 10")

    # ── Agendamento ───────────────────────────────────────────────
    separador()
    print(Fore.CYAN + "⏰ INICIAR")
    print("   [1] Agora")
    print("   [2] Agendar horário (HH:MM)")
    while True:
        ag = input_colored("   Opção [1/2]: ")
        if ag == "1":
            config_sessao["agendar"] = None
            break
        elif ag == "2":
            while True:
                hm = input_colored("   Horário de início (HH:MM): ")
                try:
                    datetime.strptime(hm, "%H:%M")
                    config_sessao["agendar"] = hm
                    break
                except ValueError:
                    aviso("Formato inválido. Use HH:MM (ex: 09:30)")
            break
        aviso("Digite 1 ou 2.")

    # ── Caminho do TXT ────────────────────────────────────────────
    separador()
    print(Fore.CYAN + "📂 CAMINHO DO ARQUIVO TXT (gerado pelo MT4)")

    # Verifica se já tem caminho salvo no config.txt
    caminho_salvo = cfg.get("txt_path", "")
    if caminho_salvo and os.path.exists(caminho_salvo):
        ok(f"Caminho salvo encontrado: {caminho_salvo}")
        usar = input_colored("   Usar este caminho? [S/N]: ").upper()
        if usar == "S":
            config_sessao["txt_path"] = caminho_salvo
        else:
            caminho = input_colored("   Novo caminho completo do TXT: ")
            config_sessao["txt_path"] = caminho
    elif caminho_salvo:
        aviso(f"Caminho salvo não encontrado: {caminho_salvo}")
        caminho = input_colored("   Digite o caminho completo do TXT: ")
        config_sessao["txt_path"] = caminho
    else:
        print("   Exemplo: C:\\Users\\...\\MQL4\\Files\\BOTDINVELAS_sinais.txt")
        print("   (Localize em: MT4 → Arquivo → Abrir pasta de dados → MQL4\\Files\\)")
        caminho = input_colored("   Caminho completo do TXT: ")
        config_sessao["txt_path"] = caminho

    # Pergunta se quer salvar o caminho
    if config_sessao["txt_path"] != caminho_salvo:
        salvar = input_colored("   💾 Salvar este caminho no config.txt? [S/N]: ").upper()
        if salvar == "S":
            salvar_caminho_config(config_sessao["txt_path"])
            ok("Caminho salvo! Na próxima vez não precisará digitar.")

    separador()
    ok("Configuração concluída! Iniciando bot...")
    print()

    return config_sessao

# ═══════════════════════════════════════════════════════════════
# PARSE DO TXT DO MT4
# ═══════════════════════════════════════════════════════════════

def parse_linha(linha: str) -> dict | None:
    """
    Faz parse de uma linha do TXT gerado pelo MT4.

    Formato esperado:
      [2026.04.10 09:15:26] EURUSD | 5m | CALL ^ | Score: 75 | Vela:09:10 | Entrada:09:15 | CONFIRMED

    Retorna dict com: par, direcao, timeframe, score, timestamp_str
    Retorna None se linha inválida ou sem CONFIRMED.
    """
    linha = linha.strip()
    if not linha:
        return None
    if "CONFIRMED" not in linha.upper():
        return None

    try:
        # Remove timestamp entre colchetes: [2026.04.10 09:15:26]
        ts_str = ""
        if linha.startswith("["):
            fim = linha.index("]")
            ts_str = linha[1:fim].strip()
            linha = linha[fim + 1:].strip()

        partes = [p.strip() for p in linha.split("|")]

        # partes[0] = par (ex: EURUSD)
        par = partes[0].strip().upper() if len(partes) > 0 else ""

        # partes[1] = timeframe (ex: 5m, M5, 15m, M15)
        tf_raw = partes[1].strip().upper() if len(partes) > 1 else "M5"
        tf_raw = tf_raw.replace("M", "").replace(" ", "")
        timeframe = f"M{tf_raw}"

        # partes[2] = direção (ex: CALL ^, PUT v)
        dir_raw = partes[2].strip().upper() if len(partes) > 2 else ""
        if "CALL" in dir_raw:
            direcao = "call"
        elif "PUT" in dir_raw:
            direcao = "put"
        else:
            return None

        # Score opcional
        score = 0
        for p in partes:
            if "SCORE:" in p.upper():
                try:
                    score = int(p.upper().replace("SCORE:", "").strip())
                except ValueError:
                    pass

        if not par or not direcao:
            return None

        return {
            "par": par,
            "direcao": direcao,
            "timeframe": timeframe,
            "score": score,
            "timestamp_str": ts_str,
        }

    except Exception as e:
        aviso(f"Erro ao parsear linha: {e} | Linha: {linha}")
        return None

# ═══════════════════════════════════════════════════════════════
# PERSISTÊNCIA — CSV + STATE JSON
# ═══════════════════════════════════════════════════════════════

def init_csv():
    """Cria o CSV de log se não existir."""
    if not os.path.exists(LOG_CSV):
        with open(LOG_CSV, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "timestamp", "par", "direcao", "timeframe",
                "score", "tipo", "valor", "resultado",
                "lucro_perda", "saldo_apos"
            ])

def log_csv(ts: str, par: str, direcao: str, timeframe: str,
            score: int, tipo: str, valor: float,
            resultado: str, lucro_perda: float, saldo: float):
    """Adiciona linha ao CSV de log."""
    with open(LOG_CSV, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            ts, par, direcao, timeframe,
            score, tipo, valor, resultado,
            round(lucro_perda, 2), round(saldo, 2)
        ])

def carregar_state() -> dict:
    """Carrega state.json ou retorna estado inicial."""
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
    """Salva state.json atualizado."""
    state["ultima_atualizacao"] = datetime.now().isoformat()
    with open(STATE_JSON, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)

# ═══════════════════════════════════════════════════════════════
# CONEXÃO IQ OPTION
# ═══════════════════════════════════════════════════════════════

def conectar(email: str, senha: str, conta: str,
             max_tentativas: int = 5) -> "IQ_Option | None":
    """Conecta na IQ Option com reconexão automática."""
    if not HAS_IQ:
        erro("iqoptionapi não instalado! Execute: pip install iqoptionapi")
        return None

    tentativa = 0
    while tentativa < max_tentativas:
        tentativa += 1
        info(f"Conectando na IQ Option... (tentativa {tentativa}/{max_tentativas})")
        try:
            iq = IQ_Option(email, senha)
            check, reason = iq.connect()
            if check:
                iq.change_balance(conta)
                ok(f"Conectado! Conta: {conta}")
                return iq
            else:
                erro(f"Falha na conexão: {reason}")
        except Exception as e:
            erro(f"Exceção ao conectar: {e}")

        if tentativa < max_tentativas:
            aguardando(f"Aguardando 10s para nova tentativa...")
            time.sleep(10)

    erro("Não foi possível conectar após todas as tentativas.")
    return None

def garantir_conexao(iq: "IQ_Option", email: str, senha: str, conta: str) -> "IQ_Option | None":
    """Verifica se está conectado; reconecta se necessário."""
    try:
        if iq.check_connect():
            return iq
    except Exception:
        pass

    aviso("Desconectado! Tentando reconectar...")
    return conectar(email, senha, conta)

# ═══════════════════════════════════════════════════════════════
# CÁLCULO DO VALOR DE ENTRADA
# ═══════════════════════════════════════════════════════════════

def calcular_valor(config: dict, saldo_atual: float, saldo_inicial: float) -> float:
    """Calcula o valor da entrada conforme configuração."""
    if config["valor_tipo"] == "fixo":
        return round(config["valor"], 2)
    else:
        base = saldo_atual if config["recalcular"] else saldo_inicial
        return round(base * config["valor"] / 100.0, 2)

# ═══════════════════════════════════════════════════════════════
# EXECUÇÃO DE ORDEM
# ═══════════════════════════════════════════════════════════════

def executar_ordem(iq: "IQ_Option", par: str, direcao: str,
                   valor: float, timeframe: str,
                   tipo_preferido: str) -> tuple:
    """
    Executa uma ordem na IQ Option.
    Tenta digital primeiro; se falhar, vai para binária.

    Returns:
        (id_ordem, tipo_usado, sucesso)
    """
    par_iq = normalizar_par(par)
    expiry = TF_EXPIRY.get(timeframe, 5)

    # ── Tenta DIGITAL ─────────────────────────────────────────────
    if tipo_preferido == "digital":
        try:
            info(f"Tentando ordem DIGITAL: {par_iq} | {direcao.upper()} | R${valor:.2f} | exp:{expiry}m")
            status, id_ordem = iq.buy_digital_spot_v2(par_iq, valor, direcao, expiry)
            if status:
                ok(f"Ordem DIGITAL aberta! ID: {id_ordem}")
                return id_ordem, "digital", True
            else:
                aviso(f"Digital falhou (status={status}). Tentando binária...")
        except Exception as e:
            aviso(f"Erro na ordem digital: {e}. Tentando binária...")

    # ── Fallback BINÁRIA ──────────────────────────────────────────
    try:
        info(f"Tentando ordem BINÁRIA: {par_iq} | {direcao.upper()} | R${valor:.2f} | exp:{expiry}m")
        status, id_ordem = iq.buy(valor, par_iq, direcao, expiry)
        if status:
            ok(f"Ordem BINÁRIA aberta! ID: {id_ordem}")
            return id_ordem, "binary", True
        else:
            erro(f"Binária também falhou (status={status}). Sinal ignorado.")
            return None, "binary", False
    except Exception as e:
        erro(f"Erro na ordem binária: {e}")
        return None, "binary", False

# ═══════════════════════════════════════════════════════════════
# AGUARDA RESULTADO
# ═══════════════════════════════════════════════════════════════

def aguardar_resultado(iq: "IQ_Option", id_ordem: int, tipo: str,
                       timeout: int = 600) -> tuple:
    """
    Aguarda resultado da ordem.

    Returns:
        (resultado, lucro_perda)
        resultado = "win" | "loss" | "equal" | "erro"
    """
    aguardando(f"Aguardando resultado da ordem {id_ordem} ({tipo})...")
    inicio = time.time()

    while time.time() - inicio < timeout:
        try:
            if tipo == "digital":
                resultado = iq.check_win_digital_v2(id_ordem)
            else:
                resultado = iq.check_win_v4(id_ordem)

            if resultado is not None:
                lucro = float(resultado)
                if lucro > 0:
                    return "win", lucro
                elif lucro < 0:
                    return "loss", lucro
                else:
                    return "equal", 0.0

        except Exception as e:
            aviso(f"Erro ao verificar resultado: {e}")

        time.sleep(5)

    aviso("Timeout ao aguardar resultado — marcando como erro.")
    return "erro", 0.0

# ═══════════════════════════════════════════════════════════════
# MONITOR DO TXT
# ═══════════════════════════════════════════════════════════════

def ler_linhas_pendentes(txt_path: str, linhas_processadas: set) -> list:
    """
    Lê o TXT do MT4 e retorna linhas CONFIRMED ainda não processadas.
    """
    if not os.path.exists(txt_path):
        return []

    novas = []
    try:
        with open(txt_path, "r", encoding="utf-8", errors="replace") as f:
            for linha in f:
                linha = linha.strip()
                if "CONFIRMED" in linha.upper() and linha not in linhas_processadas:
                    novas.append(linha)
    except Exception as e:
        aviso(f"Erro ao ler TXT: {e}")

    return novas

# ═══════════════════════════════════════════════════════════════
# VERIFICAÇÕES DE SEGURANÇA
# ═══════════════════════════════════════════════════════════════

def verificar_stops(state: dict, config: dict) -> tuple:
    """
    Verifica se Stop Win ou Stop Loss foram atingidos.

    Returns:
        (pode_operar, motivo)
    """
    sl_pct = config.get("stop_loss_pct", 0)
    sw_pct = config.get("stop_win_pct", 0)
    saldo_ini = state.get("saldo_inicial", 0)
    lucro = state.get("lucro_total", 0)

    if saldo_ini <= 0:
        return True, ""

    if sl_pct > 0:
        limite_perda = saldo_ini * sl_pct / 100.0
        if lucro <= -limite_perda:
            return False, f"🛑 STOP LOSS atingido! Perda: R${abs(lucro):.2f} / Limite: R${limite_perda:.2f}"

    if sw_pct > 0:
        limite_ganho = saldo_ini * sw_pct / 100.0
        if lucro >= limite_ganho:
            return False, f"🏆 STOP WIN atingido! Lucro: R${lucro:.2f} / Meta: R${limite_ganho:.2f}"

    return True, ""

def verificar_limite_entradas(state: dict, config: dict) -> bool:
    """Verifica se atingiu o limite de entradas."""
    limite = config.get("limite_entradas", 0)
    if limite == 0:
        return True
    return state.get("entradas", 0) < limite

# ═══════════════════════════════════════════════════════════════
# AGENDAMENTO
# ═══════════════════════════════════════════════════════════════

def aguardar_agendamento(horario: str):
    """Aguarda até o horário agendado (HH:MM). Se já passou, agenda pro dia seguinte."""
    if not horario:
        return

    from datetime import timedelta

    agora_dt = datetime.now()
    h, m = map(int, horario.split(":"))
    alvo = agora_dt.replace(hour=h, minute=m, second=0, microsecond=0)

    # Se o horário já passou hoje, agenda pro dia seguinte
    if alvo <= agora_dt:
        alvo += timedelta(days=1)
        info(f"Horário {horario} já passou hoje. Agendado para amanhã ({alvo.strftime('%d/%m/%Y %H:%M')}).")
    else:
        info(f"Bot agendado para iniciar às {horario}.")

    # Contador regressivo na mesma linha
    while True:
        agora_dt = datetime.now()
        restante = alvo - agora_dt
        if restante.total_seconds() <= 0:
            # Limpa a linha e mostra mensagem final
            sys.stdout.write("\r" + " " * 60 + "\r")
            sys.stdout.flush()
            ok(f"Horário atingido! Iniciando operações...")
            break

        # Formata HH:MM:SS restante
        total_seg = int(restante.total_seconds())
        hh = total_seg // 3600
        mm = (total_seg % 3600) // 60
        ss = total_seg % 60

        # Sobrescreve a mesma linha com \r
        sys.stdout.write(f"\r{Fore.YELLOW}⏳ Iniciando em {hh:02d}:{mm:02d}:{ss:02d}...{Style.RESET_ALL}   ")
        sys.stdout.flush()
        time.sleep(1)

# ═══════════════════════════════════════════════════════════════
# EXIBIÇÃO DE RESUMO
# ═══════════════════════════════════════════════════════════════

def exibir_resumo(state: dict):
    """Exibe resumo colorido das operações."""
    separador()
    print(Fore.CYAN + Style.BRIGHT + "📊 RESUMO DA SESSÃO")
    print(Fore.WHITE + f"   Entradas : {state['entradas']}")

    cor_wins = Fore.GREEN if state["wins"] > 0 else Fore.WHITE
    cor_loss = Fore.RED if state["losses"] > 0 else Fore.WHITE
    print(cor_wins + f"   Wins     : {state['wins']}")
    print(cor_loss + f"   Losses   : {state['losses']}")

    lucro = state["lucro_total"]
    cor_lucro = Fore.GREEN if lucro >= 0 else Fore.RED
    print(cor_lucro + Style.BRIGHT + f"   Lucro    : R${lucro:+.2f}")
    print(Fore.WHITE + f"   Saldo    : R${state['saldo_atual']:.2f}")
    separador()

# ═══════════════════════════════════════════════════════════════
# LOOP PRINCIPAL
# ═══════════════════════════════════════════════════════════════

def loop_principal(iq: "IQ_Option", config: dict):
    """Loop principal do bot — monitora TXT e executa ordens."""

    txt_path = config["txt_path"]
    linhas_processadas: set = set()
    state = carregar_state()
    init_csv()

    # Saldo inicial da sessão
    try:
        saldo = iq.get_balance()
        state["saldo_inicial"] = saldo
        state["saldo_atual"] = saldo
        salvar_state(state)
        ok(f"Saldo inicial: R${saldo:.2f} ({config['conta']})")
    except Exception as e:
        aviso(f"Não foi possível obter saldo: {e}")
        saldo = 0.0

    info(f"Monitorando TXT: {txt_path}")
    info("Pressione Ctrl+C para parar o bot.")
    separador()

    # Aguarda agendamento se configurado
    aguardar_agendamento(config.get("agendar"))

    while True:
        try:
            # ── Verifica stops antes de tudo ─────────────────────
            pode, motivo = verificar_stops(state, config)
            if not pode:
                print()
                aviso(motivo)
                exibir_resumo(state)
                info("Bot encerrado por Stop. Até a próxima! 👋")
                break

            if not verificar_limite_entradas(state, config):
                aviso(f"Limite de {config['limite_entradas']} entradas atingido!")
                exibir_resumo(state)
                info("Bot encerrado por limite de entradas. Até a próxima! 👋")
                break

            # ── Lê novas linhas do TXT ───────────────────────────
            novas_linhas = ler_linhas_pendentes(txt_path, linhas_processadas)

            for linha_raw in novas_linhas:
                linhas_processadas.add(linha_raw)

                parsed = parse_linha(linha_raw)
                if not parsed:
                    aviso(f"Linha ignorada (parse falhou): {linha_raw[:80]}")
                    continue

                par = parsed["par"]
                direcao = parsed["direcao"]
                timeframe = parsed["timeframe"]
                score = parsed["score"]

                sinal(f"Sinal CONFIRMADO: {par} | {direcao.upper()} | {timeframe} | Score:{score}")

                # ── Garante conexão ──────────────────────────────
                iq = garantir_conexao(iq, config["email"], config["senha"], config["conta"])
                if iq is None:
                    erro("Falha de reconexão. Sinal ignorado.")
                    continue

                # ── Calcula valor ────────────────────────────────
                try:
                    saldo_atual = iq.get_balance()
                    state["saldo_atual"] = saldo_atual
                except Exception:
                    saldo_atual = state.get("saldo_atual", state.get("saldo_inicial", 0))

                valor = calcular_valor(config, saldo_atual, state["saldo_inicial"])

                if valor <= 0:
                    aviso("Valor de entrada calculado é zero ou negativo. Sinal ignorado.")
                    continue

                info(f"Valor calculado: R${valor:.2f}")

                # ── Verifica ativo disponível ────────────────────
                try:
                    par_iq = normalizar_par(par)
                    todos_abertos = iq.get_all_open_time()
                    digital_aberto = (
                        todos_abertos.get("digital", {})
                        .get(par_iq, {})
                        .get("open", False)
                    )
                    binary_aberto = (
                        todos_abertos.get("turbo", {})
                        .get(par_iq, {})
                        .get("open", False)
                    )
                    if not digital_aberto and not binary_aberto:
                        aviso(f"Par {par_iq} fechado no momento. Sinal ignorado.")
                        continue
                except Exception as e:
                    aviso(f"Não foi possível verificar abertura do ativo: {e}")

                # ── Executa ordem ────────────────────────────────
                id_ordem, tipo_usado, sucesso = executar_ordem(
                    iq, par, direcao, valor, timeframe, config["tipo_preferido"]
                )

                if not sucesso or id_ordem is None:
                    erro("Falha ao abrir ordem. Sinal descartado.")
                    continue

                state["entradas"] += 1

                # ── Aguarda resultado ────────────────────────────
                resultado, lucro_perda = aguardar_resultado(iq, id_ordem, tipo_usado)

                # ── Atualiza estado ──────────────────────────────
                try:
                    saldo_apos = iq.get_balance()
                    state["saldo_atual"] = saldo_apos
                except Exception:
                    saldo_apos = saldo_atual + lucro_perda

                state["lucro_total"] += lucro_perda

                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                if resultado == "win":
                    state["wins"] += 1
                    win_msg(f"{par} | {direcao.upper()} | +R${lucro_perda:.2f} | Saldo: R${saldo_apos:.2f}")
                elif resultado == "loss":
                    state["losses"] += 1
                    loss_msg(f"{par} | {direcao.upper()} | R${lucro_perda:.2f} | Saldo: R${saldo_apos:.2f}")
                else:
                    info(f"Resultado: {resultado.upper()} | {par} | {direcao.upper()}")

                # ── Log CSV ──────────────────────────────────────
                log_csv(
                    ts, par, direcao, timeframe, score,
                    tipo_usado, valor, resultado,
                    round(lucro_perda, 2), round(saldo_apos, 2)
                )

                # ── Salva state.json ─────────────────────────────
                salvar_state(state)

                # ── Resumo parcial ───────────────────────────────
                exibir_resumo(state)

            # ── Aguarda próxima iteração ─────────────────────────
            time.sleep(2.5)

        except KeyboardInterrupt:
            print()
            aviso("Bot interrompido pelo usuário (Ctrl+C).")
            exibir_resumo(state)
            salvar_state(state)
            info("Até a próxima! 👋")
            sys.exit(0)

        except Exception as e:
            erro(f"Erro inesperado no loop: {e}")
            time.sleep(5)

# ═══════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════

def main():
    """Ponto de entrada principal do bot."""
    if not HAS_IQ:
        print_header()
        erro("iqoptionapi não está instalado!")
        info("Execute: pip install iqoptionapi colorama")
        sys.exit(1)

    # Lê config.txt
    cfg = ler_config()

    # Menu interativo
    config = menu_interativo(cfg)

    # Conecta na IQ Option
    separador()
    iq = conectar(config["email"], config["senha"], config["conta"])
    if iq is None:
        erro("Não foi possível conectar. Verifique email/senha no config.txt.")
        sys.exit(1)

    # Inicia loop
    loop_principal(iq, config)


if __name__ == "__main__":
    main()
