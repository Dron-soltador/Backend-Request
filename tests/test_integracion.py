import unittest
from unittest.mock import patch

import requests
from flask import Flask

from app.integracion import (
    IntegracionRemotaError,
    notificar_pedido_al_despachador,
)


class FakeResponse:
    def __init__(self, status_code, data):
        self.status_code = status_code
        self._data = data
        self.text = str(data)

    def json(self):
        return self._data


class TestIntegracionDespachador(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            DESPACHADOR_SERVICE_URL='http://192.168.220.131:5002',
            REMOTE_API_TIMEOUT=2,
            REMOTE_API_TOKEN=None,
        )
        self.app_context = self.app.app_context()
        self.app_context.push()

    def tearDown(self):
        self.app_context.pop()

    def test_notifica_pedido_nuevo_al_despachador(self):
        respuesta = FakeResponse(200, {
            'exito': True,
            'mensaje': 'Pedido procesado exitosamente',
        })

        with patch(
            'app.integracion.requests.post', return_value=respuesta
        ) as post:
            resultado = notificar_pedido_al_despachador(7)

        self.assertTrue(resultado['exito'])
        self.assertEqual(
            post.call_args.args[0],
            'http://192.168.220.131:5002/despachar',
        )
        self.assertEqual(post.call_args.kwargs['json'], {'pedido_id': 7})
        self.assertEqual(
            post.call_args.kwargs['headers']['Idempotency-Key'],
            'pedido-7',
        )

    def test_incluye_token_cuando_esta_configurado(self):
        self.app.config['REMOTE_API_TOKEN'] = 'token-de-prueba'
        respuesta = FakeResponse(200, {'exito': True})

        with patch(
            'app.integracion.requests.post', return_value=respuesta
        ) as post:
            notificar_pedido_al_despachador(1)

        self.assertEqual(
            post.call_args.kwargs['headers']['Authorization'],
            'Bearer token-de-prueba',
        )

    def test_propaga_error_del_despachador(self):
        respuesta = FakeResponse(500, {'error': 'ERROR_INTERNO'})

        with patch('app.integracion.requests.post', return_value=respuesta):
            with self.assertRaises(IntegracionRemotaError) as context:
                notificar_pedido_al_despachador(9)

        self.assertEqual(context.exception.status_code, 500)

    def test_informa_fallo_de_conexion(self):
        with patch(
            'app.integracion.requests.post',
            side_effect=requests.RequestException('sin conexión'),
        ):
            with self.assertRaises(IntegracionRemotaError):
                notificar_pedido_al_despachador(9)


if __name__ == '__main__':
    unittest.main()
