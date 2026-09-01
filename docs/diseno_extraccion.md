### **Categoría seleccionada**

* Categoría: Bélico  
* URL de la categoría: https://ww3.lectulandia.co/genero/belico/  
* Cantidad de libros que se propone extraer: 150  
* El listado de libros de una categoría está dividido por páginas, se recorrerán páginas de forma secuencial, empezando en la página 1, hasta acumular la cantidad de 150 libros.

**Estructura del dataset**

| Campo | Descripción |
| :---- | ----- |
| `titulo` | Título del libro |
| `autores` | Autor o autores (si hay más de uno, separados por ;)  |
| `generos` | Género o géneros (si hay más de uno, separados por ;) |
| `serie` | Serie a la que pertenece, si corresponde |
| `sinopsis` | Texto completo de la sinopsis |
| `url_libro` | Dirección de la ficha |
| `url_portada` | Dirección de la imagen de portada del libro |
| `categoria_origen` | Categoría seleccionada por el grupo (Bélico) |
| `fecha_extraccion` | Fecha en que se obtuvo el registro |

**Localización de los datos:**

| Dato | Tipo de página | Etiqueta HTML | Selector propuesto |
| :---- | :---- | :---- | :---- |
| Título | Ficha individual | \<h1\> | \#title \> h1  |
| Autores | Ficha individual | \<a\> | \#autor \> a.dinSource |
| Géneros | Ficha individual | \<a\> | \#genero \> a.dinSource |
| Serie | Ficha individual | \<a\> | \#serie \> a.dinSource |
| Sinopsis | Ficha individual | \<span\> | \#sinopsis \> span |
| url del libro | Ficha individual | \<a\> | \#page \> \#content \> \#primary \> \#main \> \#bookGrid \> article.card \> a.card-click-target (href tiene el link del libro sin “ww3.lectulandia.co”) |
| url de portada | Ficha individual | \<img\> | \#leftBlock \> \#cover \>img (acá tiene la url)  |

**Estrategia de extracción** 

1. Abrir la página de la categoría Bélico con Playwright.  
2. Recorrer las páginas del listado de forma secuencial (/page/2/, /page/3/,...) hasta juntar la cantidad de libros objetivo.  
3. Obtener el HTML de cada página del listado mediante Playwright.  
4. Analizar ese HTML con BeautifulSoup para extraer, por cada libro listado, la URL de su ficha individual.  
5. Visitar cada ficha individual con Playwright.  
6. Extraer con BeautifulSoup los metadatos (título, autores, géneros, serie, portada) y la sinopsis completa de cada ficha.  
7. Limpiar y validar los datos (eliminar espacios y saltos de línea innecesarios, normalizar campos ausentes).  
8. Eliminar libros duplicados por url\_libro.  
9. Asignar el valor constante ‘belico’ al campo ‘categoria\_origen’ y la fecha del día a ‘fecha\_extraccion’.  
10. Guardar el resultado de forma incremental y generar el archivo final libros.csv.