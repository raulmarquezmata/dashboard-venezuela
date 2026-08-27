# -*- coding: utf-8 -*-
"""
promote.py — Mueve los candidatos aprobados de bandeja.json a news.json.

Solo promueve los que tengan 'aprobado': true, categoría válida y titular.
Los demás quedan en la bandeja para la próxima revisión.

Uso:
    python promote.py
    python promote.py --forzar     # promueve aunque falten preview/body
"""
import sys, json
from pathlib import Path
import config, common

RAIZ = Path(__file__).parent
BANDEJA = RAIZ / "bandeja.json"

def main():
    forzar = '--forzar' in sys.argv
    if not BANDEJA.exists():
        raise SystemExit("No hay bandeja.json. Corré 'python ingest.py' primero.")
    cand = json.loads(BANDEJA.read_text(encoding='utf-8'))
    items = common.cargar_noticias()
    urls = {s['url'] for it in items for s in it.get('sources', [])}

    promovidos, quedan, rechazos = [], [], []
    for c in cand:
        if not c.get('aprobado'):
            quedan.append(c); continue
        if c['url'] in urls:
            rechazos.append((c['titulo'][:60], "URL ya presente")); continue
        if c.get('cat') not in config.CATS_HTML:
            rechazos.append((c['titulo'][:60], f"categoría inválida: '{c.get('cat')}'"))
            quedan.append(c); continue
        if not forzar and not c.get('body'):
            rechazos.append((c['titulo'][:60], "falta 'body' (usá --forzar para omitir)"))
            quedan.append(c); continue
        promovidos.append({
            'cat': c['cat'],
            'date': c.get('fecha_sugerida') or '',
            'es': {'title': c['titulo'],
                   'preview': c.get('preview',''),
                   'body': c.get('body','')},
            'en': {'title': c.get('titulo_en','')},
            'sectors': c.get('sectores', []),
            'sources': [{'text': c['medio'], 'url': c['url']}],
        })

    if rechazos:
        print("No promovidos:")
        for t, r in rechazos: print(f"  - {t}  ({r})")
    if promovidos:
        items.extend(promovidos)
        common.guardar_noticias(items)
        BANDEJA.write_text(json.dumps(quedan, ensure_ascii=False, indent=1), encoding='utf-8')
        print(f"\n{len(promovidos)} noticias promovidas. news.json: {len(items)} en total.")
        print("Siguiente: python enrich.py  y luego  python build.py")
    else:
        print("\nNada promovido.")

if __name__ == '__main__':
    main()
