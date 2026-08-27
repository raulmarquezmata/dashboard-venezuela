# -*- coding: utf-8 -*-
"""
ingest.py — Detecta artículos NUEVOS en los feeds RSS de los portales vigilados.

No los mete al dashboard automáticamente. Los deja en 'bandeja.json' para
revisión, porque un feed trae de todo (deportes, sucesos, farándula) y el
dashboard es un producto de research: la curaduría no se puede delegar a un
filtro de palabras clave sin degradar la calidad.

Flujo previsto:
    1. python ingest.py              -> llena bandeja.json con candidatos
    2. Revisás bandeja.json, borrás lo que no sirve, redactás cuerpo y
       preview de lo que sí (o me lo pasás a mí y lo redacto)
    3. python promote.py             -> mueve lo aprobado a news.json
    4. python enrich.py              -> les busca fuentes adicionales
    5. python build.py               -> regenera HTML + Excel

Uso:
    python ingest.py                 # últimos 7 días
    python ingest.py --dias 3
    python ingest.py --feed "Banca y Negocios"
"""
import re
import sys
import json
import time
import html as htmllib
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

import config
import common
from common import normalizar, dominio

RAIZ = Path(__file__).parent
BANDEJA = RAIZ / "bandeja.json"
UA = "Mozilla/5.0 (compatible; SolfinResearch/1.0)"
TIMEOUT = 25

# Términos que hacen a un artículo candidato. Amplios a propósito:
# es preferible revisar de más que perderse algo.
RELEVANTES = """
petroleo petrolera crudo pdvsa opep merey refineria refinacion gasolina gas
barril barriles chevron shell repsol eni ongc slb hunt exportacion exportaciones
bcv banco banca banco banesco mercantil provincial bnc bancaribe credito cartera
deposito depositos divisa divisas cambiario dolar bolivar inflacion inpc pib
reservas encaje liquidez monetario tasa intervencion
ofac sancion sanciones licencia fincen bloqueo bloqueado activos oro citgo bono
bonos deuda reestructuracion acreedores riesgo pais
bolsa bvc sunaval bursatil ibc accion acciones emision titularizacion fondo
electric electrico megavatio mw termoelectrica corpoelec apagon gener sen guri
agro agricola cafe cacao arroz maiz azucar cana fedeagro cosecha fertilizante
sequia nino clima commodities hierro mineria
telecomunicacion cantv conatel movilnet internet cable starlink
sudeban sudeaseg seguro seguros aseguradora primas
seniat tributario impuesto fiscal arancel
inversion inversiones acuerdo acuerdos contrato empresa mixta joint
fmi cepal pnud banco mundial proyeccion crecimiento
dialogo tsj asamblea gaceta decreto ley reglamento providencia
terremoto sismo reconstruccion damnificados vivienda
"""
CLAVES = {normalizar(w) for w in RELEVANTES.split() if len(w) > 3}

# Términos que descartan de plano.
DESCARTE = {normalizar(w) for w in """
futbol beisbol deporte deportes liga vinotinto goleada partido torneo
farandula miss belleza horoscopo receta viral tiktok
homicidio asesinato asesino detenido femicidio secuestro cadaver
""".split()}


def leer_feed(url: str) -> list:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:
        return _parsear(r.read())


def _parsear(xml: bytes) -> list:
    try:
        raiz = ET.fromstring(xml)
    except ET.ParseError:
        return []
    out = []
    # RSS 2.0
    for it in raiz.iter('item'):
        out.append({
            'titulo': htmllib.unescape((it.findtext('title') or '').strip()),
            'url': (it.findtext('link') or '').strip(),
            'fecha': it.findtext('pubDate') or '',
            'resumen': _limpiar(it.findtext('description') or ''),
        })
    # Atom
    if not out:
        ns = '{http://www.w3.org/2005/Atom}'
        for it in raiz.iter(ns + 'entry'):
            link = it.find(ns + 'link')
            out.append({
                'titulo': htmllib.unescape((it.findtext(ns + 'title') or '').strip()),
                'url': (link.get('href') if link is not None else '').strip(),
                'fecha': it.findtext(ns + 'updated') or '',
                'resumen': _limpiar(it.findtext(ns + 'summary') or ''),
            })
    return out


def _limpiar(s: str) -> str:
    s = re.sub(r'<[^>]+>', ' ', htmllib.unescape(s))
    return re.sub(r'\s+', ' ', s).strip()[:400]


def _fecha(cad: str):
    for parser in (parsedate_to_datetime, datetime.fromisoformat):
        try:
            d = parser(cad)
            return d if d.tzinfo else d.replace(tzinfo=timezone.utc)
        except Exception:
            continue
    return None


def relevante(titulo: str, resumen: str) -> bool:
    txt = normalizar(titulo + ' ' + resumen)
    pals = set(re.findall(r'[a-z0-9]+', txt))
    if pals & DESCARTE:
        return False
    return bool(pals & CLAVES)


def main():
    args = sys.argv[1:]
    dias = int(args[args.index('--dias') + 1]) if '--dias' in args else 7
    solo = args[args.index('--feed') + 1] if '--feed' in args else None

    corte = datetime.now(timezone.utc) - timedelta(days=dias)
    existentes = {dominio(s['url']) + urllib.request.urlparse(s['url']).path
                  if False else s['url']
                  for it in common.cargar_noticias() for s in it.get('sources', [])}

    feeds = {k: v for k, v in config.FEEDS.items() if not solo or k == solo}
    candidatos, fallidos = [], []

    for medio, url in feeds.items():
        try:
            entradas = leer_feed(url)
        except Exception as e:
            fallidos.append(f"{medio}: {type(e).__name__}")
            continue
        nuevos = 0
        for e in entradas:
            if not e['url'] or e['url'] in existentes:
                continue
            d = _fecha(e['fecha'])
            if d and d < corte:
                continue
            if not relevante(e['titulo'], e['resumen']):
                continue
            candidatos.append({
                'medio': medio,
                'fecha_rss': e['fecha'],
                'fecha_sugerida': common.fecha_es(d) if d else '',
                'titulo': e['titulo'],
                'url': e['url'],
                'resumen': e['resumen'],
                # Campos a completar en la revisión:
                'cat': '', 'sectores': [], 'preview': '', 'body': '',
                'aprobado': False,
            })
            nuevos += 1
        print(f"  {medio:22s} {nuevos:3d} candidatos de {len(entradas)} entradas")
        time.sleep(0.8)

    if fallidos:
        print("\nFeeds que fallaron (revisar la URL en config.py):")
        for f in fallidos:
            print("  -", f)

    BANDEJA.write_text(json.dumps(candidatos, ensure_ascii=False, indent=1),
                       encoding='utf-8')
    print(f"\n{len(candidatos)} candidatos -> {BANDEJA}")
    print("Revisá el archivo, poné 'aprobado': true y completá cat/preview/body "
          "en los que quieras conservar, luego corré: python promote.py")


if __name__ == '__main__':
    main()
