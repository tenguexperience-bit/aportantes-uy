# Aportantes Electorales Uruguay

Buscador de ingresos privados declarados ante la Corte Electoral en las rendiciones de cuentas
de las Elecciones Nacionales 2019 y 2024 (Ley 18.485). Se publica con Datasette Lite en GitHub Pages:
la carpeta `docs/` es todo lo que se sirve.

## Regenerar la base

```bash
python scripts/make_db.py data.json docs/aportantes.db      # crea la base y docs/simplify.sql
python scripts/make_metadata.py docs/simplify.sql docs/metadata.json
```

`data.json` sale de `scripts/build.py` (a partir de las planillas descargadas con `scripts/parse_rendiciones.py`)
y **no se publica** porque contiene cédulas sin enmascarar. `make_db.py` las oculta.

## Probar localmente

```bash
pip install datasette
datasette docs/aportantes.db -m docs/metadata.json
```
