"""Servicio de autenticación."""

import os
import datetime
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.models import db, Usuario


ph = PasswordHasher()
JWT_SECRET = os.getenv('JWT_SECRET', 'secreto_por_defecto')
CREDENCIALES_INVALIDAS = {"message": "Credenciales inválidas"}


class AuthService:
    """Servicio de autenticación con encapsulamiento de credenciales."""

    @staticmethod
    def _hashear_password(password):
        try:
            return ph.hash(password), None
        except Exception:
            return None, {"message": "Error al hashear la contraseña"}

    @staticmethod
    def _persistir_usuario(email, password_hash, rol):
        usuario = Usuario(
            email=email,
            password_hash=password_hash,
            rol=rol,
        )
        db.session.add(usuario)
        db.session.commit()
        return usuario

    @staticmethod
    def _crear_usuario(email, password, rol):
        password_hash, error = AuthService._hashear_password(password)
        if error:
            return None, error, 500
        return AuthService._persistir_usuario(email, password_hash, rol), None, 201

    @staticmethod
    def registrar(email, password, rol='cliente'):
        """Registra un nuevo usuario. Retorna (result, error, status)."""
        if Usuario.query.filter_by(email=email).first():
            return None, {"message": "El usuario ya existe"}, 400

        usuario, error, status = AuthService._crear_usuario(
            email, password, rol
        )
        if error:
            return None, error, status

        return {
            "message": "Usuario registrado exitosamente",
            "usuario": {
                "id": usuario.id,
                "email": usuario.email,
                "rol": usuario.rol,
            },
        }, None, 201

    @staticmethod
    def _generar_token(usuario):
        payload = {
            "usuario_id": usuario.id,
            "email": usuario.email,
            "rol": usuario.rol,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24),
        }
        import jwt

        return jwt.encode(payload, JWT_SECRET, algorithm="HS256")

    @staticmethod
    def iniciar_sesion(email, password):
        """Inicia sesión. Retorna (result, error, status)."""
        usuario = Usuario.query.filter_by(email=email).first()
        if not usuario:
            return None, CREDENCIALES_INVALIDAS, 401

        try:
            ph.verify(usuario.password_hash, password)
        except VerifyMismatchError:
            return None, CREDENCIALES_INVALIDAS, 401

        return {
            "message": "Inicio de sesión exitoso",
            "token": AuthService._generar_token(usuario),
            "rol": usuario.rol,
        }, None, 200
