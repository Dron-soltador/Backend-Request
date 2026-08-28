import os
import datetime
import jwt
from flask import Blueprint, request, jsonify
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.models import db, Usuario

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')
ph = PasswordHasher()
JWT_SECRET = os.getenv('JWT_SECRET', 'secreto_por_defecto')

@auth_bp.route('/register', methods=['POST'])
def register():
    """
    Registro de un nuevo usuario
    ---
    tags:
      - Autenticación
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: "usuario@ejemplo.com"
            password:
              type: string
              example: "clave123"
            rol:
              type: string
              example: "cliente"
    responses:
      201:
        description: Usuario registrado exitosamente
      400:
        description: Email/Contraseña requeridos o el usuario ya existe
    """
    data = request.get_json() or {}
    
    email = data.get('email')
    password = data.get('password')
    rol = data.get('rol', 'cliente')

    if not email or not password:
        return jsonify({"message": "Email y contraseña son requeridos"}), 400

    if Usuario.query.filter_by(email=email).first():
        return jsonify({"message": "El usuario ya existe"}), 400

    hashed_password = ph.hash(password)

    nuevo_usuario = Usuario(
        email=email,
        password_hash=hashed_password,
        rol=rol
    )

    db.session.add(nuevo_usuario)
    db.session.commit()

    return jsonify({
        "message": "Usuario registrado exitosamente",
        "usuario": nuevo_usuario.to_dict()
    }), 201


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    Inicio de sesión de usuario
    ---
    tags:
      - Autenticación
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: "usuario@ejemplo.com"
            password:
              type: string
              example: "clave123"
    responses:
      200:
        description: Inicio de sesión exitoso con Token JWT
      401:
        description: Credenciales inválidas
    """
    data = request.get_json() or {}
    email = data.get('email')
    password = data.get('password')

    if not email or not password:
        return jsonify({"message": "Email y contraseña son requeridos"}), 400

    usuario = Usuario.query.filter_by(email=email).first()

    if not usuario:
        return jsonify({"message": "Credenciales inválidas"}), 401

    try:
        ph.verify(usuario.password_hash, password)
    except VerifyMismatchError:
        return jsonify({"message": "Credenciales inválidas"}), 401

    payload = {
        "usuario_id": usuario.id,
        "email": usuario.email,
        "rol": usuario.rol,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
    }
    
    token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    return jsonify({
        "message": "Inicio de sesión exitoso",
        "token": token,
        "rol": usuario.rol
    }), 200