"""Módulo de cálculo de cotizaciones y distancias.

Proporciona funciones reutilizables para calcular distancias Haversine
y cotizaciones de envío. La lógica principal está en
``app.services.cotizador_service`` para mantener una capa de datos
organizada y reducir la duplicación.
"""

from app.services.cotizador_service import (
    calcular_distancia_haversine,
    calcular_cotizacion,
)


# Alias para compatibilidad con importaciones existentes
__all__ = ['calcular_distancia_haversine', 'calcular_cotizacion']