# TPI Módulo 2 — Pipeline ETL de exportaciones del NEA
#### Juan Nicolás Fernández Lancelle

**Unidad II · Fundamentos de la Programación**
Diplomatura en Data Analytics e IA Aplicada — UNNE / Extender

---

## ¿Qué hace?

Este proyecto es un pipeline ETL que arma un dataset de las exportaciones de las provincias del NEA a partir de los datos del INDEC (actualmente se cuenta con datos desde 1993 a 2024).

Las tres etapas del pipeline son:

1. **Extract**: Descarga los datos de las exportaciones de la API de datos.gob.ar y los guarda en "data/raw/". Esto es importante ya que permite volver a trabajar con los datos originales sin tener que volver a descargarlos en cada corrida.
2. **Transform**: Pasa los datos de formato ancho a formato largo, es decir, de una columna por país a una fila por provincia, año y destino. Calcula, además, columnas nuevas (región, década, participación, variación interanual y ranking) y las une con los datos de los rubros.
3. **Load**: Se encarga de validar el resultado con cinco controles: cantidad de filas, columnas, duplicados, rangos de valores y cobertura. En caso de que alguno de los controles críticos falle se corta el proceso, caso contrario se guarda el dataset final y deja registro de la corrida.

El proceso del pipeline se puede diagramar de la siguiente forma:

```
API datos.gob.ar  -->  data/raw/*.json  -->  data/processed/exportaciones_nea.csv
                                                data/processed/resumen.json
                                                    logs/pipeline.log
                                                    
    (EXTRACT)              (TRANSFORM)                      (LOAD)
```

El resultado es un CSV de 1.408 filas y 13 columnas, pensado para usarse en el módulo 3 de estadística descriptiva.

---

## Instalación y Ejecución

### Requisitos

- **Python 3.8 o superior.** No hace falta instalar ninguna librería: el proyecto usa solo la biblioteca estándar.
- **Conexión a internet** para la primera corrida.

> En Linux y Mac el comando suele ser `python3`; en Windows, `python` o `py`.

### 1. Clonar el repositorio

```bash
git clone https://github.com/JuanFer-NL/TPI_Diplo_Data_JNFL.git
cd TPI_Diplo_Data_JNFL
```

Todos los comandos siguientes se corren desde esta carpeta (la raíz del proyecto), no desde `src/`.

### 2. Correr el pipeline

```bash
python3 src/main.py
```

La primera vez descarga los datos de la API y los guarda en `data/raw/`.
Como los datos no se suben al repositorio, este paso precisa de internet.

Una vez descargados, se puede volver a correr sin conexión:

```bash
python3 src/main.py --sin-internet
```

### 3. Verificar las salidas

Al terminar, el pipeline genera:

| Archivo                                | Contenido                                               |
| -------------------------------------- | ------------------------------------------------------- |
| `data/processed/exportaciones_nea.csv` | El dataset final (1.408 filas × 13 columnas)            |
| `data/processed/resumen.json`          | Ficha técnica: período, estadísticas, nulos y controles |
| `logs/pipeline.log`                    | Una línea por cada corrida                              |

### 4. Correr los tests

```bash
python3 tests/test_transform.py
```

Son 19 tests: los 17 de la cátedra y 2 propios.

---

## Fuente de datos

Los datos son del **INDEC** y se obtienen a través de la [API de Series de Tiempo](https://apis.datos.gob.ar/series/api/) del portal de datos abiertos del Estado argentino (datos.gob.ar). Es una API abierta: no requiere registro ni credenciales.

|               |                                               |
| ------------- | --------------------------------------------- |
| Dataset 357.1 | Exportaciones por provincia y país de destino |
| Dataset 350.1 | Exportaciones por provincia y rubro           |
| Período       | 1993–2024 (anual)                             |
| Unidad        | Millones de dólares FOB                       |

Los identificadores de cada serie están en `config.py`.

**FOB**: Del inglés "Free on Board", significa que el valor de las exportaciones no incluye ni los costos de logística ni seguros internacionales, es decir, es el valor de únicamente la mercadería.

---

## Hallazgo
### El gran aumento de las exportaciones misioneras a Siria

| Año  | Millones de USD | % del total de Misiones | Ranking     |
| ---- | --------------- | ----------------------- | ----------- |
| 1993 | 8,75            | 6,3%                    | 3°          |
| 2002 | 7,91            | 2,9%                    | 7° (Mínimo) |
| 2011 | 30,16           | 5,6%                    | 5°          |
| 2012 | 43,78           | 9,9%                    | 3°          |
| 2015 | 80,43           | 19,9%                   | 3° (Máximo) |
| 2016 | 51,09           | 14,7%                   | 3°          |
| 2021 | 39,40           | 8,5%                    | 4°          |
| 2024 | 55,60           | 12,6%                   | 3°          |

_(Datos extraídos de la serie Misiones a Siria del `.csv`)_

Las exportaciones de Misiones a Siria crecieron más de 6 veces desde el comienzo de la serie al final, y más de 10 veces considerando la variación entre el mínimo y el máximo.

### Hipótesis

Una posible hipótesis a este suceso es que Siria es uno de los mayores consumidores de yerba mate del mundo, sin contar a Sudamérica, por lo que tiene sentido que Misiones, siendo la principal provincia productora de yerba del país, exporte tanta cantidad a dicho país.

Lo llamativo es cómo puede ser que el crecimiento más fuerte de las exportaciones (2011-2015) coincida con los primeros años de la guerra civil siria.

Es tentador pensar rápidamente que en época de guerra el consumo tiende a caer, pero quizás la explicación viene por el lado contrario: la yerba es un bien necesario, de demanda inelástica respecto del ingreso. Cuando los ingresos caen por la guerra, el consumo de yerba se mantiene, mientras que el consumo de bienes de lujo disminuye, lo que se conoce como "efecto renta" en Economía.

Esta podría ser una buena teoría para explicar cómo las exportaciones se mantuvieron por más de que Siria entró en guerra. Explicar por qué aumentaron es más complejo.

---

## Decisiones de diseño

### "Resto" queda fuera del ranking

Entre los destinos de cada provincia aparece "Resto", que no es un país sino la suma de todos los destinos que quedan fuera de los diez principales. Al ser una suma, suele superar a cualquier país individual. En el ranking original quedaba primero en 69 de los 128 grupos de provincia y año.

Esto le quitaba sentido al ranking y a la columna `es_top3`. Por ejemplo, en Chaco 2024:

|  #  | Con Resto      | Sin Resto (esta versión) |
| :-: | -------------- | ------------------------ |
|  1  | Resto (193,75) | China (110,93)           |
|  2  | China (110,93) | Chile (19,76)            |
|  3  | Chile (19,76)  | Brasil (18,12)           |
|  4  | Brasil (18,12) | Italia (14,71)           |

Por eso decidí que Resto no compita en el ranking. Su fila se mantiene en el dataset, pero queda con `ranking_destino` vacío (`None`) y `es_top3` en `False`. Elegí dejarlo vacío en lugar de asignarle el último puesto porque inventar un número confundiría al realizar el análisis estadístico, dando a pensar que fue el destino que menos exportó.

En el código, el destino excluido está definido en `config.py` (`DESTINO_SIN_RANKING`), y hay un test propio que verifica este comportamiento (`test_resto_queda_fuera_del_ranking`). Para ordenar el dataset final, las filas sin ranking se ubican al final de cada grupo.

### Diferencia con el ejemplo de la consigna

El ejemplo de la consigna muestra la fila de Chaco → Brasil 2024 con ranking 6 y `es_top3` en `False`. Este pipeline da ranking 3 y `True`, por la decisión anterior. Con los datos actuales de la API, Brasil queda 4° si se incluye a Resto y 3° si se lo excluye, así que no logré reproducir el 6° del ejemplo con ninguna de las dos variantes.

### Otras decisiones

- **Un dato faltante no es un cero**: Cuando falta un valor, las columnas calculadas quedan vacías en lugar de valer 0. En cambio, haber exportado 0 a un destino es un dato verdadero y da 0 % de participación.
- **Variación sin base**: Si el año anterior se exportó 0, la variación interanual queda vacía, porque si no estaríamos haciendo una división por cero, la cual no está definida. Este hecho y las variaciones del primer año de cada serie explican los 91 valores vacíos de esa columna.
- **LEFT JOIN con rubros**: Si para una provincia y año no hubiera datos de rubro, la fila se conserva con esas columnas vacías.

---

## Dataset de salida

`data/processed/exportaciones_nea.csv` tiene 13 columnas, en este orden:

|  #  | Columna                | Tipo  | Descripción                                                         |
| :-: | ---------------------- | ----- | ------------------------------------------------------------------- |
|  1  | `anio`                 | int   | Año de la observación (1993–2024)                                   |
|  2  | `provincia`            | str   | Chaco, Corrientes, Formosa o Misiones                               |
|  3  | `destino`              | str   | País de destino (o "Resto")                                         |
|  4  | `region_destino`       | str   | Región geoeconómica del destino                                     |
|  5  | `valor_musd`           | float | Exportado a ese destino, en millones de USD                         |
|  6  | `total_provincia_musd` | float | Total exportado por la provincia ese año                            |
|  7  | `participacion_pct`    | float | `valor / total * 100`                                               |
|  8  | `var_interanual_pct`   | float | Variación vs. el año anterior (vacía el 1er año o si la base es 0)  |
|  9  | `decada`               | str   | 1990s, 2000s, 2010s o 2020s                                         |
| 10  | `ranking_destino`      | int   | Posición del país ese año (1 = el mayor; vacía para Resto)          |
| 11  | `es_top3`              | bool  | Si está entre los 3 principales países                              |
| 12  | `rubro_principal`      | str   | Rubro más exportado por la provincia ese año (del join)             |
| 13  | `pp_participacion_pct` | float | % de productos primarios en el total de la provincia (del join)     |

Dos filas de ejemplo generadas por este pipeline:

```csv
anio,provincia,destino,region_destino,valor_musd,total_provincia_musd,participacion_pct,var_interanual_pct,decada,ranking_destino,es_top3,rubro_principal,pp_participacion_pct
2024,Chaco,China,Asia,110.93,401.74,27.61,46.36,2020s,1,True,Productos primarios,81.3
2024,Chaco,Brasil,Mercosur,18.12,401.74,4.51,30.45,2020s,3,True,Productos primarios,81.3
```

---

## Estructura del proyecto

```
├── config.py              Configuración: IDs de series, rutas, mapeos y parámetros
├── src/
│   ├── extract.py         Descarga de la API -> data/raw/
│   ├── transform.py       Formato largo, columnas derivadas y join con rubros
│   ├── load.py            Controles de calidad y guardado de las 3 salidas
│   └── main.py            Orquesta Extract -> Transform -> Load
├── tests/
│   └── test_transform.py  19 tests (17 de la cátedra + 2 propios)
├── data/
│   ├── raw/               Datos crudos (no se versionan)
│   └── processed/         Salidas finales (no se versionan)
└── logs/                  Historial de corridas (no se versiona)
```
