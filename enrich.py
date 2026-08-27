# -*- coding: utf-8 -*-
"""
enrich.py — Busca fuentes ADICIONALES para noticias que tienen pocas.

Cómo funciona: por cada noticia con menos de N fuentes, extrae las palabras
más distintivas del titular, consulta el RSS de Google News (gratis, sin API
key), y agrega los resultados cuyo titular se parece lo suficiente al original
—medido con SequenceMatcher— descartando dominios ya presentes o excluidos.

El umbral de similitud (config.UMBRAL_SIMILITUD) es la perilla importante:
demasiado bajo mete noticias distintas del mismo tema; demasiado alto no
encuentra nada porque cada medio titula distinto. 0.42 es un punto de partida
razonable para español; ajustalo mirando el log de las primeras corridas.

Uso:
    python enrich.py                    # enriquece las que tengan <2 fuentes
    python enrich.py --min 3            # apunta a mínimo 3 fuentes
    python enrich.py --limite 25        # procesa solo 25 (para probar)
    python enrich.py --dry-run          # muestra qué agregaría, sin guardar

IMPORTANTE: hace una petición HTTP por noticia. Con --limite y la pausa
incorporada evitás que Google te corte. Si empieza a devolver vacío de golpe,
esperá unos minutos: es rate limiting, no un bug.
"""
import re
import sys
import time
import html as htmllib
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from difflib import SequenceMatcher

import config
import common
from common import normalizar, dominio, peso_dominio

UA = "Mozilla/5.0 (compatible; SolfinResearch/1.0)"
PAUSA = 1.6          # segundos entre peticiones
TIMEOUT = 20

# Palabras sin valor discriminante al construir la consulta.
VACIAS = set("""de la el en los las un una y o a al del que por con para se su sus
es son fue fueron sera seran mas menos como sobre entre desde hasta este esta
estos estas lo le les ya no ni tras ante bajo cabe contra durante mediante segun
sin so tambien porque cuando donde cual cuales quien quienes cuanto muy tan
millones millon mil por ciento porciento dato datos analisis clave claves""".split())


def _consulta(titular: str, n=8) -> str:
    """Extrae los términos más distintivos del titular."""
    pals = re.findall(r"[a-záéíóúñü0-9\.\,]+", titular.lower())
    utiles = [p for p in pals if normalizar(p) not in VACIAS and len(p) > 2]
    # Prioriza palabras largas (suelen ser las entidades y los tecnicismos).
    utiles.sort(key=len, reverse=True)
    vistos, sel = set(), []
    for p in utiles:
        k = normalizar(p)
        if k not in vistos:
            vistos.add(k)
            sel.append(p)
        if len(sel) >= n:
            break
    return " ".join(sel)


def buscar_google_news(consulta: str) -> list:
    """Devuelve [(titulo, url, medio)] desde el RSS de Google News."""
    url = ("https://news.google.com/rss/search?q="
           + urllib.parse.quote(consulta)
           + "&hl=es-419&gl=VE&ceid=VE:es-419")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            xml = r.read()
    except Exception as e:
        print(f"    [red] {type(e).__name__}: {e}")
        return []
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError:
        return []
    out = []
    for item in raiz.iter('item'):
        t = item.findtext('title') or ''
        l = item.findtext('link') or ''
        src = item.find('source')
        medio = (src.text if src is not None and src.text else '')
        # Google agrega " - Medio" al final del titular; lo separamos.
        if ' - ' in t and medio and t.endswith(' - ' + medio):
            t = t[: -(len(medio) + 3)]
        out.append((htmllib.unescape(t).strip(), l.strip(), medio.strip()))
    return out


def similar(a: str, b: str) -> float:
    return SequenceMatcher(None, normalizar(a), normalizar(b)).ratio()


def enriquecer(items: list, minimo=2, limite=None, dry=False) -> int:
    objetivo = [it for it in items if len(it.get('sources', [])) < minimo]
    if limite:
        objetivo = objetivo[:limite]
    print(f"Noticias con menos de {minimo} fuentes: {len(objetivo)}"
          + (f" (procesando {limite})" if limite else "") + "\n")

    agregadas = 0
    for i, it in enumerate(objetivo, 1):
        titular = it['es']['title']
        q = _consulta(titular)
        print(f"[{i}/{len(objetivo)}] {titular[:72]}")
        print(f"    q: {q}")
        res = buscar_google_news(q)
        presentes = {dominio(s['url']) for s in it.get('sources', [])}

        cand = []
        for t, u, medio in res:
            d = dominio(u)
            if not d or d in presentes:
                continue
            if any(x in d for x in config.DOMINIOS_EXCLUIDOS):
                continue
            s = similar(titular, t)
            if s >= config.UMBRAL_SIMILITUD:
                cand.append((peso_dominio(u), -s, medio or d, u, s, t))

        cand.sort()
        cupo = config.MAX_FUENTES - len(it.get('sources', []))
        nuevas = []
        for _, _, medio, u, s, t in cand[:cupo]:
            d = dominio(u)
            if d in presentes:
                continue
            presentes.add(d)
            nuevas.append({'text': medio, 'url': u})
            print(f"    + [{s:.2f}] {medio}: {t[:60]}")

        if nuevas:
            if not dry:
                it.setdefault('sources', []).extend(nuevas)
            agregadas += len(nuevas)
        else:
            print("    (sin coincidencias por encima del umbral)")
        time.sleep(PAUSA)

    return agregadas


def main():
    args = sys.argv[1:]
    def opt(nombre, defecto=None, tipo=int):
        if nombre in args:
            return tipo(args[args.index(nombre) + 1])
        return defecto

    minimo = opt('--min', 2)
    limite = opt('--limite', None)
    dry = '--dry-run' in args

    items = common.cargar_noticias()
    n = enriquecer(items, minimo, limite, dry)

    print(f"\nFuentes nuevas encontradas: {n}")
    if dry:
        print("--dry-run: no se guardó nada.")
    elif n:
        common.guardar_noticias(items)
        print("news.json actualizado. Corré 'python build.py' para "
              "regenerar el HTML y el Excel.")
    else:
        print("Nada que guardar.")


if __name__ == '__main__':
    main()
