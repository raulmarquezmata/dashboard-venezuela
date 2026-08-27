# -*- coding: utf-8 -*-
"""
validar.py - Comprueba que el dashboard generado sea valido.

Se ejecuta en el workflow despues de build.py. Verifica que el HTML tenga la
misma cantidad de noticias que news.json y extrae el JavaScript a /tmp/c.js
para que 'node --check' confirme la sintaxis.

Uso:  python validar.py
"""
import json
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).parent
HTML = RAIZ / "salida" / "venezuela_dashboard.html"
JSON = RAIZ / "news.json"


def main() -> int:
    if not HTML.exists():
        print(f"ERROR: no existe {HTML}. ¿Corrio build.py?")
        return 1

    html = HTML.read_text(encoding="utf-8")
    datos = json.loads(JSON.read_text(encoding="utf-8"))

    ini = html.index("const NOTICIAS = [")
    fin = html.index("];", ini)
    bloque = html[ini:fin]

    n_html = bloque.count("{cat:'")
    n_json = len(datos)
    enlaces = bloque.count("url:'")

    if n_html != n_json:
        print(f"ERROR: {n_html} noticias en el HTML vs {n_json} en news.json")
        return 1

    if bloque.count("{") != bloque.count("}"):
        print("ERROR: llaves desbalanceadas en el array NOTICIAS")
        return 1

    scripts = re.findall(r"<script>(.*?)</script>", html, re.S)
    Path("/tmp/c.js").write_text("\n".join(scripts), encoding="utf-8")

    print(f"OK: {n_html} noticias, {enlaces} enlaces. "
          f"JavaScript extraido a /tmp/c.js para node --check.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
