# Genera metadata.json para Datasette (títulos, filtros y consultas guardadas).
# Uso: python scripts/make_metadata.py docs/simplify.sql docs/metadata.json
import json, sys

simplify_sql = open(sys.argv[1]).read()
COLS = "fecha, aportante, detalle, tipo, monto, eleccion, cargo, partido, hoja, departamento, candidatos, planilla"
MATCH = "texto_simplificado like '%' || " + simplify_sql + " || '%'"

meta = {
    "title": "Aportantes Electorales Uruguay",
    "description_html": (
        "<p>Ingresos privados declarados ante la Corte Electoral en las rendiciones de cuentas de las "
        "Elecciones Nacionales 2019 y 2024 (presidenciales, Senado y Diputados), según la Ley 18.485.</p>"
        "<p><strong>Para buscar un nombre tolerando errores de tipeo</strong> (v/b, s/z/c, tildes, ll/y), usá la consulta "
        "<a href=\"aportantes/buscar\">Buscar aportes</a> o <a href=\"aportantes/totales_por_aportante\">Totales por aportante</a>.</p>"
        "<p>Los textos son los que cargó cada campaña, sin corregir. Las cédulas se ocultaron. Montos en pesos uruguayos. "
        "Cada fila enlaza a la planilla original publicada por la Corte.</p>"
    ),
    "source": "Corte Electoral del Uruguay — rendiciones de cuentas",
    "source_url": "https://www.gub.uy/corte-electoral/comunicacion/publicaciones/rendiciones-cuenta-elecciones-nacionales-2024",
    "databases": {
        "aportantes": {
            "tables": {
                "aportes": {
                    "title": "Aportes",
                    "description": "Un registro por ingreso privado declarado. Excluye la contribución estatal por voto válido.",
                    "sort_desc": "monto",
                    "facets": ["eleccion", "cargo", "partido", "departamento", "tipo", "es_empresa", "es_movimiento_interno"],
                    "fts_table": "aportes_fts",
                    "fts_pk": "id",
                    "label_column": "aportante",
                    "columns": {
                        "aportante": "Nombre en la columna Origen de la planilla, cuando la campaña lo informó.",
                        "detalle": "Descripción cargada por la campaña (suele incluir el nombre del donante o el recibo).",
                        "tipo": "Tipo de ingreso, normalizado a partir del concepto declarado.",
                        "monto": "Pesos uruguayos.",
                        "es_empresa": "1 si el texto menciona S.A., S.R.L., Ltda. o cooperativa.",
                        "es_movimiento_interno": "1 si parece una cesión, transferencia, saldo inicial o préstamo entre listas o con el partido.",
                        "planilla": "Planilla original publicada por la Corte Electoral.",
                        "texto_simplificado": "Uso interno: texto normalizado para la búsqueda tolerante.",
                    },
                },
                "rendiciones": {
                    "title": "Rendiciones",
                    "description": "Una rendición de cuentas por lista o fórmula, con sus totales declarados.",
                    "sort_desc": "total_ingresos",
                    "facets": ["eleccion", "cargo", "partido", "departamento"],
                },
                "aportes_fts": {"hidden": True},
                "reglas_busqueda": {"hidden": True},
            },
            "queries": {
                "buscar": {
                    "title": "Buscar aportes (tolera errores de tipeo)", "hide_sql": True,
                    "description": "Escribí un nombre, empresa, candidato, partido o «hoja 609». Ignora tildes y confusiones v/b, s/z/c, ll/y, h.",
                    "sql": f"select {COLS} from aportes where {MATCH} order by monto desc",
                },
                "totales_por_aportante": {
                    "title": "Totales por aportante", "hide_sql": True,
                    "description": "Agrupa los aportes que coinciden con el texto por nombre declarado (sin unificar variantes de escritura).",
                    "sql": (
                        "select coalesce(aportante, detalle) as aportante_declarado, count(*) as aportes, sum(monto) as total, "
                        "group_concat(distinct partido) as partidos, group_concat(distinct eleccion) as elecciones "
                        f"from aportes where {MATCH} group by lower(coalesce(aportante, detalle)) order by total desc"
                    ),
                },
                "totales_por_partido": {
                    "title": "Totales por partido y elección", "hide_sql": True,
                    "description": "Suma de aportes privados declarados, sin cesiones ni transferencias internas.",
                    "sql": (
                        "select eleccion, partido, count(*) as aportes, sum(monto) as total from aportes "
                        "where es_movimiento_interno = 0 group by eleccion, partido order by eleccion desc, total desc"
                    ),
                },
            },
        }
    },
}
json.dump(meta, open(sys.argv[2], "w"), ensure_ascii=False, indent=2)
print("ok")
