"""Tests de cobertura para ramas auxiliares de servicios e integración."""

import os
from unittest.mock import MagicMock, patch

import pytest

from app import create_app
from app.integracion import (
    IntegracionRemotaError,
    _response_body,
    _timeout,
)
from app.models import db
from app.services.auth_service import AuthService
from app.services.pedido_service import (
    _coordenadas_punto,
    _parse_peso,
    _to_bool,
    crear_pedido,
)


@pytest.fixture
def app_ctx():
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


class TestIntegracionRamas:
    def test_timeout_invalido_usa_default(self, app_ctx):
        app_ctx.config['REMOTE_API_TIMEOUT'] = 'no-es-numero'
        assert _timeout() == 5.0

    def test_timeout_cero_usa_default(self, app_ctx):
        app_ctx.config['REMOTE_API_TIMEOUT'] = 0
        assert _timeout() == 5.0

    def test_response_body_texto_plano(self):
        respuesta = MagicMock()
        respuesta.json.side_effect = ValueError('sin json')
        respuesta.text = '  respuesta plana  '

        assert _response_body(respuesta) == 'respuesta plana'

    def test_response_body_vacio(self):
        respuesta = MagicMock()
        respuesta.json.side_effect = ValueError('sin json')
        respuesta.text = '   '

        assert _response_body(respuesta) is None

    def test_as_dict_de_error_remoto(self):
        error = IntegracionRemotaError(
            'falló', status_code=503, url='http://x', detalle={'a': 1}
        )

        assert error.as_dict() == {
            'exito': False,
            'mensaje': 'falló',
            'url': 'http://x',
            'status_code': 503,
            'detalle': {'a': 1},
        }


class TestAuthServiceRamas:
    def test_error_al_hashear_contrasena(self, app_ctx):
        hasher_roto = MagicMock()
        hasher_roto.hash.side_effect = Exception('boom')
        with patch('app.services.auth_service.ph', hasher_roto):
            result, error, status = AuthService.registrar(
                'nuevo@example.com', 'password123', 'cliente'
            )

        assert result is None
        assert status == 500
        assert error['message'] == 'Error al hashear la contraseña'


class TestPedidoServiceRamas:
    def test_to_bool_valores_no_booleanos(self):
        assert _to_bool(1) is True
        assert _to_bool(0) is False

    def test_coordenadas_punto_no_es_dict(self):
        assert _coordenadas_punto(None) == (None, None)

    def test_parse_peso_faltante(self):
        with pytest.raises(ValueError, match='peso_kg'):
            _parse_peso(None)

    def test_crear_pedido_con_direccion_acentuada(self, app_ctx):
        pedido, error = crear_pedido({
            'cliente': 'Cliente',
            'dirección': 'Calle Falsa 123',
            'peso_kg': 1.0,
            'lat_origen': -34.6037,
            'lon_origen': -58.3816,
            'lat_destino': -34.7205,
            'lon_destino': -58.2541,
        })

        assert error is None
        assert pedido.direccion == 'Calle Falsa 123'

    def test_crear_pedido_error_interno(self, app_ctx):
        with patch(
            'app.services.pedido_service.db.session.commit',
            side_effect=Exception('boom'),
        ):
            pedido, error = crear_pedido({
                'cliente': 'Cliente',
                'direccion': 'Calle Falsa 123',
                'peso_kg': 1.0,
                'lat_origen': -34.6037,
                'lon_origen': -58.3816,
                'lat_destino': -34.7205,
                'lon_destino': -58.2541,
            })

        assert pedido is None
        assert error['code'] == 500
