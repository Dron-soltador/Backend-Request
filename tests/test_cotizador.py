"""Tests for cotizador service using pytest."""
import pytest
from app.cotizador import calcular_distancia_haversine, calcular_cotizacion


class TestCalcularDistanciaHarversine:
    """Test haversine distance calculation."""

    def test_distancia_buenos_aires_a_quilmes(self):
        """Test distance between Buenos Aires and Quilmes (~17 km)."""
        distancia = calcular_distancia_haversine(-34.6037, -58.3816, -34.7205, -58.2541)
        # Aproximadamente 17 km, tolerancia de 2 km
        assert abs(distancia - 17.5) < 2.0

    def test_distancia_mismo_punto(self):
        """Distance from a point to itself should be 0."""
        distancia = calcular_distancia_haversine(-34.6037, -58.3816, -34.6037, -58.3816)
        assert distancia == 0.0

    def test_distancia_meridiano(self):
        """Test distance along a meridian (same longitude)."""
        # Same latitude, 1 degree longitude at equator is ~111 km
        # At -34.6 degrees, 1 degree longitude is cos(34.6) * 111 km
        distancia = calcular_distancia_haversine(-34.6037, -58.3816, -34.6037, -57.3816)
        # Approx 111 * cos(34.6) ≈ 111 * 0.823 ≈ 91 km
        assert 80 < distancia < 100

    def test_distancia_paralelo(self):
        """Test distance along a parallel (same latitude)."""
        # 1 degree latitude is always ~111 km
        distancia = calcular_distancia_haversine(-34.6037, -58.3816, -35.6037, -58.3816)
        # Approx 111 km
        assert 100 < distancia < 120


class TestCalcularCotizacion:
    """Test cotizacion calculation."""

    def test_cotizacion_base_sin_recargos(self):
        """Test basic calculation without surcharges."""
        res = calcular_cotizacion(0, 0, 0, 0, peso_kg=1.0, es_fragil=False, es_urgente=False)
        # TARIFA_BASE=500, costo_peso=1*200=200, costo_distancia=0*150=0
        # subtotal=700, recargo_fragil=0, recargo_urgente=0
        # costo_total=700
        assert res['distancia_km'] == 0.0
        assert res['desglose']['tarifa_base'] == 500.0
        assert res['desglose']['costo_peso'] == 200.0
        assert res['desglose']['costo_distancia'] == 0.0
        assert res['desglose']['subtotal'] == 700.0
        assert res['desglose']['recargo_fragil'] == 0.0
        assert res['desglose']['recargo_urgente'] == 0.0
        assert res['costo_total'] == 700.0

    def test_cotizacion_con_peso(self):
        """Test calculation with weight."""
        res = calcular_cotizacion(0, 0, 0, 0, peso_kg=2.0, es_fragil=False, es_urgente=False)
        # subtotal = 500 + (2*200) + 0 = 900
        assert res['desglose']['costo_peso'] == 400.0
        assert res['costo_total'] == 900.0

    def test_cotizacion_con_distancia(self):
        """Test calculation with distance."""
        res = calcular_cotizacion(-34.6037, -58.3816, -34.7205, -58.2541, peso_kg=1.0, es_fragil=False, es_urgente=False)
        # distancia ~17 km, costo_distancia = 17*150 = 2550
        # subtotal = 500 + 200 + 2550 = 3250
        assert res['distancia_km'] > 0
        assert res['desglose']['costo_distancia'] > 0
        # subtotal should include distance cost
        assert res['desglose']['subtotal'] > 700.0

    def test_cotizacion_fragil(self):
        """Test fragile surcharge (15%)."""
        res_base = calcular_cotizacion(0, 0, 0, 0, peso_kg=1.0, es_fragil=False, es_urgente=False)
        subtotal = res_base['desglose']['subtotal']  # 700
        res_recargos = calcular_cotizacion(0, 0, 0, 0, peso_kg=1.0, es_fragil=True, es_urgente=False)
        recargo_fragil_esperado = round(subtotal * 0.15, 2)  # 105.0
        assert res_recargos['desglose']['recargo_fragil'] == recargo_fragil_esperado
        assert res_recargos['costo_total'] == round(subtotal + recargo_fragil_esperado, 2)

    def test_cotizacion_urgente(self):
        """Test urgent surcharge (25%)."""
        res_base = calcular_cotizacion(0, 0, 0, 0, peso_kg=1.0, es_fragil=False, es_urgente=False)
        subtotal = res_base['desglose']['subtotal']  # 700
        res_recargos = calcular_cotizacion(0, 0, 0, 0, peso_kg=1.0, es_fragil=False, es_urgente=True)
        recargo_urgente_esperado = round(subtotal * 0.25, 2)  # 175.0
        assert res_recargos['desglose']['recargo_urgente'] == recargo_urgente_esperado
        assert res_recargos['costo_total'] == round(subtotal + recargo_urgente_esperado, 2)

    def test_cotizacion_fragil_y_urgente(self):
        """Test both surcharges applied."""
        res_base = calcular_cotizacion(0, 0, 0, 0, peso_kg=1.0, es_fragil=False, es_urgente=False)
        subtotal = res_base['desglose']['subtotal']  # 700
        res_recargos = calcular_cotizacion(0, 0, 0, 0, peso_kg=1.0, es_fragil=True, es_urgente=True)
        recargo_fragil_esperado = round(subtotal * 0.15, 2)  # 105.0
        recargo_urgente_esperado = round(subtotal * 0.25, 2)  # 175.0
        expected_total = round(subtotal + recargo_fragil_esperado + recargo_urgente_esperado, 2)  # 980.0
        assert res_recargos['desglose']['recargo_fragil'] == recargo_fragil_esperado
        assert res_recargos['desglose']['recargo_urgente'] == recargo_urgente_esperado
        assert res_recargos['costo_total'] == expected_total

    def test_cotizacion_con_peso_y_distancia(self):
        """Test calculation with both weight and distance."""
        res = calcular_cotizacion(-34.6037, -58.3816, -34.7205, -58.2541, peso_kg=2.5, es_fragil=True, es_urgente=True)
        assert res['distancia_km'] > 0
        assert res['desglose']['costo_peso'] == 2.5 * 200.0  # 500
        assert res['desglose']['costo_distancia'] > 0
        assert res['desglose']['recargo_fragil'] == round(res['desglose']['subtotal'] * 0.15, 2)
        assert res['desglose']['recargo_urgente'] == round(res['desglose']['subtotal'] * 0.25, 2)
        # total = subtotal + fragil + urgente
        expected_total = round(res['desglose']['subtotal'] + res['desglose']['recargo_fragil'] + res['desglose']['recargo_urgente'], 2)
        assert res['costo_total'] == expected_total