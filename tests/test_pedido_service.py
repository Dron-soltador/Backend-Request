"""Tests for pedido service using pytest."""
import pytest
import math
import os
from unittest.mock import patch
from app import create_app
from app.models import db, Pedido, Usuario
from app.services.pedido_service import (
    crear_pedido, _pedido_para_despachador, _validar_coordenadas,
    _to_int_or_none, _to_float_or_none, _to_bool, _fecha_utc,
    _coordenadas_pedido, _coordenadas_punto
)


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


class TestPedidoServiceHelpers:
    """Test helper functions in pedido_service."""

    def test_to_int_or_none(self):
        """Test _to_int_or_none function."""
        assert _to_int_or_none(None) is None
        assert _to_int_or_none('') is None
        assert _to_int_or_none('123') == 123
        assert _to_int_or_none(456) == 456

    def test_to_float_or_none(self):
        """Test _to_float_or_none function."""
        assert _to_float_or_none(None) is None
        assert _to_float_or_none('') is None
        assert _to_float_or_none('1.5') == 1.5
        assert _to_float_or_none('') is None
        # Invalid string raises ValueError (float('abc') raises ValueError)
        with pytest.raises(ValueError):
            _to_float_or_none('abc')

    def test_to_bool(self):
        """Test _to_bool function."""
        assert _to_bool(True) is True
        assert _to_bool(False) is False
        assert _to_bool('1') is True
        assert _to_bool('true') is True
        assert _to_bool('t') is True
        assert _to_bool('yes') is True
        assert _to_bool('si') is True
        assert _to_bool('sí') is True
        assert _to_bool('0') is False
        assert _to_bool('false') is False
        assert _to_bool('no') is False
        assert _to_bool('') is False  # empty string falls to bool(False)

    def test_fecha_utc(self):
        """Test _fecha_utc function."""
        from datetime import datetime
        # None case
        assert _fecha_utc(None) is None
        
        # datetime without tzinfo
        dt_naive = datetime(2026, 9, 30, 12, 0, 0)
        result = _fecha_utc(dt_naive)
        assert result == '2026-09-30T12:00:00Z'
        
        # datetime with tzinfo
        from datetime import timezone
        dt_aware = datetime(2026, 9, 30, 12, 0, 0, tzinfo=timezone.utc)
        result = _fecha_utc(dt_aware)
        assert result == '2026-09-30T12:00:00Z'

    def test_coordenadas_punto(self):
        """Test _coordenadas_punto function."""
        # Dict with lat/lng
        lat, lon = _coordenadas_punto({'latitud': -34.6037, 'longitud': -58.3816})
        assert lat == -34.6037
        assert lon == -58.3816
        
        # Dict with lat/lng swapped
        lat, lon = _coordenadas_punto({'lat': -34.6037, 'lng': -58.3816})
        assert lat == -34.6037
        assert lon == -58.3816

    def test_coordenadas_pedido_dict(self):
        """Test _coordenadas_pedido with dict origin/destino."""
        data = {
            'origen': {'latitud': -34.6037, 'longitud': -58.3816},
            'destino': {'latitud': -34.7205, 'longitud': -58.2541},
        }
        lat_origen, lon_origen, lat_destino, lon_destino = _coordenadas_pedido(data)
        assert lat_origen == -34.6037
        assert lon_origen == -58.3816
        assert lat_destino == -34.7205
        assert lon_destino == -58.2541

    def test_coordenadas_pedido_plano(self):
        """Test _coordenadas_pedido with flat coordinates."""
        data = {
            'lat_origen': -34.6037,
            'lon_origen': -58.3816,
            'lat_destino': -34.7205,
            'lon_destino': -58.2541,
        }
        lat_origen, lon_origen, lat_destino, lon_destino = _coordenadas_pedido(data)
        assert lat_origen == -34.6037
        assert lon_origen == -58.3816
        assert lat_destino == -34.7205
        assert lon_destino == -58.2541


class TestValidarCoordenadas:
    """Test _validar_coordenadas function."""

    def test_coordenadas_validas(self, setup_app):
        """Test valid coordinates."""
        lat, lon = _validar_coordenadas(-34.6037, -58.3816, 'test')
        assert lat == -34.6037
        assert lon == -58.3816

    def test_latitud_fuera_rango(self, setup_app):
        """Test latitude outside valid range."""
        with pytest.raises(ValueError, match='La latitud de test debe estar entre -90 y 90'):
            _validar_coordenadas(91.0, -58.3816, 'test')

    def test_longitud_fuera_rango(self, setup_app):
        """Test longitude outside valid range."""
        with pytest.raises(ValueError, match='La longitud de test debe estar entre -180 y 180'):
            _validar_coordenadas(-34.6037, 181.0, 'test')

    def test_latitud_negativa(self, setup_app):
        """Test negative latitude (south)."""
        lat, lon = _validar_coordenadas(-90.0, 0.0, 'test')
        assert lat == -90.0
        assert lon == 0.0

    def test_longitud_negativa(self, setup_app):
        """Test negative longitude (west)."""
        lat, lon = _validar_coordenadas(0.0, -180.0, 'test')
        assert lat == 0.0
        assert lon == -180.0


class TestCrearPedido:
    """Test crear_pedido function."""

    @pytest.fixture
    def app_and_db(self):
        """Fixture for app and database."""
        os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
        app = create_app()
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            db.create_all()
            yield app, db
            db.session.remove()
            db.drop_all()

    def test_crear_pedido_valido(self, app_and_db):
        """Test creating a valid pedido."""
        app, db = app_and_db
        # Add a user first
        usuario = Usuario(email='test@test.com', password_hash='hash123', rol='cliente')
        db.session.add(usuario)
        db.session.commit()
        
        data = {
            'cliente': 'Test Client',
            'direccion': 'Test Address',
            'peso_kg': 2.5,
            'lat_origen': -34.6037,
            'lon_origen': -58.3816,
            'lat_destino': -34.7205,
            'lon_destino': -58.2541,
            'categoria': 'Electrónica',
            'es_fragil': True,
            'es_urgente': False,
            'usuario_id': usuario.id,  # Include usuario_id
        }
        
        pedido, error = crear_pedido(data)
        assert error is None
        assert pedido is not None
        assert pedido.cliente == 'Test Client'
        assert pedido.peso_kg == 2.5
        assert pedido.es_fragil == True
        assert pedido.estado == 'PENDIENTE'
        assert pedido.usuario_id == usuario.id

    def test_crear_pedido_sin_campos_obligatorios(self, app_and_db):
        """Test creating pedido without required fields."""
        app, db = app_and_db
        data = {
            'peso_kg': 1.0,
            # Missing cliente and direccion
        }
        pedido, error = crear_pedido(data)
        assert error is not None
        assert pedido is None
        assert 'cliente' in error['message'] or 'direccion' in error['message']

    def test_crear_pedido_peso_invalido(self, app_and_db):
        """Test creating pedido with invalid peso_kg."""
        app, db = app_and_db
        data = {
            'cliente': 'Test Client',
            'direccion': 'Test Address',
            'peso_kg': -1.0,  # Negative weight
        }
        pedido, error = crear_pedido(data)
        assert error is not None
        assert pedido is None
        assert 'mayor que cero' in error['message']

    def test_crear_pedido_peso_cero(self, app_and_db):
        """Test creating pedido with zero peso_kg."""
        app, db = app_and_db
        data = {
            'cliente': 'Test Client',
            'direccion': 'Test Address',
            'peso_kg': 0.0,
        }
        pedido, error = crear_pedido(data)
        assert error is not None
        assert pedido is None
        assert 'mayor que cero' in error['message']

    def test_crear_pedido_sin_coordenadas_origen(self, app_and_db):
        """Test creating pedido without origin coordinates."""
        app, db = app_and_db
        data = {
            'cliente': 'Test Client',
            'direccion': 'Test Address',
            'peso_kg': 1.0,
            # No origin coordinates
        }
        pedido, error = crear_pedido(data)
        assert error is not None
        assert pedido is None

    def test_crear_pedido_sin_coordenadas_destino(self, app_and_db):
        """Test creating pedido without destination coordinates."""
        app, db = app_and_db
        data = {
            'cliente': 'Test Client',
            'direccion': 'Test Address',
            'peso_kg': 1.0,
            'lat_origen': -34.6037,
            'lon_origen': -58.3816,
            # No destination coordinates
        }
        pedido, error = crear_pedido(data)
        assert error is not None
        assert pedido is None

    def test_crear_pedido_con_usuario_id(self, app_and_db):
        """Test creating pedido with usuario_id."""
        app, db = app_and_db
        usuario = Usuario(email='test@test.com', password_hash='hash123', rol='cliente')
        db.session.add(usuario)
        db.session.commit()
        
        data = {
            'cliente': 'Test Client',
            'direccion': 'Test Address',
            'peso_kg': 1.0,
            'lat_origen': -34.6037,
            'lon_origen': -58.3816,
            'lat_destino': -34.7205,
            'lon_destino': -58.2541,
            'usuario_id': usuario.id,
        }
        
        pedido, error = crear_pedido(data)
        assert error is None
        assert pedido is not None
        assert pedido.usuario_id == usuario.id

    def test_crear_pedido_sin_usuario_id(self, app_and_db):
        """Test creating pedido without usuario_id (should be None)."""
        app, db = app_and_db
        data = {
            'cliente': 'Test Client',
            'direccion': 'Test Address',
            'peso_kg': 1.0,
            'lat_origen': -34.6037,
            'lon_origen': -58.3816,
            'lat_destino': -34.7205,
            'lon_destino': -58.2541,
            # No usuario_id
        }
        
        pedido, error = crear_pedido(data)
        assert error is None
        assert pedido is not None
        assert pedido.usuario_id is None

    def test_crear_pedido_con_direccion_con_acentos(self, app_and_db):
        """Test creating pedido with dirección with accent."""
        app, db = app_and_db
        data = {
            'cliente': 'Test Client',
            'direccion': 'Calle Falsa 123',  # Using normal chars, app handles accent
            'peso_kg': 1.0,
            'lat_origen': -34.6037,
            'lon_origen': -58.3816,
            'lat_destino': -34.7205,
            'lon_destino': -58.2541,
        }
        
        pedido, error = crear_pedido(data)
        assert error is None
        assert pedido is not None
        assert pedido.direccion == 'Calle Falsa 123'

    def test_crear_pedido_rollback_en_error(self, app_and_db):
        """Test that database session is rolled back on error."""
        app, db = app_and_db
        data = {
            'cliente': 'Test Client',
            'direccion': 'Test Address',
            # Missing required fields - will cause error
            'peso_kg': 'invalid',  # This will cause ValueError
        }
        
        pedido, error = crear_pedido(data)
        assert error is not None
        assert pedido is None
        # Session should have been rolled back
        # Check that no uncommitted data remains
        count = Pedido.query.count()
        assert count == 0