import unittest
from app.cotizador import calcular_distancia_haversine, calcular_cotizacion

class TestCotizador(unittest.TestCase):

    def test_distancia_haversine_buenos_aires(self):
        # Distancia aproximada entre Obelisco y Quilmes (~17 km)
        distancia = calcular_distancia_haversine(-34.6037, -58.3816, -34.7205, -58.2541)
        self.assertAlmostEqual(distancia, 17.5, delta=2.0)

    def test_recargos_fragil_y_urgente(self):
        # Mismas coordenadas (distancia 0 km), peso 1 kg
        res_base = calcular_cotizacion(0, 0, 0, 0, peso_kg=1.0, es_fragil=False, es_urgente=False)
        subtotal = res_base['desglose']['subtotal'] # 500 base + 200 peso = 700

        res_recargos = calcular_cotizacion(0, 0, 0, 0, peso_kg=1.0, es_fragil=True, es_urgente=True)
        recargo_fragil_esperado = subtotal * 0.15
        recargo_urgente_esperado = subtotal * 0.25
        
        self.assertEqual(res_recargos['desglose']['recargo_fragil'], recargo_fragil_esperado)
        self.assertEqual(res_recargos['desglose']['recargo_urgente'], recargo_urgente_esperado)
        self.assertEqual(res_recargos['costo_total'], subtotal + recargo_fragil_esperado + recargo_urgente_esperado)

if __name__ == '__main__':
    unittest.main()