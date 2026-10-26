import json, re, sys, os, datetime, unicodedata, collections
S = sys.argv[1]
BASE = {2019: "https://aplicaciones.corteelectoral.gub.uy/Elecciones/RendicionDeCuentas2019/Resources/Rendiciones/",
        2024: "https://aplicaciones.corteelectoral.gub.uy/Elecciones/RendicionDeCuentas2024/Resources/Rendiciones/"}
files = {2019: {re.sub(r'\..*', '', f): f for f in os.listdir(f"{S}/raw/n2019")},
         2024: {re.sub(r'\..*', '', f): f for f in os.listdir(f"{S}/raw/n2024")}}

def strip(s):
    return ''.join(ch for ch in unicodedata.normalize('NFD', s) if unicodedata.category(ch) != 'Mn').lower()

PARTIES = [("frente amplio", "Frente Amplio"), ("nacional", "Partido Nacional"), ("colorado", "Partido Colorado"),
           ("cabildo", "Cabildo Abierto"), ("independiente", "Partido Independiente"), ("asamblea", "Asamblea Popular"),
           ("ecologista", "Partido Ecologista Radical Intransigente"), ("ambientalista", "Partido Constitucional Ambientalista"),
           ("identidad soberana", "Identidad Soberana"), ("avanzar", "Partido Avanzar Republicano"),
           ("cambios necesarios", "Partido por los Cambios Necesarios"), ("digital", "Partido Digital"),
           ("verde animalista", "Partido Verde Animalista"), ("de la gente", "Partido de la Gente"),
           ("trabajadores", "Partido de los Trabajadores"), ("partico nacional", "Partido Nacional")]
def party(p):
    s = strip(p)
    for k, v in PARTIES:
        if k in s: return v
    return p.strip() or "(sin dato)"

DEPTOS = ["Artigas", "Canelones", "Cerro Largo", "Colonia", "Durazno", "Flores", "Florida", "Lavalleja", "Maldonado",
          "Montevideo", "Paysandú", "Río Negro", "Rivera", "Rocha", "Salto", "San José", "Soriano", "Tacuarembó", "Treinta y Tres"]
DMAP = {strip(d).replace(" ", ""): d for d in DEPTOS}
def depto(d):
    k = strip(d).replace(" ", "").replace(".", "")
    return DMAP.get(k, DMAP.get("treintaytres") if k in ("33", "treintaytres") else "")

def cargo(y, fid):
    n = int(fid)
    if y == 2024: return "Presidencia" if n <= 11 else "Senado" if n < 1000 else "Diputados"
    return "Presidencia" if n > 1_000_000 else "Senado" if n < 1000 else "Diputados"

def fecha(f):
    f = f.strip()
    if re.match(r'^\d{4}-\d{2}-\d{2}', f): return f[:10]
    m = re.match(r'^(\d{1,2})[./-](\d{1,2})[./-](\d{2,4})$', f)
    if m:
        d, mo, yy = map(int, m.groups()); yy += 2000 if yy < 100 else 0
        try: return datetime.date(yy, mo, d).isoformat()
        except ValueError: return ""
    if re.match(r'^\d{5}(\.0)?$', f):
        return (datetime.date(1899, 12, 30) + datetime.timedelta(days=int(float(f)))).isoformat()
    return ""

def monto(v):
    v = str(v).strip().replace("$", "").replace(" ", "")
    if not v: return None
    if re.match(r'^-?[\d.]+,\d+$', v): v = v.replace(".", "").replace(",", ".")
    elif re.match(r'^-?\d{1,3}(,\d{3})+(\.\d+)?$', v): v = v.replace(",", "")
    try: return round(float(v), 2)
    except ValueError: return None

PUB = re.compile(r'p[uú]bl|voto v[aá]lido|votos? v[aá]lidos|financiamiento c(ampa)?|contribuci[oó]n por voto|ley 18\.?485|^mef|^brou$|corte electoral', re.I)
PRIV = re.compile(r'^priv', re.I)
def sector(r):
    for k in ("fin", "origen"):
        s = r[k].strip()
        if PRIV.match(s): return "Privado"
        if re.match(r'^p[uúü]bl', s, re.I): return "Público"
    if PUB.search(r["concepto"]) or PUB.search(r["fin"]) or PUB.search(r["origen"]): return "Público"
    return "Privado"

GENERIC = {strip(x) for x in """brou banco aporte aportes privado privada público publico efectivo en efectivo donación donacion donaciones
nominativo persona física persona jurídica persona particular personal personales propio propios fondos propios ahorros ahorro personal
titular candidato aporte candidato ap candidato ap campaña anónimo anonimo anónimas anónimos colaboradores especie estado votos corte mef
dirigente sector diputado senado lema origen cash abitab redpagos bancario prestamo préstamo campaña mvd colaboración personal
cuenta bancaria personal eectivo aporte estado estatal""".replace("\n", " ").split("  ")} 
GENERIC |= {strip(x) for x in ["brou","banco","aporte","privado","privada","público","publico","efectivo","en efectivo","donación","donacion",
 "donaciones","nominativo","persona física","persona jurídica","persona","particular","personal","personales","propio","propios",
 "fondos propios","ahorros","ahorro personal","titular","candidato","aporte candidato","ap candidato","ap campaña","anónimo","anonimo",
 "anónimas","anónimos","colaboradores","especie","estado","votos","corte","mef","dirigente","sector","diputado","senado","lema","origen",
 "cash","abitab","redpagos","bancario","prestamo","préstamo","campaña","mvd","colaboración personal","cuenta bancaria personal",
 "eectivo","aporte estado","estatal","aportes personales  de mi conyuge","donacion","efectivo","eectivo","bancario","finanzas central"]}

def concepto(r):
    for k in ("concepto", "fin"):
        s = r[k].strip()
        if s and not PRIV.match(s) and not re.match(r'^p[uúü]bl', s, re.I): return s
    return ""

CANON = [("nominativ", "Donaciones nominativas"), ("an[oó]nim", "Donaciones anónimas"), ("candidat", "Donaciones de candidatos"),
         ("partido", "Donaciones del partido"), ("especie", "Donaciones en especie"), ("evento|cena", "Eventos"), ("rifa", "Rifas"),
         ("colecta", "Colectas"), ("exterior", "Aportes del exterior")]
def canon(c):
    s = strip(c)
    for pat, v in CANON:
        if re.search(pat, s): return v
    return "Otros"

out, lists, stats = [], [], collections.Counter()
for y in (2019, 2024):
    d = json.load(open(f"{S}/p{y}.json"))
    for fid, v in d.items():
        if "error" in v: continue
        m = v["meta"]
        cand = " / ".join(x for x in (m.get("titular1", ""), m.get("titular2", "")) if x) or m.get("candidato", "")
        li = len(lists)
        lists.append([y, cargo(y, fid), party(m.get("partido", "")), m.get("hoja", ""), depto(m.get("departamento", "")), cand,
                      BASE[y] + files[y][fid], monto(m.get("total_ingresos", "")), monto(m.get("total_egresos", ""))])
        for r in v["ingresos"]:
            if sector(r) == "Público": stats["pub"] += 1; continue
            imp = monto(r["importe"])
            if not imp: stats["zero"] += 1; continue
            org = r["origen"].strip()
            if strip(org) in GENERIC or PRIV.match(org) or re.match(r'^p[uú]bl', org, re.I): org = ""
            desc = re.sub(r'\s+', ' ', r["desc"]).strip()
            con = concepto(r)
            out.append([li, fecha(r["fecha"]), canon(con), org, desc, imp])
            stats["priv"] += 1
json.dump({"lists": lists, "rows": out, "generated": datetime.date.today().isoformat()},
          open(f"{S}/data.json", "w"), ensure_ascii=False, separators=(",", ":"))
print(stats, len(lists), os.path.getsize(f"{S}/data.json"))
c = collections.Counter(r[2] for r in out); print(c)
