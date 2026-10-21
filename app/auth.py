"""Vistas y rutas de autenticación API.

Este módulo define el blueprint ``auth_bp`` que es registrado por
``app/__init__.py``. La lógica de negocio ha sido extraída a
``app.services.auth_service`` para mantener las capas separadas.
"""

from flask import Blueprint, request, jsonify
from app.services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/register', methods=['POST'])
def register():
    """Registra un nuevo usuario."""
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')
    rol = data.get('rol', 'cliente')

    result, error, status = AuthService.registrar(email, password, rol)
    if error:
        return jsonify(error), status
    return jsonify(result), status


@auth_bp.route('/login', methods=['POST'])
def login():
    """Inicia sesión de usuario."""
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    result, error, status = AuthService.iniciar_sesion(email, password)
    if error:
        return jsonify(error), status
    return jsonify(result), status