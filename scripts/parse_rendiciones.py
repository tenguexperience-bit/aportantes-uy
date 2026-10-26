import sys, os, json, re, datetime, warnings, openpyxl
warnings.filterwarnings("ignore")
src, out = sys.argv[1], sys.argv[2]
def norm(v):
    if v is None: return ""
    if isinstance(v, datetime.datetime): return v.date().isoformat()
    if isinstance(v, float) and v.is_integer(): return str(int(v))
    return str(v).strip()
import xlrd
def load(path):
    if path.endswith(".xls"):
        wb = xlrd.open_workbook(path)
        def mk(sh):
            def it():
                for i in range(sh.nrows):
                    row = []
                    for c in sh.row(i):
                        v = c.value
                        if c.ctype == xlrd.XL_CELL_DATE:
                            try: v = xlrd.xldate.xldate_as_datetime(v, wb.datemode)
                            except Exception: pass
                        row.append(v)
                    yield row
            return it
        return [(sh.name, mk(sh)) for sh in wb.sheets()]
    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    return [(ws.title, (lambda ws=ws: ws.iter_rows(values_only=True))) for ws in wb.worksheets]
res = {}
for fn in sorted(os.listdir(src), key=lambda x: int(re.sub(r'\D','',x) or 0)):
    fid = re.sub(r'\..*','',fn)
    try:
        sheets = load(os.path.join(src, fn))
    except Exception as e:
        res[fid] = {"error": str(e)}; continue
    meta, rows = {}, []
    for title, it in sheets:
        t = title.lower()
        if t == "datos":
            for r in it():
                vals = [norm(v) for v in r if norm(v)]
                if not vals: continue
                k = vals[0].rstrip(":").lower()
                if k.startswith("partido pol"): meta["partido"] = vals[1] if len(vals)>1 else ""
                elif k.startswith("primer titular"): meta["titular1"] = vals[1] if len(vals)>1 and not vals[1].startswith("Credencial") else ""
                elif k.startswith("segundo titular"): meta["titular2"] = vals[1] if len(vals)>1 and not vals[1].startswith("Credencial") else ""
                elif k.startswith("candidato") and not k.startswith("candidato a"): meta["candidato"] = vals[1] if len(vals)>1 and not vals[1].startswith("Credencial") else ""
                elif k.startswith("candidato a"): meta["cargo"] = vals[1] if len(vals)>1 else ""
                elif k.startswith("nº hoja") or k.startswith("n° hoja") or k.startswith("n°hoja"): meta["hoja"] = vals[1] if len(vals)>1 else ""
                elif k.startswith("departamento"): meta["departamento"] = vals[1] if len(vals)>1 else ""
                elif k == "totales":
                    meta["total_ingresos"] = vals[1] if len(vals)>1 else ""; meta["total_egresos"] = vals[2] if len(vals)>2 else ""
        elif t.startswith("ing"):
            hdr = None
            for r in it():
                cells = [norm(v) for v in r]
                if hdr is None:
                    low = [c.lower().replace("\n"," ") for c in cells]
                    if "id" in low and "fecha" in low and any(c.startswith("importe") for c in low):
                        hdr = {}
                        for i,c in enumerate(low):
                            for key in ("id","fecha","origen","finaciamiento","financiamiento","concepto","descripción","descripcion","importe"):
                                if c.startswith(key) and key not in hdr: hdr[key]=i
                            if c.startswith("tipo"): hdr["tipo"]=i
                    continue
                g = lambda k: cells[hdr[k]] if k in hdr and hdr[k] < len(cells) else ""
                desc = g("descripción") or g("descripcion")
                imp = g("importe")
                if not desc and not imp: continue
                rows.append({"fecha": g("fecha"), "origen": g("origen"),
                             "fin": g("finaciamiento") or g("financiamiento"), "concepto": g("concepto"),
                             "desc": desc, "tipo": g("tipo"), "importe": imp})
    res[fid] = {"meta": meta, "ingresos": rows}
json.dump(res, open(out, "w"), ensure_ascii=False)
print(len(res), sum(len(v.get("ingresos",[])) for v in res.values()), sum(1 for v in res.values() if "error" in v))
