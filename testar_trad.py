# -*- coding: utf-8 -*-
"""Confere a traducao com textos reais dos perfis monitorados."""
import radar

EXEMPLOS = [
    ("nexta_tv (bloqueio infantil - deve continuar sem traducao)",
     "Russian women massively showed up at school assemblies in revealing, "
     "sexual outfits. At the ceremonial events packed with little children, "
     "the moms were flaunting themselves in stockings, mini-skirts..."),
    ("guerra - antes podia ser bloqueado",
     "Reports from Mashhad, Iran, say a vehicle drove into a pro IRGC "
     "gathering in the Eghbal Lahouri area, with a very large number of "
     "casualties reported. Emergency services are on site."),
    ("missil / conflito armado",
     "Russia has secretly helped Iran develop advanced supersonic cruise "
     "missiles able to threaten US aircraft carriers and warships in the "
     "Middle East, an investigation found."),
    ("politica",
     "Zelenskyy said that Ukraine is launching a campaign to block Russia's "
     "airspace. We want to warn every airline that uses Russian airspace, "
     "every insurer, and everyone who still uses key Russian airports."),
]

print("=" * 60)
print("Modelos:", ", ".join(radar.MODELOS))
print("=" * 60)

for rotulo, texto in EXEMPLOS:
    print("\n--- " + rotulo)
    saida = radar.traduzir(texto)
    ok = saida.strip() != texto.strip() and not saida.startswith("\u26a0")
    print("   ", ("TRADUZIU" if ok else "NAO TRADUZIU"))
    print("   ", saida[:200])
