"""Servicio de lógica de negocio para cotizaciones.

Extrae el cálculo de distancia y de tarifas para que sea reutilizable y
permanezca en la capa de lógica, separado de las vistas HTTP.
"""

import math

from app.services.pedido_service import (
    _parse_peso,
    _to_bool,
    validar_coordenadas_pedido,
)


TARIFA_BASE = 500.0
PRECIO_POR_KG = 200.0
PRECIO_POR_KM = 150.0
RECARGO_FRAGIL = 0.15
RECARGO_URGENTE = 0.25


def calcular_distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Distancia en kilómetros entre dos coordenadas (fórmula haversine)."""
    radio_tierra = 6371.0

    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(radio_tierra * c, 2)


def _recargo(subtotal, activo, porcentaje):
    """Calcula un recargo porcentual sólo cuando corresponde."""
    return round(subtotal * porcentaje, 2) if activo else 0.0


def _recargos(subtotal, opciones):
    """Devuelve (recargo_fragil, recargo_urgente) según las opciones."""
    return (
        _recargo(subtotal, opciones.get('es_fragil', False), RECARGO_FRAGIL),
        _recargo(subtotal, opciones.get('es_urgente', False), RECARGO_URGENTE),
    )


def _desglose(costo_peso, costo_distancia, subtotal, recargos):
    recargo_fragil, recargo_urgente = recargos
    return {
        "tarifa_base": TARIFA_BASE,
        "costo_peso": costo_peso,
        "costo_distancia": costo_distancia,
        "subtotal": subtotal,
        "recargo_fragil": recargo_fragil,
        "recargo_urgente": recargo_urgente,
    }


def calcular_cotizacion(*coordenadas, peso_kg, **recargos):
    """Calcula el costo de un envío entre dos puntos.

    Recibe las coordenadas en orden ``lat_a, lon_a, lat_b, lon_b`` y acepta
    ``es_fragil`` y ``es_urgente`` como opciones con nombre para mantener
    retrocompatibilidad con los llamadores existentes.
    """
    lat_a, lon_a, lat_b, lon_b = coordenadas
    distancia_km = calcular_distancia_haversine(lat_a, lon_a, lat_b, lon_b)
    costo_peso = peso_kg * PRECIO_POR_KG
    costo_distancia = distancia_km * PRECIO_POR_KM
    subtotal = TARIFA_BASE + costo_peso + costo_distancia
    recargos_aplicados = _recargos(subtotal, recargos)

    return {
        "distancia_km": distancia_km,
        "desglose": _desglose(
            costo_peso, costo_distancia, subtotal, recargos_aplicados
        ),
        "costo_total": round(subtotal + sum(recargos_aplicados), 2),
    }


def cotizar_desde_payload(data):
    """Valida un cuerpo HTTP y devuelve la cotización resultante."""
    peso_kg = _parse_peso(data.get('peso_kg'))
    lat_origen, lon_origen, lat_destino, lon_destino = (
        validar_coordenadas_pedido(data)
    )
    return calcular_cotizacion(
        lat_origen,
        lon_origen,
        lat_destino,
        lon_destino,
        peso_kg=peso_kg,
        es_fragil=_to_bool(data.get('es_fragil', False)),
        es_urgente=_to_bool(data.get('es_urgente', False)),
    )
