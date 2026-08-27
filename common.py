# -*- coding: utf-8 -*-
"""Utilidades compartidas: normalización, fechas, clasificación, dominios."""
import re
import json
import unicodedata
from pathlib import Path
from urllib.parse import urlparse

import config

RAIZ = Path(__file__).parent
NEWS_JSON = RAIZ / "news.json"

MESES = {'ene':1,'feb':2,'mar':3,'abr':4,'may':5,'jun':6,
         'jul':7,'ago':8,'sep':9,'oct':10,'nov':11,'dic':12}
MESES_INV = {v:k for k,v in MESES.items()}
MESES_NOMBRE = {1:'Enero',2:'Febrero',3:'Marzo',4:'Abril',5:'Mayo',6:'Junio',
                7:'Julio',8:'Agosto',9:'Septiembre',10:'Octubre',
                11:'Noviembre',12:'Diciembre'}


def normalizar(texto: str) -> str:
    """Minúsculas sin acentos, para comparar y clasificar."""
    t = unicodedata.normalize('NFKD', (texto or '').lower())
    return ''.join(c for c in t if not unicodedata.combining(c))


def clave_fecha(fecha: str):
    """'12 ago 2026' -> (2026, 8, 12). Ordenable. (0,0,0) si no parsea."""
    f = (fecha or '').strip()
    m = re.match(r'(\d{1,2})\s+(\w{3})\w*\s+(\d{4})', f)
    if m:
        return (int(m.group(3)), MESES.get(m.group(2)[:3].lower(), 0), int(m.group(1)))
    m = re.match(r'(\w{3})\w*\s*-?\s*\w*\s*(\d{4})', f)
    if m:
        return (int(m.group(2)), MESES.get(m.group(1)[:3].lower(), 0), 0)
    return (0, 0, 0)


def fecha_es(dt) -> str:
    """datetime -> '12 ago 2026' (formato del dashboard)."""
    return f"{dt.day} {MESES_INV[dt.month]} {dt.year}"


def dominio(url: str) -> str:
    try:
        d = urlparse(url).netloc.lower()
        return d[4:] if d.startswith('www.') else d
    except Exception:
        return ''


def _coincide(kw: str, txt: str) -> bool:
    if kw.startswith('#'):
        return re.search(r'\b' + re.escape(kw[1:]) + r'\b', txt) is not None
    return kw in txt


def clasificar(item: dict):
    """Devuelve (categoria_principal, 'sec1; sec2')."""
    txt = normalizar(item['es']['title'] + ' ' + ' '.join(item.get('sectors', [])))
    hits = [cat for cat, kws in config.RULES if any(_coincide(k, txt) for k in kws)]
    if not hits:
        return config.FALLBACK.get(item.get('cat', ''), 'Otros'), ''
    return hits[0], '; '.join(hits[1:3])


def peso_dominio(url: str) -> int:
    """Menor es mejor. Para ordenar fuentes por jerarquía editorial."""
    d = dominio(url)
    for i, pref in enumerate(config.DOMINIOS_PREFERIDOS):
        if pref in d:
            return i
    return 999


def cargar_noticias() -> list:
    with open(NEWS_JSON, encoding='utf-8') as fh:
        return json.load(fh)


def guardar_noticias(items: list) -> None:
    """Ordena por fecha descendente, deduplica fuentes y guarda.

    La deduplicación es por URL, NO por dominio: un mismo portal puede aportar
    varios artículos distintos a una noticia (la fuente principal más notas de
    contexto), y colapsarlos por dominio destruiría esas referencias cruzadas.
    El peso del dominio se usa solo para ORDENAR, poniendo primero las fuentes
    primarias y las agencias.
    """
    for it in items:
        vistos, limpias = set(), []
        for s in sorted(it.get('sources', []), key=lambda s: peso_dominio(s['url'])):
            u = (s.get('url') or '').rstrip('/')
            d = dominio(u)
            if not u or u in vistos:
                continue
            if any(x in d for x in config.DOMINIOS_EXCLUIDOS):
                continue
            vistos.add(u)
            limpias.append(s)
        it['sources'] = limpias[:config.MAX_FUENTES]
    items.sort(key=lambda x: clave_fecha(x['date']), reverse=True)
    with open(NEWS_JSON, 'w', encoding='utf-8') as fh:
        json.dump(items, fh, ensure_ascii=False, indent=1)


def escapar_js(s: str) -> str:
    """Escapa para literal JavaScript entre comillas simples."""
    return (s or '').replace('\\', '\\\\').replace("'", "\\'").replace('\n', ' ')
