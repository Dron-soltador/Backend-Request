"""Módulo de compatibilidad para importaciones históricas de pedidos.

Las rutas activas viven en :mod:`app.routes.api.pedidos`. Este módulo sólo
reexporta el blueprint y la notificación al despachador para no duplicar la
implementación.
"""

from app.integracion import notificar_pedido_al_despachador
from app.routes.api.pedidos import pedidos_bp


__all__ = ['pedidos_bp', 'notificar_pedido_al_despachador']
