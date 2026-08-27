#!/usr/bin/env python3
"""
Radar X - monitora perfis e avisa quando um post foge da media do autor.

Roda a cada 30 min pelo GitHub Actions.
Nao julga pelo total de views, e sim por views-para-a-idade-do-post,
comparando com a curva historica daquele mesmo perfil.
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
from statistics import median

import requests

BASE = "https://api.twitterapi.io"
ARQ_CONFIG = "config.json"
ARQ_ESTADO = "estado.json"

API_KEY = os.environ.get("TWITTERAPI_KEY", "").strip()
TG_TOKEN = os.environ.get("TELEGRAM_TOKEN", "").strip()
TG_CHAT = os.environ.get("TELEGRAM_CHAT_ID", "").strip()

if not API_KEY or not TG_TOKEN or not TG_CHAT:
    print("ERRO: faltam variaveis de ambiente (TWITTERAPI_KEY, TELEGRAM_TOKEN, TELEGRAM_CHAT_ID)")
    sys.exit(1)

HEADERS = {"X-API-Key": API_KEY}


# ---------------------------------------------------------------- utilidades

def agora():
    return datetime.now(timezone.utc)


def carregar(caminho, padrao):
    try:
        with open(caminho, "r", encoding="utf-8") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return padrao


def salvar(caminho, dados):
    with open(caminho, "w", encoding="utf-8") as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)


def parse_data(txt):
    """createdAt vem como 'Sun Feb 08 12:00:00 +0000 2026'."""
    if not txt:
        return None
    for fmt in ("%a %b %d %H:%M:%S %z %Y", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(txt, fmt)
        except ValueError:
            continue
    return None


def idade_min(iso_criacao):
    dt = datetime.fromisoformat(iso_criacao)
    return (agora() - dt).total_seconds() / 60.0


def encurtar(texto, limite):
    texto = " ".join((texto or "").split())
    if len(texto) <= limite:
        return texto
    return texto[:limite].rstrip() + "..."


def fmt_num(n):
    if n >= 1_000_000:
        return f"{n/1_000_000:.1f}M".replace(".", ",")
    if n >= 1_000:
        return f"{n/1_000:.0f} mil"
    return str(n)


# --------------------------------------------------------------------- API X

def api_get(caminho, params, tentativas=3):
    for i in range(tentativas):
        try:
            r = requests.get(f"{BASE}{caminho}", headers=HEADERS, params=params, timeout=30)
            if r.status_code == 200:
                return r.json()
            print(f"  API {caminho} devolveu {r.status_code}: {r.text[:200]}")
            if r.status_code in (401, 402, 403):
                return None  # chave invalida ou sem credito: nao adianta insistir
        except requests.RequestException as e:
            print(f"  falha de rede em {caminho}: {e}")
        time.sleep(2 * (i + 1))
    return None


def buscar_novos(perfis, desde_iso, max_paginas=4):
    """Busca posts recentes dos perfis via advanced_search (1 chamada cobre todos)."""
    consulta = " OR ".join(f"from:{p}" for p in perfis)
    corte = datetime.fromisoformat(desde_iso)

    achados, cursor, pagina = [], None, 0
    while pagina < max_paginas:
        params = {"query": consulta, "queryType": "Latest"}
        if cursor:
            params["cursor"] = cursor

        dados = api_get("/twitter/tweet/advanced_search", params)
        if not dados:
            break

        lote = dados.get("tweets") or []
        if not lote:
            break

        chegou_no_fim = False
        for tw in lote:
            dt = parse_data(tw.get("createdAt"))
            if dt and dt <= corte:
                chegou_no_fim = True
                continue
            achados.append(tw)

        if chegou_no_fim or not dados.get("has_next_page"):
            break
        cursor = dados.get("next_cursor")
        if not cursor:
            break
        pagina += 1

    return achados


def atualizar_views(ids):
    """Batch lookup: ate 100 ids por chamada."""
    resultado = {}
    for i in range(0, len(ids), 100):
        bloco = ids[i:i + 100]
        dados = api_get("/twitter/tweets", {"tweet_ids": ",".join(bloco)})
        if not dados:
            continue
        for tw in dados.get("tweets") or []:
            resultado[str(tw.get("id"))] = tw.get("viewCount") or 0
    return resultado


# ---------------------------------------------------------------- Telegram

def telegram(texto):
    url = f"https://api.telegram.org/bot{TG_TOKEN}/sendMessage"
    payload = {
        "chat_id": TG_CHAT,
        "text": texto,
        "parse_mode": "HTML",
        "disable_web_page_preview": False,
    }
    try:
        r = requests.post(url, json=payload, timeout=20)
        if r.status_code != 200:
            print(f"  Telegram falhou {r.status_code}: {r.text[:200]}")
            return False
        return True
    except requests.RequestException as e:
        print(f"  Telegram erro de rede: {e}")
        return False


def montar_alerta(post, views, checkpoint, mediana, mult_real):
    horas = checkpoint / 60
    idade = f"{horas:.0f}h" if horas >= 1 else f"{checkpoint}min"
    return (
        f"🔥 <b>@{post['autor']}</b> — {mult_real:.1f}x a média\n"
        f"{idade} · {fmt_num(views)} views "
        f"(normal: {fmt_num(int(mediana))})\n\n"
        f"{encurtar(post['texto'], CFG['tamanho_texto_alerta'])}\n\n"
        f"🔗 {post['url']}"
    )


# -------------------------------------------------------------------- ciclo

def main():
    global CFG
    CFG = carregar(ARQ_CONFIG, {})
    estado = carregar(ARQ_ESTADO, {
        "posts": {},
        "baseline": {},
        "ultima_busca": None,
        "alertas_enviados": 0,
    })

    perfis = CFG["perfis"]
    checkpoints = sorted(CFG["checkpoints_minutos"])
    limite_vida = checkpoints[-1]

    # janela de busca: desde a ultima rodada, com folga de 10 min
    if estado.get("ultima_busca"):
        desde = estado["ultima_busca"]
    else:
        desde = (agora().replace(microsecond=0)).isoformat()
        print("Primeira rodada: comecando a coletar a partir de agora.")

    # 1) coletar posts novos --------------------------------------------------
    novos = buscar_novos(perfis, desde)
    incluidos = 0
    for tw in novos:
        tid = str(tw.get("id") or "")
        if not tid or tid in estado["posts"]:
            continue
        if CFG.get("ignorar_respostas", True) and tw.get("isReply"):
            continue
        if CFG.get("ignorar_retweets", True) and tw.get("retweeted_tweet"):
            continue

        dt = parse_data(tw.get("createdAt"))
        if not dt:
            continue

        autor = (tw.get("author") or {}).get("userName") or ""
        if not autor:
            continue

        estado["posts"][tid] = {
            "autor": autor,
            "texto": encurtar(tw.get("text", ""), 400),
            "url": tw.get("url") or f"https://x.com/{autor}/status/{tid}",
            "criado": dt.isoformat(),
            "medicoes": {},
            "alertado": False,
        }
        incluidos += 1

    estado["ultima_busca"] = agora().replace(microsecond=0).isoformat()
    print(f"Posts novos guardados: {incluidos}")

    # 2) quem precisa de medicao agora ---------------------------------------
    a_medir = []
    for tid, p in estado["posts"].items():
        idade = idade_min(p["criado"])
        for cp in checkpoints:
            if idade >= cp and str(cp) not in p["medicoes"]:
                a_medir.append(tid)
                break

    print(f"Posts para medir: {len(a_medir)}")
    views_agora = atualizar_views(a_medir) if a_medir else {}

    # 3) registrar medicao, comparar e alertar --------------------------------
    alertas = 0
    for tid in a_medir:
        if tid not in views_agora:
            continue
        p = estado["posts"][tid]
        idade = idade_min(p["criado"])
        views = views_agora[tid]

        # marca todos os checkpoints ja vencidos com a medicao atual
        vencidos = [cp for cp in checkpoints if idade >= cp and str(cp) not in p["medicoes"]]
        for cp in vencidos:
            p["medicoes"][str(cp)] = views

        if p["alertado"]:
            continue

        cp = max(vencidos) if vencidos else None
        if cp is None:
            continue

        amostras = (estado["baseline"].get(p["autor"], {}).get(str(cp)) or [])
        if len(amostras) < CFG.get("amostras_minimas", 8):
            continue  # ainda aprendendo esse perfil

        med = median(amostras)
        if med <= 0:
            continue

        mult_exigido = CFG.get("multiplicador_por_perfil", {}).get(
            p["autor"], CFG.get("multiplicador_padrao", 3.0)
        )
        mult_real = views / med

        if mult_real >= mult_exigido:
            if telegram(montar_alerta(p, views, cp, med, mult_real)):
                p["alertado"] = True
                alertas += 1

    print(f"Alertas enviados: {alertas}")
    estado["alertas_enviados"] = estado.get("alertas_enviados", 0) + alertas

    # 4) aposentar posts velhos e alimentar a baseline ------------------------
    aposentados = 0
    for tid in list(estado["posts"].keys()):
        p = estado["posts"][tid]
        if idade_min(p["criado"]) < limite_vida + 30:
            continue

        base = estado["baseline"].setdefault(p["autor"], {})
        for cp, v in p["medicoes"].items():
            lista = base.setdefault(cp, [])
            lista.append(v)
            del lista[:-40]  # guarda so as 40 amostras mais recentes

        del estado["posts"][tid]
        aposentados += 1

    print(f"Posts aposentados: {aposentados}")

    # 5) relatorio de aprendizado --------------------------------------------
    prontos = []
    for perfil in perfis:
        base = estado["baseline"].get(perfil, {})
        n = len(base.get(str(checkpoints[0]), []))
        prontos.append(f"{perfil}:{n}")
    print("Amostras por perfil: " + " | ".join(prontos))

    salvar(ARQ_ESTADO, estado)


if __name__ == "__main__":
    main()
