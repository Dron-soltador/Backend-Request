"""Vistas (controladores) de autenticación API v1.

Define los endpoints HTTP /auth para registro e inicio de sesión.
Esta capa solo maneja la entrada/salida HTTP y delegar la lógica al servicio.
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