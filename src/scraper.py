"""
scraper.py
Extracción de metadatos y sinopsis de libros de la categoría "Bélico" en Lectulandia.
Unidad 1 - Procesamiento del Lenguaje Natural

Uso:
    python scraper.py
"""

import csv
import os
import random
import time
from datetime import date

from urllib.parse import urljoin

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

DOMINIO = "https://ww3.lectulandia.com"
BASE_URL = "https://ww3.lectulandia.com/genero/belico/"
CATEGORIA = "belico"
MIN_LIBROS = 50
MAX_LIBROS = 150
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_PATH = os.path.join(SCRIPT_DIR, "..", "data", "libros.csv")
FIELDNAMES = [
    "titulo", "autores", "generos", "serie", "sinopsis",
    "url_libro", "categoria_origen", "fecha_extraccion", "url_portada",
]


def url_pagina(n):
    """Página 1 = URL base sin sufijo. Página 2+ = /page/n/."""
    if n == 1:
        return BASE_URL
    return f"{BASE_URL}page/{n}/"


def limpiar_texto(texto):
    """Colapsa espacios y saltos de línea múltiples en uno solo."""
    if not texto:
        return ""
    return " ".join(texto.split())


def cargar_urls_existentes():
    """Lee el CSV si ya existe, para no reprocesar libros en una corrida anterior."""
    if not os.path.exists(OUTPUT_PATH):
        return set()
    with open(OUTPUT_PATH, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return {row["url_libro"] for row in reader}


def inicializar_csv():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    if not os.path.exists(OUTPUT_PATH):
        with open(OUTPUT_PATH, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
            writer.writeheader()


def guardar_registro(registro):
    """Guarda incrementalmente: un libro a la vez, no se pierde nada si el script se corta."""
    with open(OUTPUT_PATH, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writerow(registro)


def obtener_libros_de_pagina(page, numero_pagina):
    """Devuelve [{url_libro, url_portada}, ...] de una página del listado de categoría."""
    url = url_pagina(numero_pagina)
    try:
        page.goto(url, timeout=20000)
        page.wait_for_selector("article.card", timeout=10000)
    except Exception as e:
        print(f"  [!] No se pudo cargar la página {numero_pagina}: {e}")
        return [], False

    soup = BeautifulSoup(page.content(), "html.parser")

    libros = []
    for art in soup.select("article.card"):
        link_tag = art.select_one("a.title")
        img_tag = art.select_one("img.cover")
        if not link_tag or not link_tag.get("href"):
            continue
        libros.append({
            "url_libro": urljoin(DOMINIO, link_tag["href"]),
            "url_portada": img_tag["src"] if img_tag else "",
        })

    # TODO: confirmar el selector real del link "Siguiente" en el pie de paginación
    hay_siguiente = soup.select_one("a.next") is not None
    return libros, hay_siguiente


def extraer_ficha(page, url_libro, url_portada):
    """Visita la ficha individual del libro y extrae metadatos + sinopsis completa."""
    page.goto(url_libro, timeout=20000)
    page.wait_for_selector("#title", timeout=10000)
    soup = BeautifulSoup(page.content(), "html.parser")

    titulo_tag = soup.select_one("#title > h1")
    titulo = limpiar_texto(titulo_tag.get_text()) if titulo_tag else ""

    autor_tags = soup.select("#autor > a.dinSource")
    autores = "; ".join(limpiar_texto(a.get_text()) for a in autor_tags)

    # TODO: confirmar selector real de género (expandir #genero en devtools)
    genero_tags = soup.select("#genero a")
    generos = "; ".join(limpiar_texto(g.get_text()) for g in genero_tags)

    # TODO: confirmar selector real de serie (solo presente si el libro pertenece a una)
    serie_tag = soup.select_one("#serie a")  # placeholder, revisar en devtools
    serie = limpiar_texto(serie_tag.get_text()) if serie_tag else ""

    sinopsis_tag = soup.select_one("#sinopsis span")
    sinopsis = ""
    if sinopsis_tag:
        for br in sinopsis_tag.find_all("br"):
            br.replace_with("\n")
        sinopsis = limpiar_texto(sinopsis_tag.get_text(separator=" "))

    return {
        "titulo": titulo,
        "autores": autores,
        "generos": generos,
        "serie": serie,
        "sinopsis": sinopsis,
        "url_libro": url_libro,
        "categoria_origen": CATEGORIA,
        "fecha_extraccion": date.today().isoformat(),
        "url_portada": url_portada,
    }


def main():
    inicializar_csv()
    urls_existentes = cargar_urls_existentes()
    total_guardados = len(urls_existentes)
    print(f"Registros ya guardados previamente: {total_guardados}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        pagina_actual = 1
        while total_guardados < MAX_LIBROS:
            print(f"Recorriendo página de categoría {pagina_actual}...")
            libros, hay_siguiente = obtener_libros_de_pagina(page, pagina_actual)

            if not libros and pagina_actual > 1:
                print("No se encontraron más libros. Fin de la categoría.")
                break

            for libro in libros:
                if total_guardados >= MAX_LIBROS:
                    break
                if libro["url_libro"] in urls_existentes:
                    continue  # evita duplicados entre corridas

                try:
                    registro = extraer_ficha(page, libro["url_libro"], libro["url_portada"])
                    guardar_registro(registro)
                    urls_existentes.add(libro["url_libro"])
                    total_guardados += 1
                    print(f"  [{total_guardados}] {registro['titulo']}")
                except Exception as e:
                    print(f"  [!] Error al procesar {libro['url_libro']}: {e}")
                    continue  # no se detiene la ejecución completa por un error puntual

                time.sleep(random.uniform(1.5, 3.0))  # pausa entre fichas individuales

            if not hay_siguiente:
                print("No hay página siguiente. Fin de la categoría.")
                break

            pagina_actual += 1
            time.sleep(random.uniform(1.0, 2.0))  # pausa entre páginas de categoría

        browser.close()

    print(f"\nProceso terminado. Total de libros guardados: {total_guardados}")
    if total_guardados < MIN_LIBROS:
        print(f"[!] Atención: se obtuvieron menos de {MIN_LIBROS} libros. Revisar selectores o categoría.")


if __name__ == "__main__":
    main()
