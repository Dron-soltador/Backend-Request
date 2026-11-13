"""Tests adicionales de las rutas HTTP de pedidos.

Cubren los caminos de error y los endpoints que no ejercitaban los tests
existentes: cotización, detalle, estado y notificación.
"""

import os
from unittest.mock import patch

import pytest

from app import create_app
from app.models import db, Pedido


PAYLOAD = {
    'cliente': 'Laura Giménez',
    'direccion': 'Av. San Martín 450',
    'peso_kg': 1.5,
    'es_fragil': True,
    'es_urgente': False,
    'origen': {'latitud': -34.6037, 'longitud': -58.3816},
    'destino': {'latitud': -34.7205, 'longitud': -58.2541},
}


@pytest.fixture
def app_client():
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    app.config['TESTING'] = True
    app.config['WTF_CSRF_ENABLED'] = False

    with app.app_context():
        db.create_all()
        yield app, app.test_client()
        db.session.remove()
        db.drop_all()


def _crear_pedido(client, **cambios):
    payload = dict(PAYLOAD)
    payload.update(cambios)
    with patch(
        'app.pedidos.notificar_pedido_al_despachador',
        return_value={'exito': True},
    ):
        return client.post('/api/v1/pedidos', json=payload)


def _pedido_de_prueba(**cambios):
    datos = {
        'lat_origen': -34.6037,
        'lon_origen': -58.3816,
        'lat_destino': -34.7205,
        'lon_destino': -58.2541,
        'peso_kg': 2.5,
        'cliente': 'Cliente',
        'direccion': 'Dirección',
        'estado': 'PENDIENTE',
    }
    datos.update(cambios)
    pedido = Pedido(**datos)
    db.session.add(pedido)
    db.session.commit()
    return pedido


class TestCotizar:
    def test_cotiza_pedido_valido(self, app_client):
        _, client = app_client
        response = client.post('/api/v1/pedidos/cotizar', json=PAYLOAD)

        assert response.status_code == 200
        body = response.get_json()
        assert body['cotizacion']['costo_total'] > 0

    def test_rechaza_peso_faltante(self, app_client):
        _, client = app_client
        payload = dict(PAYLOAD)
        payload.pop('peso_kg')

        response = client.post('/api/v1/pedidos/cotizar', json=payload)

        assert response.status_code == 400
        assert 'peso_kg' in response.get_json()['message']

    def test_rechaza_peso_invalido(self, app_client):
        _, client = app_client
        response = client.post(
            '/api/v1/pedidos/cotizar', json=dict(PAYLOAD, peso_kg='pesado')
        )

        assert response.status_code == 400

    def test_rechaza_coordenadas_fuera_de_rango(self, app_client):
        _, client = app_client
        payload = dict(PAYLOAD, origen={'latitud': 100, 'longitud': 0})

        response = client.post('/api/v1/pedidos/cotizar', json=payload)

        assert response.status_code == 400

    def test_rechaza_cuerpo_que_no_es_objeto(self, app_client):
        _, client = app_client
        response = client.post('/api/v1/pedidos/cotizar', json=[1])

        assert response.status_code == 400

    def test_error_interno_al_cotizar(self, app_client):
        _, client = app_client
        with patch(
            'app.routes.api.pedidos.cotizar_desde_payload',
            side_effect=RuntimeError('boom'),
        ):
            response = client.post('/api/v1/pedidos/cotizar', json=PAYLOAD)

        assert response.status_code == 500


class TestCrearPedidoErrores:
    def test_rechaza_cuerpo_que_no_es_objeto(self, app_client):
        _, client = app_client
        response = client.post('/api/v1/pedidos', json=[1])

        assert response.status_code == 400

    def test_devuelve_500_si_el_servicio_falla(self, app_client):
        _, client = app_client
        with patch(
            'app.routes.api.pedidos.crear_pedido',
            return_value=(None, {'code': 500, 'message': 'boom'}),
        ):
            response = client.post('/api/v1/pedidos', json=PAYLOAD)

        assert response.status_code == 500

    def test_notificacion_con_error_generico(self, app_client):
        _, client = app_client
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            side_effect=RuntimeError('sin red'),
        ):
            response = client.post('/api/v1/pedidos', json=PAYLOAD)

        assert response.status_code == 502
        body = response.get_json()
        assert body['notificacion']['exito'] is False


class TestConsultasPedido:
    def test_obtiene_detalle_por_id(self, app_client):
        _, client = app_client
        pedido = _pedido_de_prueba()

        response = client.get(f'/api/v1/pedidos/{pedido.id}')

        assert response.status_code == 200
        assert response.get_json()['id'] == pedido.id

    def test_detalle_inexistente(self, app_client):
        _, client = app_client
        assert client.get('/api/v1/pedidos/9999').status_code == 404

    def test_estado_inexistente(self, app_client):
        _, client = app_client
        response = client.get('/api/v1/pedidos/9999/estado')
        assert response.status_code == 404

    def test_notificacion_fallida_devuelve_500(self, app_client):
        _, client = app_client
        pedido = _pedido_de_prueba()
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            side_effect=RuntimeError('sin red'),
        ):
            response = client.post(
                f'/api/v1/pedidos/{pedido.id}/notificar-despacho'
            )

        assert response.status_code == 500

    def test_estado_invalido(self, app_client):
        _, client = app_client
        pedido = _pedido_de_prueba()

        response = client.put(
            f'/api/v1/pedidos/{pedido.id}/estado',
            json={'estado': 'VOLANDO'},
        )

        assert response.status_code == 400

    def test_actualizar_estado_inexistente(self, app_client):
        _, client = app_client

        response = client.put(
            '/api/v1/pedidos/9999/estado', json={'estado': 'EN_CAMINO'}
        )

        assert response.status_code == 404

    def test_error_al_guardar_estado(self, app_client):
        _, client = app_client
        pedido = _pedido_de_prueba()

        with patch(
            'app.routes.api.pedidos.db.session.commit',
            side_effect=RuntimeError('boom'),
        ):
            response = client.put(
                f'/api/v1/pedidos/{pedido.id}/estado',
                json={'estado': 'EN_CAMINO'},
            )

        assert response.status_code == 500


class TestCompatibilidad:
    def test_modulo_auth_reexporta_el_blueprint(self):
        from app.auth import auth_bp
        from app.routes.api.auth import auth_bp as auth_bp_activo

        assert auth_bp is auth_bp_activo
