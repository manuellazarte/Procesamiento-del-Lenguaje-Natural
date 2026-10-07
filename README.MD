# Extracción de metadatos y sinopsis: Categoría Bélico (Lectulandia)

## Integrantes del grupo

- Manuel Lazarte
- Emmanuel Mendoza
- Álvaro Toledo
- Romano Maximiliano
- Troanes Federico Nahuel

## Categoría seleccionada

- **Categoría:** Bélico
- **URL:** https://ww3.lectulandia.com/genero/belico/

## Cantidad de libros extraídos

150 libros (dentro del rango de 50–150 definido para la implementación).

## Modelo de datos

| Columna | Tipo | Descripción |
|---|---|---|
| `id_libro` | varchar | Identificador único del libro en el sitio de origen |
| `titulo` | varchar | Título del libro |
| `autores` | lista de varchar | Autor o autores, en orden "Nombre Apellido" |
| `generos` | lista de varchar | Género o géneros del libro |
| `serie` | varchar, nullable | Serie a la que pertenece; vacío si no corresponde |
| `sinopsis` | texto | Sinopsis completa del libro |
| `url_libro` | varchar | Slug final de la URL de la ficha (sin dominio ni ruta completa) |
| `categoria_origen` | varchar | Categoría seleccionada por el grupo (constante: `belico`) |
| `fecha_extraccion` | date (ISO 8601) | Fecha en que se obtuvo el registro |
| `url_portada` | varchar | URL de la imagen de portada |

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

No recibe argumentos por línea de comandos: la categoría, el rango de libros (50–150),
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

---

# TP2: Embeddings y búsqueda semántica

## Contenido

```
queries.json                                       # conjunto de evaluación (14 consultas con sus relevantes)
src/TP2_Lazarte_Mendoza_Toledo_Romano_Troanes.ipynb   # notebook del TP2
docs/informe.md / docs/informe.docx                # informe (máx. 3 páginas)
```

El notebook compara cuatro representaciones de las sinopsis (TF-IDF, Word2Vec propio,
promedio de vectores de SBW y SBERT `distiluse-base-multilingual-cased-v1`), guarda los
vectores en Postgres con `pgvector` (Supabase), busca por similitud en SQL con filtro por
género y evalúa todo con precision@k contra el piso de azar. La parte avanzada elegida es
la **búsqueda híbrida** (full-text de Postgres + vectorial) con *Reciprocal Rank Fusion*.

## Ejecución (Google Colab)

1. Abrir el notebook desde el badge "Open in Colab".
2. En **Secrets** (ícono de llave en la barra lateral) crear `SUPABASE_DB_URL` con la cadena
   de conexión de Supabase (botón **Connect** del proyecto → *Session pooler*, puerto 5432 en
   el host `pooler.supabase.com`) y habilitarle el acceso al notebook. La conexión directa
   (`db.<proyecto>.supabase.co`) es solo IPv6 en el plan gratuito y Colab no tiene IPv6.
   La credencial nunca se escribe en el notebook.
3. Si `queries.json` no está en la rama `main` del repo, subirlo a `/content`.
4. Ejecutar todo (*Runtime → Run all*). La primera vez descarga SBW (~1 GB) y el modelo
   de SBERT; los embeddings quedan guardados en `embeddings/*.npy`.

Para correrlo fuera de Colab: `pip install -r requirements.txt` y definir la variable de
entorno `SUPABASE_DB_URL`.

**Nota:** los proyectos gratuitos de Supabase se pausan tras 7 días sin actividad; se
reactivan desde el panel.

## Principales dificultades encontradas

- **SBW tiene vocabulario con acentos.** Con el mismo preprocesamiento que TF-IDF
  (sin acentos), `ejército` se buscaba como `ejercito` y caía en una variante mal escrita.
  Se agregó un preprocesamiento para SBW que conserva los acentos.
- **SBERT trunca en silencio.** El modelo tiene un límite de 128 tokens y no avisa:
  141 de las 150 sinopsis se truncan. Se cuentan tokenizando con el tokenizer del modelo.
- **`numpy==1.23.5` del apunte no convive con `sentence-transformers`.** Se usa
  `gensim>=4.3.3` con el numpy que trae Colab.
- **El pooler de Supabase no soporta *prepared statements*.** Se conecta con
  `prepare_threshold=None` en psycopg.
- **Con 150 filas Postgres no usa el índice HNSW** (prefiere un recorrido secuencial
  exacto), así que para mostrar el problema de recall con filtros hubo que forzar el
  índice con `enable_seqscan = off` y `enable_sort = off`.
