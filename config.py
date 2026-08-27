# -*- coding: utf-8 -*-
"""
Configuración compartida del pipeline de inteligencia Venezuela — Grupo Solfín.
Editar aquí para agregar portales, feeds o categorías sin tocar los scripts.
"""

# ---------------------------------------------------------------- PORTALES
# Feeds RSS de los portales que se monitorean para INGESTA de noticias nuevas.
# Verificar cada URL una vez antes de confiar en ella: los medios cambian
# de CMS y rompen sus feeds sin avisar. ingest.py reporta los que fallan.
FEEDS = {
    "Banca y Negocios":   "https://www.bancaynegocios.com/feed/",
    "Finanzas Digital":   "https://finanzasdigital.com/feed/",
    "Descifrado":         "https://www.descifrado.com/feed/",
    "El Nacional":        "https://www.elnacional.com/feed/",
    "TalCual":            "https://talcualdigital.com/feed/",
    "Efecto Cocuyo":      "https://efectococuyo.com/feed/",
    "Bloomberg Línea":    "https://www.bloomberglinea.com/arc/outboundfeeds/rss/?outputType=xml",
    "El Estímulo":        "https://elestimulo.com/feed/",
    "Correo del Caroní":  "https://correodelcaroni.com/feed/",
    "Venezuelanalysis":   "https://venezuelanalysis.com/rss",
    "Petroguía":          "http://www.petroguia.com/rss.xml",
}

# Dominios preferidos al buscar fuentes adicionales de una misma noticia.
# El orden importa: enrich.py prioriza los primeros como "fuente de mayor peso".
DOMINIOS_PREFERIDOS = [
    # Primarias / oficiales
    "bcv.org.ve", "ofac.treasury.gov", "fincen.gov", "sudeban.gob.ve",
    "sunaval.gob.ve", "bolsadecaracas.com", "opec.org", "eia.gov",
    "imf.org", "tsj.gob.ve", "businesswire.com", "prnewswire.com",
    # Agencias e internacionales
    "reuters.com", "bloomberg.com", "bloomberglinea.com", "ft.com",
    "apnews.com", "efe.com", "semafor.com", "axios.com", "fortune.com",
    # Nacionales
    "bancaynegocios.com", "finanzasdigital.com", "descifrado.com",
    "elnacional.com", "talcualdigital.com", "efectococuyo.com",
    "elestimulo.com", "correodelcaroni.com", "banca ynegocios.com",
    "venezuelanalysis.com", "lapatilla.com", "eluniversal.com",
    "acn.com.ve", "primicia.com.ve", "confirmado.com.ve", "curadas.com",
]

# Dominios a excluir siempre: agregadores de baja calidad, scrapers,
# y sitios que republican sin atribución.
DOMINIOS_EXCLUIDOS = [
    "entornointeligente.com", "noticiasaldiayalahora.co",
    "msn.com", "news.google.com", "facebook.com", "twitter.com",
    "x.com", "youtube.com", "reddit.com",
]

# ---------------------------------------------------------------- TAXONOMÍA
# Categorías del dashboard HTML (las que usan los filtros de la interfaz).
CATS_HTML = {
    "oil": "Petróleo", "fin": "Financiero", "mac": "Macroeconomía",
    "pol": "Político", "jur": "Jurídico/Regulatorio", "inv": "Inversión",
    "mkt": "Mercado de capitales", "min": "Minería",
}

# Taxonomía granular para el Excel. Se evalúa EN ORDEN: la primera que
# coincide es la categoría principal; las siguientes van como secundarias.
# Prefijo '#' = coincidencia por palabra completa (evita que "gas" capture
# "gasto" o "mw" capture cualquier cosa).
RULES = [
 ('Licencias y sanciones', ['ofac','licencia general','licencias generales','#gl 5','fincen',
    'sanciona','sancion','estatuto de roma','#bis','licencia de eeuu','licencia que autoriza',
    'obtiene licencia','desbloquear fondos','aprueba licencia','flexibiliza']),
 ('Deuda soberana y activos externos', ['#bono','#bonos','citgo','pdvsa 2020','reestructurac',
    'riesgo pais','#oro','banco de inglaterra','auditoras','deuda de venezuela','venezuela 2.0',
    '47 toneladas','#deg','pendiente de cobro','plan maestro']),
 ('Commodities y agro', ['#cafe','arroz','azucar','canicultor','fevearroz','fesoca','zafra',
    'cosecha','camaron','agricola','#agro','fertilizante','pequiven','supernino','super nino',
    '#el nino','sequia','agronomo','cacao','#oit','alimentos','proteinas']),
 ('Gas', ['#gas','#gasifero','loran','dragon','manatee','metano','#lng','atlantic']),
 ('Petróleo — Contratos e inversión', ['hunt oil','#slb','crossover','formentera','junin','ongc',
    '916','faja petrolifera','roraima','batista','fluxus','marco legal','firman acuerdos',
    'alianzas estrategicas','30 acuerdos','vitol','maurel','vendio su participacion','chevron',
    'reparto de produccion','houston','halliburton','hidrocarburos','shell','areas disponibles']),
 ('Petróleo — Exportaciones y comercialización', ['exportacion','exportaciones','segundo proveedor',
    'compra directa','buques cisterna','clientes petroleros','ventas venezolanas',
    'importaciones de petroleo','refinerias de eeuu','refinerias globales','corea del sur',
    'secreto','cargamento']),
 ('Petróleo — Refinación y combustibles', ['refinacion','refineria','gasolina','combustible']),
 ('Petróleo — Producción y precios', ['produccion de crudo','produccion petrolera','momr','opep',
    'merey','precio promedio del petroleo','productores de petroleo','#bcg','industria petrolera',
    '#1.200','barriles']),
 ('Energía eléctrica', ['electric','megavatio','#mw','termoelectric','termocarabobo','tocoma',
    'impsa','guri','transmision','apagon','demanda energetica','#insa','general electric',
    'corpoelec','#sen','generacion']),
 ('Telecomunicaciones', ['cantv','conatel','spacex','starlink','cable submarino','fenix',
    'telecomunicacion','internet','liberty','movilnet']),
 ('Cambiario y monetario', ['tipo de cambio','dolar oficial','brecha cambiaria','mercado cambiario',
    'divisas','tarifario','dolarizacion','hanke','unificacion cambiaria','#smc','bcv vendio',
    'tamara herrera','oferta de divisas','coordinacion tecnica']),
 ('Bancario y crédito', ['cartera de credito','depositos bancarios','#banca','#banco','#bancos',
    'corresponsalia','#credito','#creditos','hipotecari','bancamiga','cashea','fintech','#bdt',
    'liquidez','multiplicador','solvencia','microcredito']),
 ('Mercado de capitales', ['#bvc','bolsa de valores','#ibc','sunaval','#avex','titularizacion',
    'bursatil','#emision','acciones']),
 ('Seguros', ['asegurador','primas','sudeaseg','#seguros']),
 ('Macroeconomía y proyecciones', ['#pib','inflacion','#inpc','cedice','crecimiento','#pnud',
    'proyecta','proyeccion','no petrolero','produccion industrial','farmaceutica','consumo',
    'comercio entre venezuela','aristimuno','#fmi','balanza']),
 ('Minería', ['mineria','hierro','mineral','#ferreo']),
 ('Judicial y DDHH', ['#tsj','afiuni','magistrado','judicial','excarcelacion','presos politicos',
    'tribunal','saren','arrendamiento','jurisdiccion','#ddhh','desaparecidos']),
 ('Reconstrucción y emergencia', ['terremoto','sismo','damnificado','vivienda','reconstruccion',
    'venezuela renace','ayuda humanitaria','doblete']),
 ('Logística y transporte', ['#puerto','aeropuerto','avavit','logistica','#carga',
    'nacionalizacion de mercancias','maiquetia','aeronautico','turismo']),
 ('Consumo, comercio y empresas', ['nutresa','tio rico','grupo exito','general motors','#retail',
    '#empresas','#grupo','multinacional','venamcham']),
 ('Fiscal y tributario', ['seniat','tributari','#rif','impuesto','facturacion','#fiscal','arancel']),
 ('Político e institucional', ['dialogo','oposicion','delcy','jorge rodriguez','trump','ministro',
    'canciller','gabinete','militar','plasencia','maniglia','encargado de negocios',
    'congreso de eeuu','claver-carone','ballard','israel','#cpi','elecciones','interceptados',
    'figuera']),
]

# Respaldo cuando ninguna regla coincide: se usa la categoría del HTML.
FALLBACK = {
    'oil':'Petróleo — Producción y precios', 'fin':'Bancario y crédito',
    'mac':'Macroeconomía y proyecciones', 'pol':'Político e institucional',
    'jur':'Judicial y DDHH', 'inv':'Energía eléctrica',
    'mkt':'Mercado de capitales', 'min':'Minería',
}

# ---------------------------------------------------------------- IDENTIDAD
COLOR_NAVY = "1F2A44"
COLOR_GOLD = "C9A227"
COLOR_GREY = "E1E0D9"
FUENTE = "Arial"

# Umbral de similitud (0-1) para aceptar que dos titulares son la MISMA
# noticia al buscar fuentes adicionales. La métrica (ver enrich.similar) ya
# exige compartir una cifra o un nombre propio como condición previa, así que
# este umbral solo discrimina ENTRE candidatos que ya pasaron ese filtro —
# por eso puede ser más bajo que un umbral de similitud "a secas". Calibrado
# contra 5 casos reales de la misma noticia en dos medios (0.34 a 0.76) y 4
# casos de noticias distintas (0.15 a 0.30): 0.32 separa ambos grupos con
# margen. Subirlo reduce falsos positivos; bajarlo de más empieza a mezclar
# los negativos calibrados.
UMBRAL_SIMILITUD = 0.32

# Máximo de fuentes por noticia (evita listas interminables). Contempla que
# un portal puede aportar más de un artículo: la fuente principal más notas de
# contexto o antecedentes. La deduplicación es por URL, no por dominio.
MAX_FUENTES = 8
