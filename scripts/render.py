# Enmascara cédulas en los textos e inserta los datos en la plantilla HTML.
import json, re, sys
data_path, tpl_path, out_path = sys.argv[1:4]
d = json.load(open(data_path))
CI = re.compile(r'(C\.?\s?I\.?\s*[:.]?\s*)?\b\d{1}\.?\d{3}\.?\d{3}\s?[-/]?\s?\d\b', re.I)
n = 0
for r in d["rows"]:
    for k in (3, 4):
        new = CI.sub("CI ***", r[k])
        if new != r[k]: n += 1; r[k] = new
blob = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
open(out_path, "w").write(open(tpl_path).read().replace("__DATA__", blob))
print("masked", n)
