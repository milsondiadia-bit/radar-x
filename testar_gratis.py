# -*- coding: utf-8 -*-
"""Testa se existe alguma forma GRATUITA de listar os posts recentes de um perfil."""
import json
import re
import requests

PERFIS = ["MarioNawfal", "clashreport"]
UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")
S = requests.Session()
S.headers.update({"User-Agent": UA})


def cabecalho(nome):
    print("\n" + "=" * 60)
    print(nome)
    print("=" * 60)


def metodo_1(perfil):
    """syndication.twitter.com - pagina HTML com JSON embutido."""
    url = f"https://syndication.twitter.com/srv/timeline-profile/screen-name/{perfil}"
    try:
        r = S.get(url, timeout=25)
        print(f"  HTTP {r.status_code} | {len(r.content)} bytes")
        if r.status_code != 200 or len(r.content) < 500:
            return 0
        m = re.search(r'<script id="__NEXT_DATA__"[^>]*>(.*?)</script>',
                      r.text, re.S)
        if not m:
            print("  sem __NEXT_DATA__ na pagina")
            return 0
        dados = json.loads(m.group(1))
        entradas = (dados.get("props", {}).get("pageProps", {})
                    .get("timeline", {}).get("entries", []))
        posts = [e for e in entradas if e.get("type") == "tweet"]
        print(f"  posts encontrados: {len(posts)}")
        if posts:
            c = posts[0].get("content", {}).get("tweet", {})
            print(f"  exemplo id={c.get('id_str')} "
                  f"favs={c.get('favorite_count')} "
                  f"texto={(c.get('text') or '')[:60]!r}")
            print(f"  tem contagem de views? "
                  f"{'sim' if c.get('views') else 'NAO'}")
        return len(posts)
    except Exception as e:
        print(f"  erro: {e}")
        return 0


def metodo_2(perfil):
    """cdn.syndication.twimg.com/timeline/profile"""
    url = "https://cdn.syndication.twimg.com/timeline/profile"
    try:
        r = S.get(url, params={"screen_name": perfil, "lang": "en"}, timeout=25)
        print(f"  HTTP {r.status_code} | {len(r.content)} bytes")
        if r.status_code == 200 and len(r.content) > 500:
            print(f"  inicio: {r.text[:200]!r}")
            return 1
        return 0
    except Exception as e:
        print(f"  erro: {e}")
        return 0


def metodo_3(perfil):
    """api.fxtwitter.com/{perfil} - devolve timeline?"""
    try:
        r = S.get(f"https://api.fxtwitter.com/{perfil}", timeout=25)
        print(f"  HTTP {r.status_code}")
        if r.status_code != 200:
            return 0
        d = r.json()
        u = d.get("user") or {}
        print(f"  chaves em user: {sorted(u.keys())}")
        for chave in ("tweets", "timeline", "latest_tweet", "recent"):
            if chave in u or chave in d:
                print(f"  >>> tem '{chave}'")
        return 1
    except Exception as e:
        print(f"  erro: {e}")
        return 0


for perfil in PERFIS:
    cabecalho(f"@{perfil} - metodo 1: syndication timeline-profile")
    metodo_1(perfil)
    cabecalho(f"@{perfil} - metodo 2: cdn.syndication timeline/profile")
    metodo_2(perfil)
    cabecalho(f"@{perfil} - metodo 3: fxtwitter perfil")
    metodo_3(perfil)
