"""Tests del orquestador de despacho (app.despachador)."""

from unittest.mock import MagicMock, patch

import pytest
from flask import Flask

from app import despachador


def _respuesta(status=200, texto='ok'):
    respuesta = MagicMock()
    respuesta.status_code = status
    respuesta.text = texto
    return respuesta


@pytest.fixture
def client():
    app = Flask(__name__)
    app.config['TESTING'] = True
    app.register_blueprint(despachador.despacho_bp)
    return app.test_client()


def _despachar(client, **cambios):
    payload = {'pedido_id': 1, 'dron_id': 2}
    payload.update(cambios)
    return client.post('/despacho/despachar', json=payload)


class TestDespachador:
    def test_rechaza_campos_faltantes(self, client):
        assert _despachar(client, pedido_id=None).status_code == 400
        assert _despachar(client, dron_id=None).status_code == 400

    def test_despacho_exitoso(self, client):
        with patch.object(
            despachador.requests, 'put', return_value=_respuesta()
        ) as put:
            response = _despachar(client)

        assert response.status_code == 200
        body = response.get_json()
        assert body['estado_pedido'] == 'EN_CAMINO'
        assert body['estado_dron'] == 'EN_MISION'
        assert put.call_count == 2

    def test_falla_el_servicio_de_drones(self, client):
        with patch.object(
            despachador.requests,
            'put',
            return_value=_respuesta(500, 'error'),
        ):
            response = _despachar(client)

        assert response.status_code == 500
        assert 'Drones' in response.get_json()['message']

    def test_falla_el_pedido_y_revierte_el_dron(self, client):
        with patch.object(
            despachador.requests,
            'put',
            side_effect=[_respuesta(), _respuesta(500, 'error'), _respuesta()],
        ) as put:
            response = _despachar(client)

        assert response.status_code == 500
        assert put.call_count == 3
        assert put.call_args_list[-1].kwargs['json'] == {
            'estado': 'DISPONIBLE'
        }

    def test_error_de_conexion_al_actualizar_dron(self, client):
        with patch.object(
            despachador.requests, 'put', side_effect=Exception('sin red')
        ):
            response = _despachar(client)

        assert response.status_code == 500

    def test_error_al_revertir_el_dron(self, client):
        with patch.object(
            despachador.requests,
            'put',
            side_effect=[
                _respuesta(),
                _respuesta(500, 'error'),
                Exception('sin red'),
            ],
        ):
            response = _despachar(client)

        assert response.status_code == 500
