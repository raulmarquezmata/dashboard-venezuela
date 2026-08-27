# Pipeline de inteligencia Venezuela — Grupo Solfín

Mantiene sincronizados el **dashboard HTML** y el **inventario Excel** desde una
sola fuente de datos, y automatiza la búsqueda de fuentes adicionales para cada
noticia.

## El cambio de arquitectura

Antes: el HTML era la fuente de verdad y el Excel una foto derivada que quedaba
vieja al día siguiente.

Ahora: **`news.json` es la única fuente de verdad.** El HTML y el Excel son
salidas generadas. No pueden desincronizarse porque ambos se producen del mismo
archivo en la misma corrida.

```
                       ┌──────────────┐
   ingest.py  ───────► │  bandeja     │ ──► revisión humana ──► promote.py
   (feeds RSS)         │  .json       │                              │
                       └──────────────┘                              ▼
                                                          ┌────────────────┐
   enrich.py  ◄────────────────────────────────────────── │   news.json    │
   (+ fuentes)  ─────────────────────────────────────────►│  (verdad)      │
                                                          └────────┬───────┘
                                                                   │
                                                            build.py
                                                                   │
                                          ┌────────────────────────┴───────┐
                                          ▼                                ▼
                            venezuela_dashboard.html      inventario_noticias.xlsx
```

## Instalación

```bash
pip install -r requirements.txt      # solo openpyxl
```

Python 3.9+. `enrich.py` e `ingest.py` usan únicamente la librería estándar.

## Los cinco comandos

```bash
python ingest.py --dias 7      # 1. busca artículos nuevos en los feeds
                               #    -> bandeja.json (NO entra al dashboard aún)

#  2. Revisás bandeja.json: borrás lo que no sirve, y en lo que sí ponés
#     "aprobado": true, "cat": "oil", "preview": "...", "body": "..."

python promote.py              # 3. mueve lo aprobado a news.json
python enrich.py --min 3       # 4. busca más fuentes para las que tengan pocas
python build.py                # 5. regenera HTML + Excel
```

Salidas en `salida/`.

### Por qué la ingesta no es automática

Un feed RSS trae de todo: sucesos, deportes, farándula. `ingest.py` filtra por
palabras clave y descarta lo obvio, pero decidir si una noticia entra a un
producto de research —y con qué encuadre— es criterio editorial. Automatizarlo
degradaría la calidad que el dashboard tiene hoy. Por eso la bandeja.

El **enriquecimiento sí es automático**: buscar la misma noticia en otros
portales es una tarea mecánica y verificable.

## Automatización desatendida

`.github/workflows/actualizar.yml` corre de lunes a viernes a las 7:00 AM
Caracas en GitHub Actions (gratis en repos privados hasta cierta cuota):
enriquece fuentes, regenera ambos entregables y commitea si hubo cambios.

Alternativa local con cron (Linux/Mac):

```cron
0 7 * * 1-5  cd /ruta/pipeline && python enrich.py --min 3 --limite 40 && python build.py
```

En Windows: Programador de tareas, misma línea.

## Cómo funciona el enriquecimiento multi-fuente

`enrich.py` toma el titular, extrae sus términos más distintivos, consulta el
**RSS de Google News** (gratis, sin API key) y acepta los resultados cuyo
titular se parece lo suficiente al original.

La perilla importante es `UMBRAL_SIMILITUD` en `config.py` (por defecto `0.42`):

- **Muy bajo** → mete noticias distintas del mismo tema como si fueran la misma.
- **Muy alto** → no encuentra nada, porque cada medio titula diferente.

Ajustalo mirando el log de las primeras corridas. `--dry-run` muestra qué
agregaría sin escribir nada, y el log imprime el puntaje de cada candidato:

```
[3/40] Cartera de créditos superó los US$4.000 millones...
    q: interanual crecimiento creditos millones cartera real
    + [0.61] Finanzas Digital: Cartera de crédito del sistema bancario superó...
    + [0.47] Descifrado: Créditos bancarios crecieron 59,38% real en...
```

Las fuentes se ordenan por jerarquía editorial (`DOMINIOS_PREFERIDOS`): primero
primarias y oficiales (BCV, OFAC, FinCEN, BVC, OPEC), después agencias
(Reuters, Bloomberg, FT), después nacionales. Se deduplica por dominio, así que
nunca vas a tener dos enlaces del mismo medio en una noticia.

`DOMINIOS_EXCLUIDOS` bloquea agregadores y scrapers que republican sin
atribución.

## Limitaciones que conviene saber

- **Google News puede aplicar rate limiting.** Si de golpe todo devuelve vacío,
  esperá unos minutos. De ahí la pausa de 1,6 s y la opción `--limite`.
- **Los feeds RSS se rompen.** Los medios cambian de CMS sin avisar.
  `ingest.py` reporta los que fallan al final de cada corrida; corregí la URL
  en `config.py`. Ninguna de las URLs de `FEEDS` fue verificada en vivo:
  validalas en la primera corrida.
- **El enriquecimiento no lee el artículo, compara titulares.** Puede colar un
  falso positivo. Para noticias que van a un informe institucional, revisá el
  enlace antes de citarlo.
- **`plantilla.html` es el molde.** Todo lo que no sea el array `NOTICIAS`
  (indicadores, gráficos, tabs, toggle ES/EN) vive ahí y `build.py` no lo toca.
  Cuando cambien los KPI o las series, se edita la plantilla.
- **No editar `news.json` a mano** mientras corre el pipeline: `guardar_noticias`
  reordena y deduplica al escribir.
- **La deduplicación es por URL, no por dominio.** 99 de las 315 noticias tienen
  varios enlaces del mismo portal apuntando a artículos distintos (la fuente
  principal más notas de contexto). Deduplicar por dominio destruía 157 de esos
  enlaces. `enrich.py` sí evita agregar un segundo artículo del mismo medio,
  porque ahí el objetivo es diversidad editorial.
- **`enrich.py` compara titulares en el mismo idioma.** Un titular en inglés
  puntúa bajo contra uno en español y queda descartado aunque sea la misma
  noticia. Para agregar fuentes anglosajonas conviene hacerlo a mano.
- **El `.xlsx` cambia de bytes en cada corrida** (openpyxl escribe timestamps
  nuevos en el ZIP). Por eso el workflow decide si commitear mirando
  **`news.json`**, no las salidas: si mirara el Excel, commitearía todos los
  días sin motivo.

## Estructura de un item en news.json

```json
{
 "cat": "oil",
 "date": "12 ago 2026",
 "es": {"title": "...", "preview": "...", "body": "..."},
 "en": {"title": "..."},
 "sectors": ["Petróleo", "Producción"],
 "sources": [{"text": "Banca y Negocios", "url": "https://..."}]
}
```

`cat` debe ser una de: `oil`, `fin`, `mac`, `pol`, `jur`, `inv`, `mkt`, `min`
(son las que usan los filtros del dashboard).

La taxonomía granular del Excel (21 categorías) se deriva automáticamente en
`build.py` a partir de las reglas de `config.py` — no se guarda en el JSON, así
que podés reclasificar todo el histórico cambiando las reglas y corriendo
`build.py` otra vez.

## Verificación

`build.py` aborta si el HTML generado no tiene la misma cantidad de noticias que
el JSON. Además conviene validar la sintaxis del JavaScript tras cambios
grandes:

```bash
python -c "import re;h=open('salida/venezuela_dashboard.html').read();\
open('/tmp/c.js','w').write('\n'.join(re.findall(r'<script>(.*?)</script>',h,re.S)))"
node --check /tmp/c.js
```

Probado sobre las 315 noticias actuales: los 315 cuerpos sobreviven el ciclo
completo idénticos, con acentos, comillas angulares y apóstrofos intactos.
