# TP2 — Embeddings y búsqueda semántica sobre un corpus de novelas bélicas

**Procesamiento del Lenguaje Natural — Tecnicatura Universitaria en Inteligencia Artificial, FCEIA-UNR, 2026**

Integrantes: Manuel Lazarte, Emmanuel Mendoza, Álvaro Toledo, Maximiliano Romano, Federico Nahuel Troanes.

Docente: [COMPLETAR] — Fecha de entrega: [COMPLETAR]

## Resumen

Comparamos cuatro representaciones de 150 sinopsis de la categoría Bélico de Lectulandia (el corpus del TP1): TF-IDF, Word2Vec entrenado sobre el corpus, el promedio de vectores de SBW y el modelo de oración `distiluse-base-multilingual-cased-v1` (SBERT). Persistimos los vectores en Postgres con pgvector, implementamos la búsqueda en SQL con un filtro por género y una búsqueda híbrida (full-text + vectorial) con *Reciprocal Rank Fusion*. Con un conjunto propio de 14 consultas, TF-IDF obtiene la mejor precision@5 (0.40, contra 0.31 de SBERT y 0.03 del azar). Los embeddings le ganan en las consultas sin palabras en común con los relevantes, donde TF-IDF da 0 por construcción, y en alguna consulta en la que a TF-IDF le falta *stemming*.

## 1. Metodología

- **Texto.** El preprocesamiento depende del modelo:
  - versión limpia (minúsculas, sin puntuación, sin stopwords, sin acentos) para TF-IDF y el Word2Vec propio;
  - la misma limpieza **conservando los acentos** para SBW, cuyo vocabulario los tiene;
  - texto **crudo** para SBERT.
- **Modelos.**
  - Word2Vec propio: skip-gram, 300 dimensiones, ventana 5, `min_count=3`, negative sampling.
  - Promedio de vectores SBW (300 dimensiones).
  - SBERT (512 dimensiones, límite de 128 tokens: **141 de 150 sinopsis se truncan**).
  - TF-IDF como línea de base léxica.
- **Persistencia.** Una tabla por modelo (`vector(300)` y `vector(512)`), con índice HNSW `vector_cosine_ops` porque las consultas usan `<=>`. Antes de insertar, se descartan los vectores nulos o no finitos y se normalizan. No hubo que descartar ninguno.
- **Evaluación.** `queries.json` tiene 14 consultas con sus relevantes elegidos a mano leyendo las sinopsis, antes de correr ningún modelo: 11 léxicas y 3 paráfrasis verificadas por código para que no compartan ningún token con sus relevantes. Medimos precision@5 y @10 contra dos referencias:
  - el piso de azar, |relevantes|/N, verificado con 1000 permutaciones;
  - el techo, min(|relevantes|, k)/k.

## 2. Resultados

| precision@5 | TF-IDF | W2V propio | W2V SBW | SBERT | Azar | Techo |
|---|---|---|---|---|---|---|
| Todas (14) | **0.400** | 0.143 | 0.229 | 0.314 | 0.032 | 0.814 |
| Léxicas (11) | **0.509** | 0.182 | 0.236 | 0.364 | 0.035 | 0.873 |
| Paráfrasis (3) | 0.000 | 0.000 | **0.200** | 0.133 | 0.022 | 0.600 |

En precision@10 el orden se mantiene: TF-IDF 0.243, SBERT 0.221, W2V SBW 0.171, W2V propio 0.107, azar 0.032.

La híbrida (`ts_rank` + SBERT con RRF) da 0.357 en P@5, por debajo del full-text solo (0.371), y **0.264 en P@10**, el mejor valor de todos.

La similitud entre pares de documentos al azar es de 0.97 en promedio en el W2V propio y de 0.90 en SBW: en esos espacios todo se parece a todo. En SBERT es 0.28 ± 0.09, el único espacio con dispersión real.

## 3. Discusión

### 3.1 ¿Qué modelo elegiríamos para producción?

**La búsqueda híbrida: full-text de Postgres + SBERT, fusionados con RRF.**

- **Métrica.** Es la mejor en P@10 (0.264) y la más estable: en P@10 nunca queda por debajo del full-text y de SBERT a la vez. Su límite son las paráfrasis: ahí da 0.067 en P@5, lo mismo que el full-text y la mitad que SBERT solo, porque los primeros puestos del full-text desplazan a los vectoriales.
- **Costo.** Corre en una CPU. Embeber 150 sinopsis lleva segundos, y el full-text y el índice viven en la misma base, sin servicios extra.
- **Privacidad.** El modelo corre localmente: ni las consultas ni el catálogo salen a un tercero. Una API comercial de embeddings sí enviaría cada consulta afuera.
- **Reproducibilidad.** El modelo es abierto y con versión fija, así que el mismo texto da siempre el mismo vector. Con una API, el proveedor puede cambiar o retirar el modelo, y entonces hay que re-embeber toda la base.
- **Dependencia de terceros.** Solo para descargar el modelo una vez.

Descartamos el **Word2Vec propio**: con 150 documentos sus vecinos son coocurrencias y no semántica, y es el peor en promedio en P@5 y en P@10. Si hubiera que elegir **un solo** método para este catálogo, el full-text o TF-IDF es más barato y rinde más con el tipo de consultas que medimos. Pero eso depende del sesgo que explicamos en 3.2.

### 3.2 ¿Cuánto mejor es que TF-IDF?

**En promedio no es mejor: es peor.** SBERT obtiene 0.31 de P@5 contra 0.40 de TF-IDF. Por consulta, TF-IDF le gana en 6, empatan en 6 y pierde en 2.

**TF-IDF gana** cuando la consulta nombra términos raros que están literalmente en la sinopsis: "Vietnam" (P@5 = 1.0 contra 0.4), "frente del este" (0.6 contra 0.2), "napoleónicas", "Hernán Cortés". Esos términos tienen IDF alto, mientras que SBERT diluye un nombre propio entre 128 tokens.

**TF-IDF pierde:**
- en las **paráfrasis** (0 por construcción). Por ejemplo, "surcando el firmamento a bordo de aeronaves": SBERT recupera *El vuelo del Intruder* y *Pearl Harbor* sin compartir ninguna palabra con sus sinopsis;
- cuando **falta el stemming**: "submarinos" en plural no coincide con "submarino", y en esa consulta TF-IDF da 0 mientras W2V SBW da 0.4.

Una advertencia: escribimos las consultas léxicas después de leer las sinopsis, así que tomaron su vocabulario, y eso favorece a TF-IDF. Un usuario que no conoce los textos escribiría más parecido a nuestras paráfrasis.

### 3.3 ¿Qué mide y qué no mide precision@k?

**Mide** qué fracción de los primeros k resultados el grupo consideró relevante.

**No mide:**
- **el orden** dentro del top-k;
- **el recall**: con 2 relevantes, P@10 no puede superar 0.2, por eso reportamos el techo al lado;
- **los relevantes que no marcamos**: cuentan como error aunque sean pertinentes;
- **la variación del juicio**: el juicio es binario, de un solo grupo, sobre sinopsis promocionales.

Además, **con 14 consultas las diferencias chicas no son concluyentes**. Los 0.09 que separan a TF-IDF de SBERT equivalen a unos 6 libros relevantes en total. Lo que sí es robusto es que todos superan ampliamente al azar y que el W2V propio es el peor.

### 3.4 Un caso concreto de falla

**Consulta:** "novelas sobre la Guerra Civil norteamericana" (5 relevantes). SBERT obtiene P@5 = 0. Devuelve libros de soldados estadounidenses en la Segunda Guerra (*Las aventuras de Wesley Jackson*, *El baile de los malditos*) y deja al mejor relevante en el puesto 7.

**Hipótesis.** El modelo interpreta "norteamericanos en guerra" y no el evento histórico, porque las sinopsis relevantes no usan esa expresión: dicen "Confederación", "confederado", "guerra de Secesión". `distiluse` es un modelo chico, entrenado para paráfrasis, sin el conocimiento de que esos nombres designan lo mismo. No es un problema de truncado: "Confederación" está en la primera línea.

**Prueba.** Reformulamos la consulta como "la guerra de Secesión entre la Confederación y la Unión":
- las dos novelas que dicen "Confederación" suben a los puestos **1 y 2** (estaban en el 24 y el 15);
- *Cuentos de la Guerra Civil*, la única que dice "Guerra Civil norteamericana", **cae del 41 al 71**.

En este caso, cada libro sube cuando la consulta usa las palabras de su propia sinopsis, que es justo la limitación que se esperaba superar.

TF-IDF falla por la razón opuesta: "civil" lo lleva a una novela de la Guerra Civil **española**.

## 4. Conclusiones

Un buscador semántico "que devuelve cosas razonables" no es necesariamente mejor que TF-IDF. En nuestro corpus, TF-IDF gana en promedio. Los embeddings ganan en las paráfrasis y cuando a TF-IDF le falta *stemming*.

La línea de base y el piso de azar fueron imprescindibles para interpretar los números. Lo mismo la distribución de similitudes: mostró que los espacios de Word2Vec no discriminan aunque el ranking "funcione".

Como trabajo futuro: usar un conjunto de consultas más grande y escrito por personas que no leyeron las sinopsis, aplicar *chunking* para el truncado de SBERT y probar un modelo de oración más grande.

## Uso de asistentes de IA

[COMPLETAR por el grupo: un párrafo que declare para qué se usaron asistentes de IA, según el §9 del enunciado.]
