# -*- coding: utf-8 -*-
"""
Mede quanto o filtro de engajamento cortaria da busca do Radar X.
Compara a MESMA janela com e sem min_faves.
"""
import json
import os
import time
from datetime import datetime, timedelta, timezone

import requests

CHAVE = os.environ["TWITTERAPI_KEY"]
BASE = "https://api.twitterapi.io"
PERFIS = ["MarioNawfal", "Osint613", "clashreport", "nexta_tv",
          "NewsLiberdade", "MachadoDarlon"]

# janela de 1 hora, parecida com o volume de uma rodada acumulada
desde = int((datetime.now(timezone.utc) - timedelta(hours=1)).timestamp())
grupo = "(" + " OR ".join(f"from:{p}" for p in PERFIS) + ")"


def buscar(consulta, max_paginas=6):
    total, cursor, pagina = 0, None, 0
    favs = []
    while pagina < max_paginas:
        params = {"query": consulta, "queryType": "Latest"}
        if cursor:
            params["cursor"] = cursor
        r = requests.get(f"{BASE}/twitter/tweet/advanced_search",
                         headers={"X-API-Key": CHAVE}, params=params, timeout=30)
        if r.status_code != 200:
            print(f"    HTTP {r.status_code}: {r.text[:150]}")
            break
        d = r.json()
        lote = d.get("tweets") or []
        total += len(lote)
        for t in lote:
            favs.append(t.get("likeCount") or t.get("favorite_count") or 0)
        if not lote or not d.get("has_next_page"):
            break
        cursor = d.get("next_cursor")
        if not cursor:
            break
        pagina += 1
        time.sleep(1)
    return total, favs


print("=" * 60)
print("MEDICAO DO FILTRO DE ENGAJAMENTO - janela de 1 hora")
print("=" * 60)

base = f"{grupo} since_time:{desde} -filter:replies"
print("\n[SEM FILTRO]")
total, favs = buscar(base)
print(f"  posts: {total}  (~{total*15} creditos)")

if favs:
    favs_ord = sorted(favs)
    n = len(favs_ord)
    print(f"  curtidas: minimo={favs_ord[0]} "
          f"mediana={favs_ord[n//2]} maximo={favs_ord[-1]}")
    print("\n  quantos sobrariam com cada piso de curtidas:")
    for piso in (10, 25, 50, 100, 200, 500):
        sobram = sum(1 for f in favs if f >= piso)
        corte = 100 * (1 - sobram / n) if n else 0
        print(f"    min_faves:{piso:<4} -> {sobram:3} posts "
              f"({corte:.0f}% de corte, ~{sobram*15} creditos)")

print("\n[COM min_faves:50 - conferindo na pratica]")
total2, _ = buscar(f"{base} min_faves:50")
print(f"  posts: {total2}  (~{total2*15} creditos)")

print(f"\nCUSTO DESTA MEDICAO: ~{(total+total2)*15} creditos")
