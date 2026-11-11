"""Módulo de compatibilidad para importaciones históricas de autenticación.

Las rutas activas viven en :mod:`app.routes.api.auth`. Este módulo sólo
reexporta el blueprint para no duplicar la implementación.
"""

from app.routes.api.auth import auth_bp


__all__ = ['auth_bp']
