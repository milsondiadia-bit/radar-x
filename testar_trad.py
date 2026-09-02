# -*- coding: utf-8 -*-
"""Testa a traducao com o texto exato que veio em ingles no Telegram."""
import json
import os
import requests
import radar

TEXTO = ("\U0001F4AB Russian women massively showed up at school assemblies "
         "in revealing, sexual outfits\n\nAt the ceremonial events packed with "
         "little (and not-so-little) children, the moms were flaunting "
         "themselves in stockings, mini-skirts...")

print("=" * 60)
print("Modelos:", ", ".join(radar.MODELOS))
print("=" * 60)

# 1) resposta crua do Gemini, para ver o motivo exato
url = ("https://generativelanguage.googleapis.com/v1beta/models/"
       "gemini-3.1-flash-lite:generateContent")
pedido = (
    "Traduza o texto abaixo para portugues do Brasil. "
    "Traduza o texto INTEIRO, do inicio ao fim, sem cortar. "
    "Responda SOMENTE com a traducao, sem aspas, sem comentarios, "
    "sem explicacao. Mantenha nomes proprios, siglas, @perfis e hashtags "
    "como estao. Se o texto ja estiver em portugues, devolva-o inalterado.\n\n"
    + TEXTO
)
r = requests.post(
    url,
    headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"],
             "Content-Type": "application/json"},
    json={"contents": [{"parts": [{"text": pedido}]}],
          "generationConfig": {"temperature": 1, "maxOutputTokens": 4000,
                               "thinkingConfig": {"thinkingLevel": "low"}}},
    timeout=30,
)
print("\n[RESPOSTA CRUA DO GEMINI]")
print("HTTP", r.status_code)
d = r.json()
print(json.dumps(d, ensure_ascii=False, indent=1)[:1500])

# 2) o que a funcao do bot devolve
print("\n[PELA FUNCAO DO BOT]")
saida = radar.traduzir(TEXTO)
print("SAIDA:", saida[:400])
print("MUDOU?", "sim" if saida.strip() != TEXTO.strip() else "NAO - devolveu o original")
