"""Tests for pedidos routes using pytest."""
import os
import pytest
from datetime import datetime
from unittest.mock import patch
from app import create_app
from app.models import db, Pedido
from app.routes.api.pedidos import pedidos_bp


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


class TestPedidosRoutes:
    """Test pedidos API routes."""

    @pytest.fixture
    def client(self, setup_app):
        app, db = setup_app
        client = app.test_client()
        return client

    def test_registra_y_notifica_pedido_nuevo(self, client):
        """Test POST /api/v1/pedidos registers and notifies."""
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            return_value={'exito': True, 'status_code': 200},
        ) as notificar:
            response = client.post(
                '/api/v1/pedidos', json={
                    'cliente': 'Laura Giménez',
                    'direccion': 'Av. San Martín 450',
                    'peso_kg': 1.5,
                    'es_fragil': True,
                    'es_urgente': False,
                    'origen': {
                        'latitud': -34.6037,
                        'longitud': -58.3816,
                    },
                    'destino': {
                        'latitud': -34.7205,
                        'longitud': -58.2541,
                    },
                }
            )
        
        assert response.status_code == 201
        body = response.get_json()
        assert body['notificacion']['exito'] is True
        notificar.assert_called_once_with(body['pedido']['id'])

    def test_conserva_pedido_si_falla_la_notificacion(self, client):
        """Test that pedido is saved even if notification fails."""
        from app.integracion import IntegracionRemotaError
        error = IntegracionRemotaError(
            'despachador no disponible', status_code=503
        )
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            side_effect=error,
        ):
            response = client.post(
                '/api/v1/pedidos', json={
                    'cliente': 'Laura Giménez',
                    'direccion': 'Av. San Martín 450',
                    'peso_kg': 1.5,
                    'es_fragil': True,
                    'es_urgente': False,
                    'origen': {
                        'latitud': -34.6037,
                        'longitud': -58.3816,
                    },
                    'destino': {
                        'latitud': -34.7205,
                        'longitud': -58.2541,
                    },
                }
            )
        
        assert response.status_code == 502
        body = response.get_json()
        assert body['pedido']['estado'] == 'PENDIENTE'
        # When notification fails, the response doesn't include 'notificacion' key
        # but the pedido is still created with PENDIENTE state

    def test_reintenta_notificacion_del_mismo_pedido(self, client):
        """Test re-notification of a pedido."""
        # Create a pedido first
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            return_value={'exito': True},
        ) as notificar:
            response = client.post(
                '/api/v1/pedidos', json={
                    'cliente': 'Laura Giménez',
                    'direccion': 'Av. San Martín 450',
                    'peso_kg': 1.5,
                    'es_fragil': True,
                    'es_urgente': False,
                    'origen': {
                        'latitud': -34.6037,
                        'longitud': -58.3816,
                    },
                    'destino': {
                        'latitud': -34.7205,
                        'longitud': -58.2541,
                    },
                }
            )
            pedido_id = response.get_json()['pedido']['id']
        
        # Now try to re-notify (mocked as well)
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            return_value={'exito': True},
        ) as notificar2:
            response = client.post(
                f'/api/v1/pedidos/{pedido_id}/notificar-despacho'
            )

        assert response.status_code == 200
        notificar2.assert_called_once_with(pedido_id)

    def test_rechaza_pedido_sin_coordenadas(self, client):
        """Test that pedido is rejected without coordinates."""
        response = client.post('/api/v1/pedidos', json={
            'cliente': 'Laura Giménez',
            'direccion': 'Av. San Martín 450',
            'peso_kg': 1.5,
        })
        
        assert response.status_code == 400
        body = response.get_json()
        assert 'origen' in body['message']

    def test_lista_solo_los_campos_del_despachador(self, client):
        """Test that /para-despachador only exposes allowed fields."""
        # Create a pedido
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            return_value={'exito': True},
        ):
            client.post(
                '/api/v1/pedidos', json={
                    'cliente': 'Laura Giménez',
                    'direccion': 'Av. San Martín 450',
                    'peso_kg': 1.5,
                    'es_fragil': True,
                    'es_urgente': False,
                    'origen': {
                        'latitud': -34.6037,
                        'longitud': -58.3816,
                    },
                    'destino': {
                        'latitud': -34.7205,
                        'longitud': -58.2541,
                    },
                }
            )
        
        response = client.get('/api/v1/pedidos/para-despachador')
        assert response.status_code == 200
        body = response.get_json()
        assert len(body) == 1
        allowed_keys = {
            'id', 'peso_kg', 'es_urgente', 'fecha_creacion',
            'es_fragil', 'origen', 'destino'
        }
        assert set(body[0].keys()) == allowed_keys
        assert 'categoria' not in body[0]
        assert 'costo_total' not in body[0]
        assert 'cliente' not in body[0]
        assert 'direccion' not in body[0]

    def test_no_existe_listado_de_pedidos_pendientes(self, client):
        """Test that /pendientes returns 404 (not implemented)."""
        response = client.get('/api/v1/pedidos/pendientes')
        assert response.status_code == 404

    def test_obtiene_un_pedido_para_despachador(self, client):
        """Test GET /api/v1/pedidos/para-despachador/:id"""
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            return_value={'exito': True},
        ):
            client.post(
                '/api/v1/pedidos', json={
                    'cliente': 'Laura Giménez',
                    'direccion': 'Av. San Martín 450',
                    'peso_kg': 1.5,
                    'es_fragil': True,
                    'es_urgente': False,
                    'origen': {
                        'latitud': -34.6037,
                        'longitud': -58.3816,
                    },
                    'destino': {
                        'latitud': -34.7205,
                        'longitud': -58.2541,
                    },
                }
            )
        
        # Get the created pedido ID from the database
        pedido = db.session.query(Pedido).first()
        assert pedido is not None
        
        # Test getting a specific pedido for despachador
        response = client.get(
            f'/api/v1/pedidos/para-despachador/{pedido.id}'
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body['id'] == pedido.id
        
        # Test non-existent pedido
        response = client.get('/api/v1/pedidos/para-despachador/9999')
        assert response.status_code == 404

    def test_usuario_consulta_estado_local(self, client):
        """Test GET /api/v1/pedidos/:id/estado"""
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            return_value={'exito': True},
        ):
            client.post(
                '/api/v1/pedidos', json={
                    'cliente': 'Laura Giménez',
                    'direccion': 'Av. San Martín 450',
                    'peso_kg': 1.5,
                    'es_fragil': True,
                    'es_urgente': False,
                    'origen': {
                        'latitud': -34.6037,
                        'longitud': -58.3816,
                    },
                    'destino': {
                        'latitud': -34.7205,
                        'longitud': -58.2541,
                    },
                }
            )
        
        # Create pedido with EN_CAMINO state
        pedido = db.session.query(Pedido).first()
        pedido.estado = 'EN_CAMINO'
        db.session.commit()
        
        response = client.get(
            f'/api/v1/pedidos/{pedido.id}/estado'
        )
        assert response.status_code == 200
        body = response.get_json()
        assert body['pedido_id'] == pedido.id
        assert body['estado'] == 'EN_CAMINO'

    def test_administrador_actualiza_estado(self, client):
        """Test PUT /api/v1/pedidos/:id/estado"""
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            return_value={'exito': True},
        ):
            client.post(
                '/api/v1/pedidos', json={
                    'cliente': 'Laura Giménez',
                    'direccion': 'Av. San Martín 450',
                    'peso_kg': 1.5,
                    'es_fragil': True,
                    'es_urgente': False,
                    'origen': {
                        'latitud': -34.6037,
                        'longitud': -58.3816,
                    },
                    'destino': {
                        'latitud': -34.7205,
                        'longitud': -58.2541,
                    },
                }
            )
        
        # Update estado
        response = client.put(
            f'/api/v1/pedidos/1/estado',
            json={'estado': 'EN_CAMINO'}
        )
        
        assert response.status_code == 200
        body = response.get_json()
        assert body['pedido']['estado'] == 'EN_CAMINO'

    def test_obtiene_pedido_por_usuario(self, client):
        """Test GET /api/v1/pedidos/usuario/:usuario_id"""
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            return_value={'exito': True},
        ):
            # Create a user and pedido with usuario_id
            from app.models import Usuario
            user = Usuario(email='test@test.com', password_hash='hash123', rol='cliente')
            db.session.add(user)
            db.session.commit()
            
            client.post(
                '/api/v1/pedidos', json={
                    'cliente': 'Laura Giménez',
                    'direccion': 'Av. San Martín 450',
                    'peso_kg': 1.5,
                    'es_fragil': True,
                    'es_urgente': False,
                    'origen': {
                        'latitud': -34.6037,
                        'longitud': -58.3816,
                    },
                    'destino': {
                        'latitud': -34.7205,
                        'longitud': -58.2541,
                    },
                    'usuario_id': user.id,
                }
            )
        
        # Get usuario_id from the created pedido
        pedido = db.session.query(Pedido).first()
        response = client.get(
            f'/api/v1/pedidos/usuario/{pedido.usuario_id}'
        )
        assert response.status_code == 200
        body = response.get_json()
        assert len(body) == 1
        assert body[0]['cliente'] == 'Laura Giménez'