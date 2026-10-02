import unittest
from datetime import datetime
from unittest.mock import patch

from flask import Flask

from app.integracion import IntegracionRemotaError
from app.models import db, Pedido
from app.pedidos import pedidos_bp


class TestPedidosParaDespachador(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config.update(
            TESTING=True,
            SQLALCHEMY_DATABASE_URI='sqlite:///:memory:',
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
        )
        db.init_app(self.app)
        self.app.register_blueprint(pedidos_bp)

        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        self.client = self.app.test_client()

    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()

    def _crear_pedido(self, **cambios):
        datos = {
            'usuario_id': None,
            'lat_origen': -34.6037,
            'lon_origen': -58.3816,
            'lat_destino': -34.7205,
            'lon_destino': -58.2541,
            'peso_kg': 2.5,
            'cliente': 'Cliente que no se publica',
            'direccion': 'Dirección que no se publica',
            'categoria': 'Electrónica',
            'es_fragil': True,
            'es_urgente': False,
            'costo_total': 4125.0,
            'fecha_programada': None,
            'estado': 'PENDIENTE',
            'fecha_creacion': datetime(2026, 9, 30, 12, 0, 0),
        }
        datos.update(cambios)
        pedido = Pedido(**datos)
        db.session.add(pedido)
        db.session.commit()
        return pedido

    def _payload_pedido(self):
        return {
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

    def test_registra_y_notifica_pedido_nuevo(self):
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            return_value={'exito': True, 'status_code': 200},
        ) as notificar:
            response = self.client.post(
                '/api/v1/pedidos', json=self._payload_pedido()
            )

        self.assertEqual(response.status_code, 201)
        body = response.get_json()
        self.assertTrue(body['notificacion']['exito'])
        self.assertEqual(body['pedido']['lat_origen'], -34.6037)
        notificar.assert_called_once_with(body['pedido']['id'])

    def test_conserva_pedido_si_falla_la_notificacion(self):
        error = IntegracionRemotaError(
            'despachador no disponible', status_code=503
        )
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            side_effect=error,
        ):
            response = self.client.post(
                '/api/v1/pedidos', json=self._payload_pedido()
            )

        self.assertEqual(response.status_code, 502)
        body = response.get_json()
        self.assertEqual(body['pedido']['estado'], 'PENDIENTE')
        self.assertFalse(body['notificacion']['exito'])

    def test_reintenta_notificacion_del_mismo_pedido(self):
        pedido = self._crear_pedido()
        with patch(
            'app.pedidos.notificar_pedido_al_despachador',
            return_value={'exito': True},
        ) as notificar:
            response = self.client.post(
                f'/api/v1/pedidos/{pedido.id}/notificar-despacho'
            )

        self.assertEqual(response.status_code, 200)
        notificar.assert_called_once_with(pedido.id)

    def test_rechaza_pedido_sin_coordenadas(self):
        response = self.client.post('/api/v1/pedidos', json={
            'cliente': 'Laura Giménez',
            'direccion': 'Av. San Martín 450',
            'peso_kg': 1.5,
        })

        self.assertEqual(response.status_code, 400)
        self.assertIn('origen', response.get_json()['message'])

    def test_lista_solo_los_campos_del_despachador(self):
        pedido = self._crear_pedido()

        response = self.client.get('/api/v1/pedidos/para-despachador')

        self.assertEqual(response.status_code, 200)
        body = response.get_json()
        self.assertEqual(len(body), 1)
        self.assertEqual(set(body[0].keys()), {
            'id',
            'peso_kg',
            'es_urgente',
            'fecha_creacion',
            'es_fragil',
            'origen',
            'destino',
        })
        self.assertEqual(body[0]['id'], pedido.id)
        self.assertEqual(body[0]['fecha_creacion'], '2026-09-30T12:00:00Z')
        self.assertNotIn('categoria', body[0])
        self.assertNotIn('costo_total', body[0])
        self.assertNotIn('cliente', body[0])
        self.assertNotIn('direccion', body[0])

    def test_no_existe_listado_de_pedidos_pendientes(self):
        response = self.client.get('/api/v1/pedidos/pendientes')
        self.assertEqual(response.status_code, 404)

    def test_obtiene_un_pedido_para_despachador(self):
        pedido = self._crear_pedido()

        encontrado = self.client.get(
            f'/api/v1/pedidos/para-despachador/{pedido.id}'
        )
        inexistente = self.client.get(
            '/api/v1/pedidos/para-despachador/9999'
        )

        self.assertEqual(encontrado.status_code, 200)
        self.assertEqual(encontrado.get_json()['id'], pedido.id)
        self.assertEqual(inexistente.status_code, 404)

    def test_usuario_consulta_estado_local(self):
        pedido = self._crear_pedido(estado='EN_CAMINO')

        response = self.client.get(
            f'/api/v1/pedidos/{pedido.id}/estado'
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json(), {
            'pedido_id': pedido.id,
            'estado': 'EN_CAMINO',
        })

    def test_administrador_actualiza_estado(self):
        pedido = self._crear_pedido()

        response = self.client.put(
            f'/api/v1/pedidos/{pedido.id}/estado',
            json={'estado': 'EN_CAMINO'},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()['pedido']['estado'], 'EN_CAMINO')


if __name__ == '__main__':
    unittest.main()
