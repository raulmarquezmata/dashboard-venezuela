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


def buscar_noticias(consulta: str) -> list:
    """Devuelve [(titulo, url, medio)] desde el RSS de búsqueda de Bing News.

    Se usa Bing en vez de Google News porque el RSS de Google no entrega el
    enlace del artículo: entrega un enlace propio de redirección
    (news.google.com/rss/articles/...) que solo resuelve mediante JavaScript
    del lado del navegador — un HEAD o GET normal no lo sigue, así que
    filtrar por dominio deja SIEMPRE ese dominio (news.google.com), que
    además está excluido a propósito, y el resultado es que nunca se
    aceptaba ninguna fuente. Bing entrega el link real del portal
    directamente, sin ese problema.

    Registra cada fallo explícitamente: sin esto, un problema de red o un
    bloqueo devuelve una lista vacía indistinguible de una búsqueda legítima
    sin resultados, sin dar ninguna pista de por qué.
    """
    url = ("https://www.bing.com/news/search?q="
           + urllib.parse.quote(consulta)
           + "&format=RSS&setmkt=es-419&cc=VE")
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
            status = r.status
            xml = r.read()
    except Exception as e:
        print(f"    [DIAG] petición HTTP falló: {type(e).__name__}: {e}")
        return []
    if status != 200:
        print(f"    [DIAG] HTTP {status} (se esperaba 200)")
        return []
    if not xml or len(xml) < 50:
        print(f"    [DIAG] respuesta vacía o demasiado corta ({len(xml)} bytes)")
        return []
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError as e:
        print(f"    [DIAG] la respuesta no es XML válido ({e}). "
              f"Primeros 200 bytes: {xml[:200]!r}")
        return []
    out = []
    for item in raiz.iter('item'):
        t = item.findtext('title') or ''
        l = item.findtext('link') or ''
        # Bing no siempre trae una etiqueta de fuente separada; cuando no
        # está, se usa el dominio del enlace como nombre visible provisorio
        # (queda prolijo igual: "elnacional.com" en vez de vacío).
        medio = ''
        for tag in ('source', 'Source', '{http://schemas.microsoft.com/rss/1.0}Source'):
            el = item.find(tag)
            if el is not None and el.text:
                medio = el.text
                break
        out.append((htmllib.unescape(t).strip(), l.strip(), medio.strip()))
    return out


def _anclas(t: str) -> set:
    """Nombres propios (mayúscula fuera del inicio de frase, o siglas) y
    cifras. Es una aproximación barata a 'entidad nombrada' sin librerías de
    NLP: casi siempre acierta con marcas, personas, instituciones y montos,
    e ignora adjetivos y sustantivos comunes aunque sean largos (a diferencia
    de filtrar solo por longitud de palabra, que deja pasar falsos positivos
    como "venezolana" o "farmacéutica").
    """
    out = set()
    for m in re.finditer(r'\d[\d\.,%]*', t):
        out.add(m.group())
    for i, p in enumerate(t.split()):
        limpio = re.sub(r'[^\wÁÉÍÓÚÑáéíóúñ]', '', p)
        if not limpio:
            continue
        if limpio[0].isupper() and (i > 0 or limpio.isupper()):
            out.add(normalizar(limpio))
    return out


def _jaccard(a: str, b: str) -> float:
    A, B = set(normalizar(a).split()), set(normalizar(b).split())
    return len(A & B) / len(A | B) if A and B else 0.0


def similar(a: str, b: str) -> float:
    """Similitud entre dos titulares, calibrada para el caso real: el mismo
    hecho contado por dos medios con redacción distinta.

    Combina estructura (SequenceMatcher) y contenido (solapamiento de
    palabras), pero exige además que compartan al menos una 'ancla' —una
    cifra o un nombre propio— porque el promedio solo puede dar falsos
    positivos altos entre noticias de temas distintos con la misma forma de
    frase ("La industria X venezolana reporta crecimiento de Y% en el primer
    semestre" empata alto entre farmacéutica y automotriz sin esa exigencia).
    Sin ancla compartida, se devuelve 0.0 sin más cálculo.
    """
    if not (_anclas(a) & _anclas(b)):
        return 0.0
    sm = SequenceMatcher(None, normalizar(a), normalizar(b)).ratio()
    jc = _jaccard(a, b)
    return (sm + jc) / 2


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
        res = buscar_noticias(q)
        presentes = {dominio(s['url']) for s in it.get('sources', [])}

        # Comparo TITULARES primero (barato). Bing entrega el link directo
        # del portal, así que no hace falta resolver ninguna redirección
        # antes de poder filtrar por dominio.
        cand, sin_ancla, bajo_umbral, descartados_dominio = [], 0, 0, 0
        for t, u, medio in res:
            s = similar(titular, t)
            if s == 0.0:
                sin_ancla += 1
                continue
            if s < config.UMBRAL_SIMILITUD:
                bajo_umbral += 1
                continue
            d = dominio(u)
            if not d or d in presentes or any(x in d for x in config.DOMINIOS_EXCLUIDOS):
                descartados_dominio += 1
                continue
            presentes.add(d)
            cand.append((peso_dominio(u), -s, medio or d, u, s, t))

        print(f"    [DIAG] feed: {len(res)} resultados | "
              f"sin ancla compartida: {sin_ancla} | "
              f"con ancla pero bajo umbral: {bajo_umbral} | "
              f"descartados por dominio (ya presente/excluido): {descartados_dominio} | "
              f"aceptados: {len(cand)}")
        cand.sort()
        cupo = config.MAX_FUENTES - len(it.get('sources', []))
        nuevas = []
        for _, _, medio, u, s, t in cand[:cupo]:
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
