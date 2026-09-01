# Extracción de metadatos y sinopsis — Categoría Bélico (Lectulandia)

## Integrantes del grupo

_Completar con los nombres del grupo._

## Categoría seleccionada

- **Categoría:** Bélico
- **URL:** https://ww3.lectulandia.co/genero/belico/

## Cantidad de libros extraídos

_Completar luego de correr el scraper (objetivo: 100–200 libros)._

## Instalación

```bash
# 1. Crear entorno virtual
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Instalar el navegador Chromium para Playwright
playwright install chromium
```

## Ejecución

Desde la carpeta `src/`:

```bash
# Ejecución estándar (headless, objetivo 150 libros)
python scraper.py --target 150

# Ver el navegador mientras corre (para debug)
python scraper.py --target 150 --show-browser

# Ajustar pausa entre requests (segundos) y ruta de salida
python scraper.py --target 150 --delay 2 --output ../data/libros.csv
```

El script:

- Recorre el listado de la categoría de forma secuencial (`/page/2/`, `/page/3/`, ...).
- Extrae la URL de cada ficha individual.
- Visita cada ficha y extrae título, autores, géneros, serie, sinopsis y portada.
- Va guardando cada libro de forma incremental en `data/libros.csv` (append), así que si se corta a mitad de camino se puede volver a correr sin perder lo ya extraído ni duplicar registros.
- Al finalizar, imprime un resumen con duplicados y registros sin sinopsis como control mínimo.

## Estructura del repositorio

```
README.md
src/
    scraper.py
data/
    libros.csv
docs/
    diseno_extraccion.md
```

## Principales dificultades encontradas

_Completar durante/después de correr el scraper contra el sitio real (selectores que
requieran ajuste, paginación, timeouts, bloqueos, etc.)._

## Nota importante

Este script fue desarrollado en base al diseño aprobado en `docs/diseno_extraccion.md`,
pero **no pudo ejecutarse contra el sitio real** en este entorno porque el acceso de red
está restringido a un listado cerrado de dominios que no incluye `lectulandia.co`. Antes
de la entrega final es necesario:

1. Correrlo en un entorno con acceso a internet.
2. Verificar visualmente (con `--show-browser` o inspeccionando el HTML real) que los
     selectores de `docs/diseno_extraccion.md` siguen vigentes, ya que el sitio puede
     haber cambiado su estructura desde que se diseñó la extracción.
3. Ajustar selectores si algún campo sale vacío.