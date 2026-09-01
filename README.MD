# Extracción de metadatos y sinopsis: Categoría Bélico (Lectulandia)

## Integrantes del grupo

- Manuel Lazarte
- Emmanuel Mendoza
- Álvaro Toledo
-
-

## Categoría seleccionada

- **Categoría:** Bélico
- **URL:** https://ww3.lectulandia.com/genero/belico/

## Cantidad de libros extraídos

150 libros (dentro del rango de 50–150 definido para la implementación).

## Instalación

```bash
# 1. Crear entorno virtual (dentro de la carpeta del repo)
python -m venv .venv
.venv\Scripts\activate      # Windows
source .venv/bin/activate   # macOS/Linux

# 2. Instalar dependencias
pip install -r requirements.txt

# 3. Instalar el navegador Chromium para Playwright
#    (paso obligatorio y separado de pip install: descarga el binario del navegador)
playwright install chromium
```

## Ejecución

Desde la carpeta `src/`:

```bash
python scraper.py
```

No recibe argumentos por línea de comandos: la categoría, el rango de libros (50–100),
la URL base y el modo headless están definidos como constantes al inicio del archivo
(`BASE_URL`, `CATEGORIA`, `MIN_LIBROS`, `MAX_LIBROS`).

El script:

- Recorre el listado de la categoría de forma secuencial. La página 1 usa la URL base
  sin sufijo; a partir de la página 2 se agrega `/page/n/` (comportamiento propio de
  WordPress, que es lo que corre el sitio).
- Extrae de cada tarjeta del listado (`article.card`) la URL de la ficha individual y
  la URL de portada.
- Visita cada ficha individual con Playwright y extrae con BeautifulSoup: título,
  autores, géneros, serie y la sinopsis completa (distinta de la sinopsis truncada que
  aparece en el listado de categoría).
- Limpia espacios y saltos de línea innecesarios en todos los campos de texto.
- Evita registros duplicados por `url_libro`, tanto dentro de la misma corrida como
  entre corridas distintas (si `data/libros.csv` ya existe, el script retoma desde ahí
  sin reprocesar libros ya guardados).
- Guarda cada libro de forma incremental (fila por fila) en `data/libros.csv`, así que
  si el proceso se corta a mitad de camino no se pierde lo ya extraído.
- Incorpora una pausa aleatoria entre requests (1.5–3 s entre fichas individuales,
  1–2 s entre páginas de categoría) para no sobrecargar el sitio.
- Controla errores por libro individualmente (try/except) sin detener la ejecución
  completa si una ficha puntual falla.


## Estructura del repositorio

```
README.md
src/
    scraper.py
data/
    libros.csv
docs/
    diseno_extraccion.md
requirements.txt
```

## Principales dificultades encontradas

- **Playwright no incluye el navegador al instalarlo con pip.** `pip install playwright`
  solo instala la librería; hace falta correr además `playwright install chromium`
  para descargar el binario del navegador.
- **Las URLs de los libros en el listado de categoría vienen como rutas relativas**
  (ej. `/book/bombardero/`) y no como URLs completas, por lo que Playwright no podía
  navegar directamente a ellas. Se resolvió con `urllib.parse.urljoin`, combinando cada
  ruta relativa con el dominio base antes de visitarla.
- **La ruta de salida `data/libros.csv` se resolvía respecto al directorio desde el que
  se ejecutaba el script**, y no respecto a la ubicación del archivo `scraper.py`, lo
  que generaba la carpeta `data/` dentro de `src/` en vez de al lado. Se corrigió
  anclando la ruta a `os.path.dirname(os.path.abspath(__file__))`.
- **La sinopsis completa de la ficha individual usa `<br>` para separar párrafos**, a
  diferencia de la sinopsis truncada del listado de categoría. Fue necesario reemplazar
  los `<br>` por saltos de línea antes de extraer el texto para no perder la separación
  entre párrafos.
