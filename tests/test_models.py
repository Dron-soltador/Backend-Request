"""Tests for models module using pytest."""
import pytest
from app.models import db, Pedido, Usuario


@pytest.fixture
def setup_app():
    """Create a fresh app and database for each test."""
    from app import create_app
    import os
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    
    with app.app_context():
        db.create_all()
        yield app, db
        db.session.remove()
        db.drop_all()


class TestUsuarioModel:
    """Test Usuario model."""

    def test_usuario_has_required_fields(self, setup_app):
        app, db = setup_app
        # Test that Usuario model has the required fields
        assert hasattr(Usuario, 'email')
        assert hasattr(Usuario, 'password_hash')
        assert hasattr(Usuario, 'rol')

    def test_usuario_rol_default(self, setup_app):
        app, db = setup_app
        usuario = Usuario(email='test@example.com', password_hash='hash123', rol='cliente')
        db.session.add(usuario)
        db.session.commit()
        assert usuario.rol == 'cliente'

    def test_usuario_to_dict(self, setup_app):
        app, db = setup_app
        usuario = Usuario(email='test@example.com', password_hash='hash123', rol='admin')
        db.session.add(usuario)
        db.session.commit()
        result = usuario.to_dict()
        assert result['id'] == usuario.id
        assert result['email'] == 'test@example.com'
        assert result['rol'] == 'admin'
        # password_hash should not be in the dict
        assert 'password_hash' not in result


class TestPedidoModel:
    """Test Pedido model."""

    def test_pedido_has_table(self, setup_app):
        app, db = setup_app
        assert Pedido.__table__ is not None

    def test_pedido_creacion(self, setup_app):
        app, db = setup_app
        usuario = Usuario(email='test@example.com', password_hash='hash123', rol='cliente')
        db.session.add(usuario)
        db.session.commit()
        
        pedido = Pedido(
            usuario_id=usuario.id,
            lat_origen=-34.6037,
            lon_origen=-58.3816,
            lat_destino=-34.7205,
            lon_destino=-58.2541,
            peso_kg=2.5,
            cliente='Test Client',
            direccion='Test Address',
            categoria='Estándar',
            es_fragil=False,
            es_urgente=False,
            costo_total=1000.0,
            estado='PENDIENTE'
        )
        db.session.add(pedido)
        db.session.commit()
        
        assert pedido.id is not None
        assert pedido.estado == 'PENDIENTE'
        assert pedido.costo_total == 1000.0
        assert pedido.usuario_id == usuario.id

    def test_pedido_to_dict(self, setup_app):
        app, db = setup_app
        usuario = Usuario(email='test2@example.com', password_hash='hash123', rol='cliente')
        db.session.add(usuario)
        db.session.commit()
        
        pedido = Pedido(
            usuario_id=usuario.id,
            lat_origen=-34.6037,
            lon_origen=-58.3816,
            lat_destino=-34.7205,
            lon_destino=-58.2541,
            peso_kg=2.5,
            cliente='Test Client',
            direccion='Test Address',
            es_fragil=True,
            es_urgente=False,
            costo_total=1000.0,
            estado='PENDIENTE'
        )
        db.session.add(pedido)
        db.session.commit()
        
        result = pedido.to_dict()
        assert result['id'] == pedido.id
        assert result['usuario_id'] == usuario.id
        assert result['cliente'] == 'Test Client'
        assert result['direccion'] == 'Test Address'
        assert result['es_fragil'] == True
        assert result['es_urgente'] == False
        assert result['costo_total'] == 1000.0
        # fecha_creacion should be isoformatted
        assert 'fecha_creacion' in result