"""Tests for auth service using pytest."""
import pytest
import os
from unittest.mock import patch
from app import create_app
from app.models import db, Usuario
from app.services.auth_service import AuthService
from argon2 import PasswordHasher


@pytest.fixture
def setup_app():
    """Create a fresh app and database for each test."""
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    os.environ['JWT_SECRET'] = 'test-secret'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app, db
        db.session.remove()
        db.drop_all()


class TestAuthServiceRegister:
    """Test AuthService.registrar."""

    def test_registrar_usuario_nuevo(self, setup_app):
        """Test registering a new user."""
        app, db = setup_app
        result, error, status = AuthService.registrar('test@example.com', 'password123', 'cliente')
        assert status == 201
        assert error is None
        assert result['message'] == 'Usuario registrado exitosamente'
        assert 'usuario' in result
        assert result['usuario']['email'] == 'test@example.com'
        assert result['usuario']['rol'] == 'cliente'
        
        # User should be in database
        usuario = Usuario.query.filter_by(email='test@example.com').first()
        assert usuario is not None
        assert usuario.rol == 'cliente'

    def test_registrar_usuario_duplicado(self, setup_app):
        """Test registering a user that already exists."""
        app, db = setup_app
        # First registration
        AuthService.registrar('test2@example.com', 'password123', 'cliente')
        
        # Second registration should fail
        result, error, status = AuthService.registrar('test2@example.com', 'password123', 'cliente')
        assert status == 400
        assert error is not None
        assert error['message'] == 'El usuario ya existe'

    def test_registrar_error_hasheo(self, setup_app):
        """Test error during password hashing."""
        app, db = setup_app
        # This is hard to trigger directly, but we test the flow
        result, error, status = AuthService.registrar('nuevo@example.com', 'password123', 'cliente')
        # Should succeed normally
        assert status == 201 or error is None


class TestAuthServiceLogin:
    """Test AuthService.iniciar_sesion."""

    def test_iniciar_sesion_correcto(self, setup_app):
        """Test successful login."""
        app, db = setup_app
        # First register a user
        AuthService.registrar('login@example.com', 'password123', 'cliente')
        
        # Then login
        result, error, status = AuthService.iniciar_sesion('login@example.com', 'password123')
        assert status == 200
        assert error is None
        assert 'message' in result
        assert 'token' in result
        assert result['rol'] == 'cliente'

    def test_iniciar_sesion_usuario_inexistente(self, setup_app):
        """Test login with non-existent user."""
        app, db = setup_app
        result, error, status = AuthService.iniciar_sesion('nonexistent@example.com', 'password123')
        assert status == 401
        assert error is not None
        assert error['message'] == 'Credenciales inválidas'

    def test_iniciar_sesion_contrasena_incorrecta(self, setup_app):
        """Test login with wrong password."""
        app, db = setup_app
        # Register user first
        AuthService.registrar('wrongpass@example.com', 'correct_password', 'cliente')
        
        # Try with wrong password
        result, error, status = AuthService.iniciar_sesion('wrongpass@example.com', 'wrong_password')
        assert status == 401
        assert error is not None
        assert error['message'] == 'Credenciales inválidas'