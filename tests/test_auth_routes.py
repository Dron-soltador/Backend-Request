"""Tests for auth routes using pytest."""
import os
import pytest
from app import create_app
from app.models import db


@pytest.fixture
def setup_app():
    """Create a fresh app and database for each test."""
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app, db
        db.session.remove()
        db.drop_all()


class TestAuthRoutes:
    """Test authentication routes."""

    def test_register_endpoint(self, setup_app):
        """Test POST /auth/register endpoint."""
        app, db = setup_app
        client = app.test_client()
        
        response = client.post('/auth/register', json={
            'email': 'test@example.com',
            'password': 'password123',
            'rol': 'cliente'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['message'] == 'Usuario registrado exitosamente'
        assert data['usuario']['email'] == 'test@example.com'

    def test_register_duplicate_email(self, setup_app):
        """Test registering with duplicate email."""
        app, db = setup_app
        client = app.test_client()
        
        # First registration
        client.post('/auth/register', json={
            'email': 'test2@example.com',
            'password': 'password123',
        })
        
        # Second registration with same email
        response = client.post('/auth/register', json={
            'email': 'test2@example.com',
            'password': 'password123',
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['message'] == 'El usuario ya existe'

    def test_login_successful(self, setup_app):
        """Test POST /auth/login with correct credentials."""
        app, db = setup_app
        client = app.test_client()
        
        # First register
        client.post('/auth/register', json={
            'email': 'login@example.com',
            'password': 'password123',
        })
        
        # Then login
        response = client.post('/auth/login', json={
            'email': 'login@example.com',
            'password': 'password123',
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['message'] == 'Inicio de sesión exitoso'
        assert 'token' in data
        assert data['rol'] == 'cliente'

    def test_login_wrong_credentials(self, setup_app):
        """Test POST /auth/login with wrong credentials."""
        app, db = setup_app
        client = app.test_client()
        
        # Register first
        client.post('/auth/register', json={
            'email': 'wrong@example.com',
            'password': 'correct_password',
        })
        
        # Try wrong password
        response = client.post('/auth/login', json={
            'email': 'wrong@example.com',
            'password': 'wrong_password',
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['message'] == 'Credenciales inválidas'

    def test_login_nonexistent_user(self, setup_app):
        """Test POST /auth/login with non-existent user."""
        app, db = setup_app
        client = app.test_client()
        
        response = client.post('/auth/login', json={
            'email': 'nonexistent@example.com',
            'password': 'password123',
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert data['message'] == 'Credenciales inválidas'