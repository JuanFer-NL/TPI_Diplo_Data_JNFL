"""
TRANSFORM — De datos crudos a un dataset analítico
=============================================================================

Este es el corazón del TP. El Extract ya te trae los datos y el Load ya
sabe guardarlos: lo que falta es convertir lo crudo en algo analizable.

El recorrido es:

    formato ANCHO (como llega de la API)
        fecha        China   Brasil   ...   __TOTAL__
        1993-01-01    12.3     45.6   ...      120.0

              |  ancho_a_largo()
              v

    formato LARGO / "tidy" (una fila por observación)
        anio  provincia  destino  valor_musd  total_provincia_musd
        1993  Chaco      China          12.3                 120.0
        1993  Chaco      Brasil         45.6                 120.0

              |  + columnas derivadas
              |  + join con rubros
              v

    dataset final de 13 columnas
"""

import logging

import config

# Nombre reservado que usa extract.py para la serie del total provincial
CLAVE_TOTAL = "__TOTAL__"

# Orden final de las columnas del CSV. Es un contrato: el Load lo respeta
# y la consigna del TP lo exige. NO lo modifiques.
COLUMNAS = [
    "anio",
    "provincia",
    "destino",
    "region_destino",
    "valor_musd",
    "total_provincia_musd",
    "participacion_pct",
    "var_interanual_pct",
    "decada",
    "ranking_destino",
    "es_top3",
    "rubro_principal",
    "pp_participacion_pct",
]


# ======================================================================
# 1) ANCHO -> LARGO
# ======================================================================
def extraer_anio(fecha_texto):
    """Convierte '1993-01-01' en el entero 1993.

    Esta te la dejamos resuelta como ejemplo del estilo que esperamos:
    una función corta, con nombre de verbo y un solo trabajo.
    """
    return int(fecha_texto[:4])


def ancho_a_largo(paquetes_destino):
    """CONTRATO: recibe los paquetes crudos de destino; devuelve una lista
    de dicts con una fila por (año, provincia, destino).

    Cada dict debe tener exactamente estas 5 claves:
        anio                  (int)
        provincia             (str)
        destino               (str)
        valor_musd            (float, redondeado a 2 decimales)
        total_provincia_musd  (float, redondeado a 2 decimales)

    Cada paquete tiene esta forma:
        {
          "provincia": "Chaco",
          "orden_columnas": ["China", "Brasil", ..., "__TOTAL__"],
          "data": [["1993-01-01", 12.3, 45.6, ..., 120.0], ...]
        }

    En cada fila de 'data', el elemento 0 es la fecha y los siguientes
    son los valores, EN EL MISMO ORDEN que 'orden_columnas'.

    Ojo con tres cosas:
      - La columna CLAVE_TOTAL no es un destino: no genera fila propia,
        pero su valor va en 'total_provincia_musd' de todas las filas
        de ese año.
      - Si un valor es None, salteá esa observación (patrón 'continue').
      - Redondeá los valores a 2 decimales con round().
    """
    filas = []

    # TODO 1 --------------------------------------------------------------
    for paquete in paquetes_destino:
        provincia = paquete["provincia"]
        columnas = paquete["orden_columnas"]
        posicion_total = columnas.index(CLAVE_TOTAL)

        for fila_cruda in paquete["data"]:
            anio = extraer_anio(fila_cruda[0])
            valores = fila_cruda[1:]
            total = valores[posicion_total]
            total_redondeado = round(total, 2) if total is not None else None

            for posicion, destino in enumerate(columnas):
                valor = valores[posicion]
                # El total no es un destino, y un faltante no se puede
                # marcar como cero: si se rellena se distorsionan promedios
                # y variaciones.
                if destino == CLAVE_TOTAL or valor is None:
                    continue
                filas.append({
                    "anio": anio,
                    "provincia": provincia,
                    "destino": destino,
                    "valor_musd": round(valor, 2),
                    "total_provincia_musd": total_redondeado,
                })
    # ---------------------------------------------------------------------

    logging.info("  ancho_a_largo: %s filas", len(filas))
    return filas


# ======================================================================
# 2) COLUMNAS DERIVADAS SIMPLES
# ======================================================================
def clasificar_region(destino):
    """Devuelve la región geoeconómica de un país de destino.

    Ejemplos:  'Brasil' -> 'Mercosur'   |   'China' -> 'Asia'

    El mapeo está en config.REGIONES. Si el país NO está en el
    diccionario, devolvé config.REGION_POR_DEFECTO en lugar de romper.
    """
    # TODO 2 --------------------------------------------------------------
    # Si hay un país nuevo en la API que no haya sido mapeado
    # se usa la región por defecto y así no se corta el pipeline
    return config.REGIONES.get(destino, config.REGION_POR_DEFECTO)
    # ---------------------------------------------------------------------


def calcular_decada(anio):
    """Devuelve la década de un año como texto.

    Ejemplos:  1993 -> '1990s'   |   2024 -> '2020s'
    """
    # TODO 3 --------------------------------------------------------------
    decada = (anio // 10) * 10
    return f"{decada}s"
    # ---------------------------------------------------------------------


def calcular_participacion(valor, total):
    """Qué porcentaje del total exportado representa este destino.

    Ejemplo:  valor=110.93, total=401.74  ->  27.61

    Devolvé None si el total es cero o None: dividir por cero rompe el
    programa, y un dato ausente es más honesto que un cero inventado.
    Redondeá a 2 decimales.
    """
    # TODO 4 --------------------------------------------------------------
    # Se devuelve None y no cero porque un dato faltante no es lo mismo
    # que haber exportado cero, y un cero inventado sesgaría cálculos futuros
    if valor is None or total is None or total == 0:
        return None

    participacion_destino = (valor / total) * 100
    return round(participacion_destino, 2)
    # ---------------------------------------------------------------------


def agregar_derivadas_simples(filas):
    """Agrega region_destino, decada y participacion_pct a cada fila.

    CONTRATO: modifica y devuelve la misma lista de filas.
    """
    for fila in filas:
        fila["region_destino"] = clasificar_region(fila["destino"])
        fila["decada"] = calcular_decada(fila["anio"])
        fila["participacion_pct"] = calcular_participacion(
            fila["valor_musd"], fila["total_provincia_musd"]
        )
    return filas


# ======================================================================
# 3) VARIACIÓN INTERANUAL
# ======================================================================
def calcular_variacion(actual, anterior):
    """Variación porcentual entre dos valores.

    Fórmula:  (actual - anterior) / anterior * 100
    Ejemplo:  actual=110.93, anterior=75.79  ->  46.36

    Devolvé None si 'anterior' es None o cero. Redondeá a 2 decimales.
    """
    # TODO 5 --------------------------------------------------------------
    # Si no hay año anterior, como sucede con el primer año de la serie,
    # o si el año anterior no se exportó nada,
    # no tiene sentido calcular la variación
    if anterior is None or anterior == 0:
        return None

    variacion_exportacion = (actual / anterior - 1) * 100
    return round(variacion_exportacion, 2)
    # ---------------------------------------------------------------------


def agregar_variacion_interanual(filas):
    """Agrega var_interanual_pct comparando cada fila con el año previo
    del MISMO destino y la MISMA provincia.

    CONTRATO: modifica y devuelve la misma lista de filas. La primera
    observación de cada serie queda con None (no hay año anterior).
    """
    # TODO 6 --------------------------------------------------------------
    # Primero se crea un dict para encontrar cualquier valor sin recorrer
    # toda la lista, porque las filas no están ordenadas por serie
    valores_por_serie = {}
    for fila in filas:
        clave = (fila["provincia"], fila["destino"], fila["anio"])
        valores_por_serie[clave] = fila["valor_musd"]

    # Luego, cada fila se compara con su misma serie del año previo
    for fila in filas:
        clave_anio_previo = (
            fila["provincia"], fila["destino"], fila["anio"] - 1
        )
        valor_anterior = valores_por_serie.get(clave_anio_previo)
        fila["var_interanual_pct"] = calcular_variacion(
            fila["valor_musd"], valor_anterior
        )

    return filas
    # ---------------------------------------------------------------------


# ======================================================================
# 4) RANKING DE DESTINOS
# ======================================================================
def agregar_ranking(filas, top_n=None):
    """Agrega ranking_destino (1 = el que más exportó) y es_top3 (bool).

    El ranking se calcula DENTRO de cada grupo (provincia, año): ser el
    destino #1 de Chaco en 2024 no dice nada sobre Misiones en 1998.

    CONTRATO: modifica y devuelve la misma lista de filas.
    El destino de config.DESTINO_SIN_RANKING no compite: queda con
    ranking None y es_top3 en False.
    """
    if top_n is None:
        top_n = config.TOP_N

    # TODO 7 --------------------------------------------------------------
    # Se rankean los países por provincia y año
    grupos = {}
    for fila in filas:
        clave_prov_anio = (fila["provincia"], fila["anio"])
        grupos.setdefault(clave_prov_anio, []).append(fila)

    for grupo in grupos.values():
        # Se excluye a Resto del ranking
        for fila in grupo:
            if fila["destino"] == config.DESTINO_SIN_RANKING:
                fila["ranking_destino"] = None
                fila["es_top3"] = False

        paises = [
            f for f in grupo if f["destino"] != config.DESTINO_SIN_RANKING
        ]
        orden = sorted(paises, key=lambda f: f["valor_musd"], reverse=True)
        for posicion, fila in enumerate(orden, start=1):
            fila["ranking_destino"] = posicion
            fila["es_top3"] = posicion <= top_n

    return filas
    # ---------------------------------------------------------------------


# ======================================================================
# 5) JOIN CON LOS RUBROS
# ======================================================================
def construir_indice_rubros(paquetes_rubro):
    """CONTRATO: recibe los paquetes crudos de rubro; devuelve un índice

        {(provincia, anio): {"rubro_principal": str,
                             "pp_participacion_pct": float}}

    Ese índice es la "tabla derecha" del join: la clave compuesta
    (provincia, anio) es lo que permite pegarlo al dataset de destinos.

    Para cada (provincia, año):
      - rubro_principal      = el rubro con MAYOR valor ese año.
      - pp_participacion_pct = qué % del total de ese año representan los
                               'Productos primarios', redondeado a 2 dec.

    Los paquetes tienen la misma forma que en ancho_a_largo(), pero sus
    columnas son los 4 rubros (sin columna de total).
    """
    indice = {}

    # TODO 8a -------------------------------------------------------------
    for paquete in paquetes_rubro:
        provincia = paquete["provincia"]
        columnas = paquete["orden_columnas"]

        for fila_cruda in paquete["data"]:
            anio = extraer_anio(fila_cruda[0])
            valores = fila_cruda[1:]

            # Se sacan los rubros sin datos para que no ganen
            # ni sumen al total del año
            valor_por_rubro = {
                rubro: valor
                for rubro, valor in zip(columnas, valores)
                if valor is not None
            }
            if not valor_por_rubro:
                continue

            total_anio = sum(valor_por_rubro.values())
            rubro_max = max(valor_por_rubro, key=valor_por_rubro.get)
            indice[(provincia, anio)] = {
                "rubro_principal": rubro_max,
                "pp_participacion_pct": calcular_participacion(
                    valor_por_rubro.get("Productos primarios"), total_anio
                ),
            }
    # ---------------------------------------------------------------------

    logging.info("  índice de rubros: %s claves (provincia, año)", len(indice))
    return indice


def unir_con_rubros(filas, indice_rubros):
    """Join por clave compuesta (provincia, anio).

    Debe ser un LEFT JOIN: si una combinación no está en el índice, las
    dos columnas quedan en None, pero LA FILA NO SE PIERDE.

    CONTRATO: modifica y devuelve la misma lista de filas.
    """
    # TODO 8b -------------------------------------------------------------
    for fila in filas:
        clave = (fila["provincia"], fila["anio"])
        # LEFT JOIN: si no hay match, el dict vacío deja las columnas
        # en None y la fila se conserva
        datos_rubro = indice_rubros.get(clave, {})
        fila["rubro_principal"] = datos_rubro.get("rubro_principal")
        fila["pp_participacion_pct"] = datos_rubro.get("pp_participacion_pct")

    return filas
    # ---------------------------------------------------------------------


# ======================================================================
# ORQUESTACIÓN DEL TRANSFORM  (ya resuelta: no hace falta tocarla)
# ======================================================================

def calcular_clave_orden(fila):
    """Devuelve la clave para ordenar el dataset final:
    provincia, año y ranking (1 primero).

    Las filas sin ranking (Resto) van al final de su grupo. Para lograr
    esto se reemplaza el None de Resto por infinito porque no se puede
    comparar un NoneType con un número.
    """
    ranking = fila["ranking_destino"]
    if ranking is None:
        ranking = float("inf")
    return (fila["provincia"], fila["anio"], ranking)


def ordenar_columnas(filas):
    """Devuelve las filas con las claves en el orden definido por COLUMNAS."""
    return [{columna: fila.get(columna) for columna in COLUMNAS} for fila in filas]


def transformar(datos_crudos):
    """CONTRATO: recibe {'destino': [...], 'rubro': [...]} crudos;
    devuelve la lista de filas finales, ordenadas y con las 13 columnas.

    Fijate cómo esta función 'directora' solo llama a las otras en orden.
    Eso es diseño modular: si mañana cambia una regla, tocás una función.
    """
    logging.info("TRANSFORM: iniciando")

    filas = ancho_a_largo(datos_crudos["destino"])
    filas = agregar_derivadas_simples(filas)
    filas = agregar_variacion_interanual(filas)
    filas = agregar_ranking(filas)

    indice = construir_indice_rubros(datos_crudos["rubro"])
    filas = unir_con_rubros(filas, indice)

    filas.sort(key=calcular_clave_orden)
    filas = ordenar_columnas(filas)

    logging.info("TRANSFORM OK: %s filas x %s columnas", len(filas), len(COLUMNAS))
    return filas
