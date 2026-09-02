import math

def calcular_distancia_haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0  # Radio de la Tierra en km
    
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = math.sin(delta_phi / 2)**2 + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    return round(R * c, 2)

def calcular_cotizacion(lat_a, lon_a, lat_b, lon_b, peso_kg, es_fragil=False, es_urgente=False):
    TARIFA_BASE = 500.0      # Precio base fijo
    PRECIO_POR_KG = 200.0    # Costo por kilo
    PRECIO_POR_KM = 150.0    # Costo por km recorrido

    distancia_km = calcular_distancia_haversine(lat_a, lon_a, lat_b, lon_b)
    
    costo_peso = peso_kg * PRECIO_POR_KG
    costo_distancia = distancia_km * PRECIO_POR_KM
    subtotal = TARIFA_BASE + costo_peso + costo_distancia

    recargo_fragil = round(subtotal * 0.15, 2) if es_fragil else 0.0
    recargo_urgente = round(subtotal * 0.25, 2) if es_urgente else 0.0

    total = round(subtotal + recargo_fragil + recargo_urgente, 2)

    return {
        "distancia_km": distancia_km,
        "desglose": {
            "tarifa_base": TARIFA_BASE,
            "costo_peso": costo_peso,
            "costo_distancia": costo_distancia,
            "subtotal": subtotal,
            "recargo_fragil": recargo_fragil,
            "recargo_urgente": recargo_urgente
        },
        "costo_total": total
    }