# -*- coding: utf-8 -*-
"""Descobre quais modelos existem na chave e testa um tradutor de reserva."""
import json
import os
import requests
from urllib.parse import quote

CHAVE = os.environ["GEMINI_API_KEY"]

TEXTO = ("\U0001F4AB Russian women massively showed up at school assemblies "
         "in revealing, sexual outfits\n\nAt the ceremonial events packed with "
         "little (and not-so-little) children, the moms were flaunting "
         "themselves in stockings, mini-skirts...")

print("=" * 60)
print("MODELOS DISPONIVEIS NESTA CHAVE")
print("=" * 60)
r = requests.get("https://generativelanguage.googleapis.com/v1beta/models",
                 headers={"x-goog-api-key": CHAVE}, timeout=30)
if r.status_code == 200:
    for m in r.json().get("models", []):
        nome = m["name"].replace("models/", "")
        if "generateContent" in (m.get("supportedGenerationMethods") or []):
            if "flash" in nome or "lite" in nome:
                print("  ", nome)
else:
    print("  HTTP", r.status_code, r.text[:200])

print()
print("=" * 60)
print("TRADUTOR DE RESERVA (Google Translate publico, sem chave)")
print("=" * 60)


def traduzir_google(texto, destino="pt"):
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": "auto", "tl": destino,
              "dt": "t", "q": texto}
    r = requests.get(url, params=params, timeout=25,
                     headers={"User-Agent": "Mozilla/5.0"})
    if r.status_code != 200:
        print("  HTTP", r.status_code)
        return None
    dados = r.json()
    return "".join(p[0] for p in dados[0] if p and p[0])


saida = traduzir_google(TEXTO)
print("SAIDA:", saida)
print()
print("MUDOU?", "sim" if saida and saida.strip() != TEXTO.strip() else "NAO")
