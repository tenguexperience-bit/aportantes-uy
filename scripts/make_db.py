# Genera la base SQLite para Datasette a partir de data.json (salida de build.py).
# Uso: python scripts/make_db.py data.json site/aportantes.db
import json, re, sqlite3, sys, os, unicodedata

data_path, db_path = sys.argv[1:3]
d = json.load(open(data_path))

# Cédulas: se ocultan antes de guardar cualquier texto.
CI = re.compile(r'(C\.?\s?I\.?\s*[:.]?\s*)?\b\d{1}\.?\d{3}\.?\d{3}\s?[-/]?\s?\d\b', re.I)
COMPANY = re.compile(r'\b(s\.?\s?a\.?|s\.?\s?r\.?\s?l\.?|ltda\.?|sociedad an[oó]nima|cooperativa)(\s|$|[,.)])', re.I)
INTERNAL = re.compile(r'cesi[oó]n|transferencia|traspaso|saldo inicial|adelanto|pr[eé]stamo|cr[eé]dito (del|de la)|diferencia de cambio|intereses', re.I)

# Simplificación fonética del español. La misma lista de reemplazos se aplica en SQL
# al texto que escribe quien busca (ver sql_simplify), así que el orden importa.
ACCENTS = [("á", "a"), ("é", "e"), ("í", "i"), ("ó", "o"), ("ú", "u"), ("ü", "u"), ("à", "a"), ("è", "e"), ("ì", "i"), ("ò", "o"), ("ù", "u"),
           ("Á", "a"), ("É", "e"), ("Í", "i"), ("Ó", "o"), ("Ú", "u"), ("Ü", "u"), ("Ñ", "ñ")]
RULES = ACCENTS + [
    ("ch", "#"), ("h", ""), ("#", "ch"),
    ("ll", "y"), ("v", "b"), ("w", "u"), ("z", "s"),
    ("ce", "se"), ("ci", "si"), ("ge", "je"), ("gi", "ji"),
    ("qu", "k"), ("ca", "ka"), ("co", "ko"), ("cu", "ku"), ("x", "ks"),
    ("bb", "b"), ("ss", "s"), ("rr", "r"), ("nn", "n"), ("tt", "t"), ("ll", "y"), ("cc", "ks"),
    (".", ""), (",", " "), ("  ", " "),
]

def simplify(s):
    s = (s or "").lower()
    for a, b in RULES:
        s = s.replace(a, b)
    return s

def sql_simplify(expr):
    for a, b in RULES:
        expr = "replace(%s, '%s', '%s')" % (expr, a.replace("'", "''"), b.replace("'", "''"))
    return expr

def mask(s):
    return CI.sub("CI ***", s or "")

if os.path.exists(db_path):
    os.remove(db_path)
db = sqlite3.connect(db_path)
db.executescript("""
CREATE TABLE rendiciones (
  id INTEGER PRIMARY KEY, eleccion INTEGER, cargo TEXT, partido TEXT, hoja TEXT, departamento TEXT,
  candidatos TEXT, total_ingresos REAL, total_egresos REAL, planilla TEXT);
CREATE TABLE aportes (
  id INTEGER PRIMARY KEY, fecha TEXT, aportante TEXT, detalle TEXT, tipo TEXT, monto REAL,
  eleccion INTEGER, cargo TEXT, partido TEXT, hoja TEXT, departamento TEXT, candidatos TEXT,
  es_empresa INTEGER, es_movimiento_interno INTEGER, planilla TEXT,
  rendicion_id INTEGER REFERENCES rendiciones(id), texto_simplificado TEXT);
""")
for i, l in enumerate(d["lists"]):
    y, cargo, partido, hoja, depto, cand, url, ting, tegr = l
    db.execute("INSERT INTO rendiciones VALUES (?,?,?,?,?,?,?,?,?,?)",
               (i + 1, y, cargo, partido, hoja or None, depto or None, cand or None, ting, tegr, url))
for li, fecha, tipo, org, desc, monto in d["rows"]:
    y, cargo, partido, hoja, depto, cand, url, _, _ = d["lists"][li]
    org, desc = mask(org), mask(desc)
    if not org and tipo == "Donaciones anónimas":
        org = "Anónimo"
    if desc == org:
        desc = ""
    db.execute("""INSERT INTO aportes (fecha, aportante, detalle, tipo, monto, eleccion, cargo, partido, hoja, departamento,
                  candidatos, es_empresa, es_movimiento_interno, planilla, rendicion_id, texto_simplificado)
                  VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
               (fecha or None, org or None, desc or None, tipo, monto, y, cargo, partido, hoja or None, depto or None, cand or None,
                int(bool(COMPANY.search(org + " " + desc))), int(bool(INTERNAL.search(desc + " " + org))), url, li + 1,
                " " + simplify(" ".join([org, desc, cand, partido, "hoja " + hoja if hoja else ""])) + " "))

# Búsqueda de texto completo para el cuadro de búsqueda estándar de Datasette.
db.executescript("""
CREATE VIRTUAL TABLE aportes_fts USING fts5(aportante, detalle, candidatos, partido, content='aportes', content_rowid='id',
  tokenize='unicode61 remove_diacritics 2');
INSERT INTO aportes_fts(rowid, aportante, detalle, candidatos, partido) SELECT id, aportante, detalle, candidatos, partido FROM aportes;
CREATE INDEX idx_aportes_monto ON aportes(monto);
CREATE INDEX idx_aportes_partido ON aportes(partido);
""")
db.commit()
db.execute("VACUUM")
print("aportes", db.execute("select count(*) from aportes").fetchone()[0],
      "rendiciones", db.execute("select count(*) from rendiciones").fetchone()[0],
      "cedulas visibles", db.execute(r"select count(*) from aportes where aportante glob '*[0-9].[0-9][0-9][0-9].[0-9][0-9][0-9]-[0-9]*' or detalle glob '*[0-9].[0-9][0-9][0-9].[0-9][0-9][0-9]-[0-9]*'").fetchone()[0])

# Expresión SQL que usan las consultas guardadas para simplificar lo que escribe quien busca.
open(os.path.join(os.path.dirname(db_path), "simplify.sql"), "w").write(sql_simplify("lower(:texto)"))
