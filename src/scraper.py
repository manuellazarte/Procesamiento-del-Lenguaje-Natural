"""
Scraper de Lectulandia - Categoría Bélico
==========================================

Extrae metadatos y sinopsis de libros de la categoría "Bélico" en Lectulandia,
siguiendo el diseño acordado en docs/diseno_extraccion.md.

Estrategia (resumen):
    1. Recorrer el listado de la categoría de forma secuencial (page/2, page/3, ...).
    2. Extraer con BeautifulSoup las URLs de las fichas individuales de cada página listada.
    3. Visitar cada ficha con Playwright y extraer título, autores, géneros, serie,
       sinopsis y portada con BeautifulSoup.
    4. Limpiar texto, evitar duplicados por url_libro y guardar incrementalmente en CSV.

Uso:
    python scraper.py --target 150 --headless
    python scraper.py --target 150 --delay 2 --output ../data/libros.csv
"""

import argparse
import csv
import sys
import time
from datetime import date
from pathlib import Path
from urllib.parse import urljoin

import pandas as pd
from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# --------------------------------------------------------------------------- #
# Configuración
# --------------------------------------------------------------------------- #

BASE_URL = "https://ww3.lectulandia.co"
CATEGORY_URL = f"{BASE_URL}/genero/belico/"
CATEGORY_ORIGEN = "belico"

FIELDNAMES = [
    "titulo",
    "autores",
    "generos",
    "serie",
    "sinopsis",
    "url_libro",
    "url_portada",
    "categoria_origen",
    "fecha_extraccion",
]

# Selectores según docs/diseno_extraccion.md
SEL_TITULO = "#title h1"
SEL_AUTORES = "#autor a.dinSource"
SEL_GENEROS = "#genero a.dinSource"
SEL_SERIE = "#serie a.dinSource"
SEL_SINOPSIS = "#sinopsis span"
SEL_PORTADA = "#leftBlock #cover img"
SEL_BOOK_LINKS = "#page #content #primary #main #bookGrid article.card a.card-click-target"


# --------------------------------------------------------------------------- #
# Utilidades
# --------------------------------------------------------------------------- #

def clean_text(text: str | None) -> str:
    """Elimina espacios y saltos de línea innecesarios. Devuelve '' si no hay texto."""
    if not text:
        return ""
    return " ".join(text.split()).strip()


def join_multi(elements) -> str:
    """Une varios elementos <a> (autores, géneros, serie) con ';'."""
    values = [clean_text(el.get_text()) for el in elements]
    values = [v for v in values if v]
    return ";".join(values)


def load_existing_urls(output_path: Path) -> set[str]:
    """Si ya existe un CSV parcial, carga las URLs ya extraídas para no repetirlas."""
    if not output_path.exists():
        return set()
    try:
        df = pd.read_csv(output_path)
        return set(df["url_libro"].dropna().tolist())
    except Exception:
        return set()


def append_row_to_csv(row: dict, output_path: Path) -> None:
    """Guarda un registro de forma incremental (append) en el CSV final."""
    file_exists = output_path.exists()
    with open(output_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row)


# --------------------------------------------------------------------------- #
# Extracción
# --------------------------------------------------------------------------- #

def get_html(page, url: str, timeout_ms: int = 20000) -> str | None:
    """Navega a una URL con Playwright y devuelve el HTML. Devuelve None si falla."""
    try:
        page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
        return page.content()
    except PlaywrightTimeoutError:
        print(f"  [WARN] Timeout al cargar: {url}")
        return None
    except Exception as exc:
        print(f"  [WARN] Error al cargar {url}: {exc}")
        return None


def extract_book_links(listing_html: str) -> list[str]:
    """Extrae las URLs de las fichas individuales desde una página de listado."""
    soup = BeautifulSoup(listing_html, "html.parser")
    links = []
    for a in soup.select(SEL_BOOK_LINKS):
        href = a.get("href")
        if not href:
            continue
        # El href puede venir sin el dominio, o ya completo
        full_url = urljoin(BASE_URL, href)
        links.append(full_url)
    return links


def extract_book_data(book_html: str, url: str) -> dict | None:
    """Extrae los metadatos y la sinopsis de una ficha individual de libro."""
    soup = BeautifulSoup(book_html, "html.parser")

    titulo_el = soup.select_one(SEL_TITULO)
    titulo = clean_text(titulo_el.get_text()) if titulo_el else ""

    if not titulo:
        # Sin título no consideramos válido el registro (control mínimo del diseño)
        return None

    autores = join_multi(soup.select(SEL_AUTORES))
    generos = join_multi(soup.select(SEL_GENEROS))
    serie = join_multi(soup.select(SEL_SERIE))

    sinopsis_el = soup.select_one(SEL_SINOPSIS)
    sinopsis = clean_text(sinopsis_el.get_text()) if sinopsis_el else ""

    portada_el = soup.select_one(SEL_PORTADA)
    url_portada = portada_el.get("src") if portada_el else ""
    if url_portada:
        url_portada = urljoin(BASE_URL, url_portada)

    return {
        "titulo": titulo,
        "autores": autores,
        "generos": generos,
        "serie": serie,
        "sinopsis": sinopsis,
        "url_libro": url,
        "url_portada": url_portada or "",
        "categoria_origen": CATEGORY_ORIGEN,
        "fecha_extraccion": date.today().isoformat(),
    }


# --------------------------------------------------------------------------- #
# Loop principal
# --------------------------------------------------------------------------- #

def collect_book_urls(page, target: int, delay: float) -> list[str]:
    """Recorre el listado de la categoría de forma secuencial hasta juntar
    al menos `target` URLs de libros únicas."""
    urls: list[str] = []
    seen = set()
    page_num = 1

    while len(urls) < target:
        listing_url = CATEGORY_URL if page_num == 1 else urljoin(CATEGORY_URL, f"page/{page_num}/")
        print(f"[LISTADO] Página {page_num}: {listing_url}")

        html = get_html(page, listing_url)
        if html is None:
            print(f"  [WARN] No se pudo obtener la página {page_num}, se detiene el listado.")
            break

        links = extract_book_links(html)
        if not links:
            print(f"  [INFO] No se encontraron más libros en la página {page_num}. Fin del listado.")
            break

        nuevos = 0
        for link in links:
            if link not in seen:
                seen.add(link)
                urls.append(link)
                nuevos += 1

        print(f"  -> {nuevos} libros nuevos (acumulado: {len(urls)})")

        page_num += 1
        time.sleep(delay)

    return urls[:target] if len(urls) > target else urls


def scrape_books(page, book_urls: list[str], output_path: Path, delay: float) -> int:
    """Visita cada ficha individual, extrae los datos y los guarda incrementalmente."""
    already_done = load_existing_urls(output_path)
    guardados = 0

    for i, url in enumerate(book_urls, start=1):
        if url in already_done:
            continue  # evita duplicados si se corta y se vuelve a correr el script

        print(f"[FICHA {i}/{len(book_urls)}] {url}")

        html = get_html(page, url)
        if html is None:
            continue  # error controlado: se sigue con el próximo libro

        try:
            data = extract_book_data(html, url)
        except Exception as exc:
            print(f"  [WARN] Error al parsear {url}: {exc}")
            continue

        if data is None:
            print("  [WARN] Registro descartado: sin título.")
            continue

        append_row_to_csv(data, output_path)
        already_done.add(url)
        guardados += 1

        time.sleep(delay)

    return guardados


def run(target: int, delay: float, headless: bool, output: str) -> None:
    output_path = Path(output)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        print("=== Paso 1: recolectando URLs de libros del listado ===")
        book_urls = collect_book_urls(page, target=target, delay=delay)
        print(f"Total de URLs únicas recolectadas: {len(book_urls)}")

        print("\n=== Paso 2: visitando fichas individuales ===")
        guardados = scrape_books(page, book_urls, output_path, delay=delay)

        browser.close()

    print(f"\nListo. Se guardaron {guardados} libros nuevos en: {output_path}")

    # Control mínimo: reportar duplicados y campos faltantes
    if output_path.exists():
        df = pd.read_csv(output_path)
        print(f"Total acumulado en {output_path.name}: {len(df)} registros")
        print(f"Duplicados por url_libro: {df.duplicated(subset='url_libro').sum()}")
        print(f"Registros sin sinopsis: {(df['sinopsis'].fillna('') == '').sum()}")


def main():
    parser = argparse.ArgumentParser(description="Scraper de la categoría Bélico en Lectulandia")
    parser.add_argument("--target", type=int, default=150, help="Cantidad objetivo de libros (100-200)")
    parser.add_argument("--delay", type=float, default=1.5, help="Pausa en segundos entre requests")
    parser.add_argument("--headless", action="store_true", default=True, help="Ejecutar sin ventana de navegador")
    parser.add_argument("--show-browser", dest="headless", action="store_false", help="Mostrar la ventana del navegador")
    parser.add_argument("--output", type=str, default="../data/libros.csv", help="Ruta del CSV de salida")
    args = parser.parse_args()

    try:
        run(target=args.target, delay=args.delay, headless=args.headless, output=args.output)
    except KeyboardInterrupt:
        print("\nInterrumpido por el usuario. Los datos guardados hasta ahora quedan en el CSV.")
        sys.exit(0)


if __name__ == "__main__":
    main()