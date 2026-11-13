"""Módulo de compatibilidad para el cálculo de cotizaciones.

La implementación vive en :mod:`app.services.cotizador_service`; este módulo
sólo reexporta las funciones para importaciones históricas.
"""

from app.services.cotizador_service import (
    calcular_cotizacion,
    calcular_distancia_haversine,
)


__all__ = ['calcular_distancia_haversine', 'calcular_cotizacion']
