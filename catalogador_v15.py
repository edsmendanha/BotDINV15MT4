#!/usr/bin/env python3
"""
📊 Catalogador V15 — Análise de Sinais Históricos
Lê os CSVs gerados pelo Catalogador_V15.mq4 e gera relatórios.
"""

import csv
import os
import configparser
from datetime import datetime, time

CONFIG_FILE = "config.txt"
CONFIG_SECTION = "CAMINHOS"
CONFIG_KEY = "catalogo_path"

# ─────────────────────────────────────────────
#  Persistência do caminho em config.txt
# ─────────────────────────────────────────────

def load_saved_path():
    cfg = configparser.ConfigParser()
    if os.path.isfile(CONFIG_FILE):
        cfg.read(CONFIG_FILE, encoding="utf-8")
        if cfg.has_option(CONFIG_SECTION, CONFIG_KEY):
            return cfg.get(CONFIG_SECTION, CONFIG_KEY).strip()
    return ""


def save_path(path):
    cfg = configparser.ConfigParser()
    if os.path.isfile(CONFIG_FILE):
        cfg.read(CONFIG_FILE, encoding="utf-8")
    if not cfg.has_section(CONFIG_SECTION):
        cfg.add_section(CONFIG_SECTION)
    cfg.set(CONFIG_SECTION, CONFIG_KEY, path)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        cfg.write(f)


# ─────────────────────────────────────────────
#  Leitura / parse de CSV
# ─────────────────────────────────────────────

def parse_date(date_str):
    """Converte YYYY.MM.DD → datetime.date"""
    try:
        return datetime.strptime(date_str.strip(), "%Y.%m.%d").date()
    except ValueError:
        return None


def parse_time(time_str):
    """Converte HH:MM → datetime.time"""
    try:
        t = datetime.strptime(time_str.strip(), "%H:%M")
        return t.time()
    except ValueError:
        return None


def load_csv(path):
    rows = []
    try:
        with open(path, newline="", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                rows.append(row)
    except Exception as e:
        print(f"  ⚠️  Erro ao ler {path}: {e}")
    return rows


def load_all_csvs(folder):
    files = [f for f in os.listdir(folder) if f.lower().endswith(".csv")]
    files.sort()
    all_rows = []
    for fn in files:
        rows = load_csv(os.path.join(folder, fn))
        all_rows.extend(rows)
    return all_rows


# ─────────────────────────────────────────────
#  Filtragem por data e horário
# ─────────────────────────────────────────────

def apply_filters(rows, date_start, date_end, time_start, time_end):
    filtered = []
    for r in rows:
        d = parse_date(r.get("data", ""))
        t = parse_time(r.get("horario", ""))
        if d is None or t is None:
            continue
        if date_start and d < date_start:
            continue
        if date_end and d > date_end:
            continue
        if t < time_start:
            continue
        if t > time_end:
            continue
        filtered.append(r)
    return filtered


# ─────────────────────────────────────────────
#  Funções auxiliares de análise
# ─────────────────────────────────────────────

def confirmed_rows(rows):
    return [r for r in rows if r.get("status", "").upper() == "CONFIRMED"]


def win_rows(rows):
    return [r for r in confirmed_rows(rows) if r.get("resultado", "").upper() == "WIN"]


def loss_rows(rows):
    return [r for r in confirmed_rows(rows) if r.get("resultado", "").upper() == "LOSS"]


def winrate(rows):
    conf = confirmed_rows(rows)
    if not conf:
        return 0.0, 0, 0
    wins = len(win_rows(rows))
    losses = len(loss_rows(rows))
    return wins / len(conf) * 100, wins, losses


def color_winrate(wr):
    if wr >= 65:
        return "🟢"
    if wr >= 50:
        return "🟡"
    return "🔴"


# ─────────────────────────────────────────────
#  Relatório principal
# ─────────────────────────────────────────────

SEP_DOUBLE = "═" * 45
SEP_SINGLE = "━" * 45


def fmt_date_br(d):
    if d is None:
        return "todas"
    return d.strftime("%d/%m")


def fmt_time(t):
    return t.strftime("%H:%M")


def print_report(rows, date_start, date_end, time_start, time_end, multi_file):
    total_armed   = len(rows)
    total_conf    = len(confirmed_rows(rows))
    total_rej     = len([r for r in rows if r.get("status", "").upper() == "REJECTED"])
    conf_rate     = (total_conf / total_armed * 100) if total_armed else 0.0
    wr, wins, losses = winrate(rows)

    date_label = f"{fmt_date_br(date_start)} a {fmt_date_br(date_end)}"
    time_label = f"{fmt_time(time_start)}~{fmt_time(time_end)}"

    print()
    print(SEP_DOUBLE)
    print(f"  📊 RELATÓRIO — {date_label} ({time_label})")
    print(SEP_DOUBLE)
    print(f"  Total ARMED:      {total_armed}")
    print(f"  Total CONFIRMED:  {total_conf}")
    print(f"  Total REJECTED:   {total_rej}")
    print(f"  Taxa confirmação: {conf_rate:.1f}%")
    print(SEP_SINGLE)
    print(f"  ✅ WIN:  {wins}  |  ❌ LOSS: {losses}")
    print(f"  📈 Winrate: {wr:.1f}%")

    # Seção 2: ranking por par (só com múltiplos arquivos)
    if multi_file:
        print()
        print("  🏆 RANKING POR PAR:")
        pair_data = {}
        for r in rows:
            sym = r.get("symbol", "?")
            if sym not in pair_data:
                pair_data[sym] = []
            pair_data[sym].append(r)
        ranked = []
        for sym, rws in pair_data.items():
            conf = confirmed_rows(rws)
            if not conf:
                continue
            wr2, w2, _ = winrate(rws)
            ranked.append((sym, wr2, len(conf)))
        ranked.sort(key=lambda x: x[1], reverse=True)
        for i, (sym, wr2, cnt) in enumerate(ranked, 1):
            print(f"  {i}. {sym:<10} → {wr2:.0f}% winrate ({cnt} sinais)")

    # Seção 3: ranking por faixa horária (blocos de 1 hora)
    print()
    print("  🕐 RANKING POR FAIXA HORÁRIA:")
    hour_data = {}
    for r in confirmed_rows(rows):
        t = parse_time(r.get("horario", ""))
        if t is None:
            continue
        h = t.hour
        if h not in hour_data:
            hour_data[h] = []
        hour_data[h].append(r)
    ranked_h = []
    for h, rws in hour_data.items():
        if not rws:
            continue
        wr2, w2, _ = winrate(rws)
        ranked_h.append((h, wr2, len(rws)))
    ranked_h.sort(key=lambda x: x[1], reverse=True)
    for i, (h, wr2, cnt) in enumerate(ranked_h, 1):
        icon = color_winrate(wr2)
        print(f"  {i}. {h:02d}:00-{(h+1)%24:02d}:00 → {wr2:.0f}% ({cnt} sinais) {icon}")

    # Seção 4: ranking por padrão
    print()
    print("  🎯 RANKING POR PADRÃO:")
    pat_data = {}
    for r in confirmed_rows(rows):
        pat = r.get("pattern", "?")
        if pat not in pat_data:
            pat_data[pat] = []
        pat_data[pat].append(r)
    ranked_p = []
    for pat, rws in pat_data.items():
        if not rws:
            continue
        wr2, w2, _ = winrate(rws)
        ranked_p.append((pat, wr2, len(rws)))
    ranked_p.sort(key=lambda x: x[1], reverse=True)
    for i, (pat, wr2, cnt) in enumerate(ranked_p, 1):
        print(f"  {i}. {pat:<22} → {wr2:.0f}% ({cnt} sinais)")

    # Seção 5: score mínimo ideal
    print()
    print("  📈 SCORE MÍNIMO IDEAL:")
    thresholds = [100, 90, 80, 70, 60]
    current_min = 70  # default do indicador M5
    for thr in thresholds:
        subset = [r for r in confirmed_rows(rows)
                  if _safe_int(r.get("score", "0")) >= thr]
        if not subset:
            print(f"  Score >= {thr:3d} → sem dados")
            continue
        wr2, w2, l2 = winrate(subset)
        tag = " ← atual" if thr == current_min else ""
        print(f"  Score >= {thr:3d} → {wr2:.0f}% winrate ({len(subset)} sinais){tag}")

    # Seção 6: análise de losses
    losses_list = loss_rows(rows)
    if losses_list:
        print()
        print(f"  ❌ ANÁLISE DE LOSSES — {len(losses_list)} total")
        print(SEP_SINGLE)
        reversao = [r for r in losses_list if r.get("tipo_loss", "").upper() == "REVERSAO"]
        margem   = [r for r in losses_list if r.get("tipo_loss", "").upper() == "MARGEM"]
        timing   = [r for r in losses_list if r.get("tipo_loss", "").upper() == "TIMING"]
        total_l  = len(losses_list)

        pct = lambda n: (n / total_l * 100) if total_l else 0

        print(f"  ❌ LOSS por reversão forte:  {len(reversao)} ({pct(len(reversao)):.0f}%)")
        print(f"     → Vela foi contra com força (> 3 pips)")
        print(f"  ⚠️  LOSS por margem mínima:   {len(margem)} ({pct(len(margem)):.0f}%)")
        print(f"     → Perdeu por menos de 1 pip")
        print(f"  🔄 LOSS por timing:          {len(timing)} ({pct(len(timing)):.0f}%)")
        print(f"     → Possível entrada atrasada")

    print(SEP_DOUBLE)


def _safe_int(val):
    try:
        return int(val)
    except (ValueError, TypeError):
        return 0


# ─────────────────────────────────────────────
#  Entrada de data/hora com validação
# ─────────────────────────────────────────────

def ask_date(prompt, default=None):
    while True:
        raw = input(prompt).strip()
        if not raw:
            return default
        try:
            return datetime.strptime(raw, "%d/%m/%Y").date()
        except ValueError:
            print("  ⚠️  Formato inválido. Use DD/MM/YYYY (ex: 06/04/2026)")


def ask_time(prompt, default_str):
    while True:
        raw = input(prompt).strip()
        if not raw:
            return datetime.strptime(default_str, "%H:%M").time()
        try:
            return datetime.strptime(raw, "%H:%M").time()
        except ValueError:
            print("  ⚠️  Formato inválido. Use HH:MM (ex: 09:00)")


# ─────────────────────────────────────────────
#  Loop principal
# ─────────────────────────────────────────────

def main():
    print()
    print(SEP_DOUBLE)
    print("  📊 CATALOGADOR V15 — Análise de Sinais Históricos")
    print(SEP_DOUBLE)

    saved = load_saved_path()

    while True:
        # 1. Obter pasta dos catálogos
        if saved:
            prompt = f"  📂 Pasta dos catálogos [{saved}]: "
        else:
            prompt = "  📂 Pasta dos catálogos (caminho completo): "

        raw = input(prompt).strip()
        folder = raw if raw else saved

        if not folder:
            print("  ⚠️  Nenhum caminho informado.")
            continue
        if not os.path.isdir(folder):
            print(f"  ⚠️  Pasta não encontrada: {folder}")
            saved = ""
            continue

        # Salva/atualiza caminho
        if folder != saved:
            save_path(folder)
            saved = folder

        # 2. Lista CSVs
        csv_files = sorted([f for f in os.listdir(folder) if f.lower().endswith(".csv")])
        if not csv_files:
            print("  ⚠️  Nenhum CSV encontrado na pasta.")
            break

        print()
        print("  📋 Arquivos encontrados:")
        for i, fn in enumerate(csv_files, 1):
            rows_tmp = load_csv(os.path.join(folder, fn))
            print(f"  [{i}] {fn} ({len(rows_tmp)} linhas)")
        print("  [0] TODOS")

        # 3. Seleção do arquivo
        while True:
            raw = input("\n  Escolha (número): ").strip()
            try:
                choice = int(raw)
                if 0 <= choice <= len(csv_files):
                    break
            except ValueError:
                pass
            print(f"  ⚠️  Digite um número entre 0 e {len(csv_files)}")

        if choice == 0:
            rows = load_all_csvs(folder)
            multi_file = (len(csv_files) > 1)
        else:
            rows = load_csv(os.path.join(folder, csv_files[choice - 1]))
            multi_file = False

        if not rows:
            print("  ⚠️  Sem dados carregados.")
        else:
            print(f"\n  ✅ {len(rows)} sinais carregados.")

            # 4. Filtros
            print()
            date_start = ask_date("  📅 Data início (DD/MM/YYYY ou ENTER p/ todas): ", None)
            date_end   = ask_date("  📅 Data fim   (DD/MM/YYYY ou ENTER p/ todas): ", None)
            time_start = ask_time("  🕐 Horário início (HH:MM ou ENTER p/ 00:00): ", "00:00")
            time_end   = ask_time("  🕐 Horário fim   (HH:MM ou ENTER p/ 23:59): ", "23:59")

            filtered = apply_filters(rows, date_start, date_end, time_start, time_end)
            print(f"\n  ✅ {len(filtered)} sinais no período filtrado.")

            # 5. Relatório
            if filtered:
                print_report(filtered, date_start, date_end, time_start, time_end, multi_file)
            else:
                print("\n  ⚠️  Nenhum sinal no filtro selecionado.")

        # 6. Menu para rodar de novo ou sair
        print()
        raw = input("  🔄 Analisar novamente? (S/N): ").strip().upper()
        if raw != "S":
            print()
            print("  Até logo! 👋")
            print()
            break


if __name__ == "__main__":
    main()
