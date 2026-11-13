"""Tests for integracion module using pytest."""
import os
import pytest
import requests
from unittest.mock import patch, MagicMock
from app import create_app
from app.models import db
from app.integracion import (
    notificar_pedido_al_despachador,
    IntegracionRemotaError,
)


@pytest.fixture
def app_fixture():
    """Create a fresh app for each test."""
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False
    app.config['DESPACHADOR_SERVICE_URL'] = 'http://192.168.220.131:5002'
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class TestNotificarPedidoAlDespachador:
    """Test notificar_pedido_al_despachador function."""

    def test_notifica_pedido_nuevo(self, app_fixture):
        """Test notifying new pedido to despachador with success response."""
        app = app_fixture
        with app.app_context():
            respuesta = {
                'exito': True,
                'mensaje': 'Pedido procesado exitosamente',
            }
            
            with patch('app.integracion.requests.post', return_value=MagicMock(
                status_code=200,
                json=lambda: respuesta,
                text=''
            )) as post:
                resultado = notificar_pedido_al_despachador(7)
                
                assert resultado['exito'] is True
                post.assert_called_once()
                # Check the URL
                call_args = post.call_args
                assert 'despachar' in call_args[0][0]
                # Check the payload
                kwargs = call_args[1]
                assert kwargs['json'] == {'pedido_id': 7}
                assert kwargs['headers']['Idempotency-Key'] == 'pedido-7'

    def test_incluye_token_cuando_esta_configurado(self, app_fixture):
        """Test that token is included when configured."""
        app = app_fixture
        app.config['REMOTE_API_TOKEN'] = 'token-de-prueba'
        
        with app.app_context():
            respuesta = {'exito': True}
            
            with patch('app.integracion.requests.post', return_value=MagicMock(
                status_code=200,
                json=lambda: respuesta,
                text=''
            )) as post:
                notificar_pedido_al_despachador(1)
                
                call_args = post.call_args
                headers = call_args[1]['headers']
                assert headers['Authorization'] == 'Bearer token-de-prueba'

    def test_propaga_error_del_despachador(self, app_fixture):
        """Test that dispatcher error is propagated."""
        app = app_fixture
        with app.app_context():
            respuesta = MagicMock(
                status_code=500,
                json=lambda: {'error': 'ERROR_INTERNO'},
                text='ERROR_INTERNO'
            )
            
            with patch('app.integracion.requests.post', return_value=respuesta):
                with pytest.raises(IntegracionRemotaError) as exc_info:
                    notificar_pedido_al_despachador(9)
                
                assert exc_info.value.status_code == 500
                assert exc_info.value.url is not None

    def test_informa_fallo_de_conexion(self, app_fixture):
        """Test that connection failure is informed."""
        app = app_fixture
        with app.app_context():
            with patch(
                'app.integracion.requests.post',
                side_effect=requests.RequestException('sin conexión')
            ):
                with pytest.raises(IntegracionRemotaError):
                    notificar_pedido_al_despachador(9)

    def test_timeout_configurado(self, app_fixture):
        """Test that timeout is configured properly."""
        app = app_fixture
        app.config['REMOTE_API_TIMEOUT'] = 10
        
        with app.app_context():
            with patch('app.integracion.requests.post', return_value=MagicMock(
                status_code=200,
                json=lambda: {'exito': True},
                text=''
            )) as post:
                notificar_pedido_al_despachador(1)
                # Timeout should be set in the call
                call_args = post.call_args
                assert call_args[1]['timeout'] == 10.0