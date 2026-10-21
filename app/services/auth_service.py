"""Servicio de autenticación."""

import os
import datetime
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from app.models import db, Usuario


ph = PasswordHasher()
JWT_SECRET = os.getenv('JWT_SECRET', 'secreto_por_defecto')


class AuthService:
    """Servicio de autenticación con encapsulamiento de credenciales."""
    
    @staticmethod
    def registrar(email, password, rol='cliente'):
        """Registra un nuevo usuario. Retorna (result_dict, error_dict_or_None, status_code)."""
        from app.models import Usuario, ph
        
        if Usuario.query.filter_by(email=email).first():
            return None, {"message": "El usuario ya existe"}, 400
        
        try:
            hashed_password = ph.hash(password)
        except Exception:
            return None, {"message": "Error al hashear la contraseña"}, 500
        
        nuevo_usuario = Usuario(
            email=email,
            password_hash=hashed_password,
            rol=rol
        )
        
        db.session.add(nuevo_usuario)
        db.session.commit()
        
        return {
            "message": "Usuario registrado exitosamente",
            "usuario": {
                "id": nuevo_usuario.id,
                "email": nuevo_usuario.email,
                "rol": nuevo_usuario.rol
            }
        }, None, 201
    
    @staticmethod
    def iniciar_sesion(email, password):
        """Inicia sesión. Retorna (result_dict, error_dict_or_None, status_code)."""
        from app.models import Usuario, ph
        
        usuario = Usuario.query.filter_by(email=email).first()
        
        if not usuario:
            return None, {"message": "Credenciales inválidas"}, 401
        
        try:
            ph.verify(usuario.password_hash, password)
        except VerifyMismatchError:
            return None, {"message": "Credenciales inválidas"}, 401
        
        payload = {
            "usuario_id": usuario.id,
            "email": usuario.email,
            "rol": usuario.rol,
            "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=24)
        }
        
        import jwt
        token = jwt.encode(payload, JWT_SECRET, algorithm="HS256")
        
        return {
            "message": "Inicio de sesión exitoso",
            "token": token,
            "rol": usuario.rol
        }, None, 200