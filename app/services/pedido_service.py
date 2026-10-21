"""Servicio de lógica de negocio para pedidos.

Extrae funciones auxiliares y operaciones de pedido de
app.pedidos para mantener las capas separadas y reducir la duplicación.
"""

from datetime import timezone
import math


def _to_int_or_none(value):
    if value is None or value == '':
        return None
    return int(value)


def _to_float_or_none(value):
    if value is None or value == '':
        return None
    return float(value)


def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 't', 'yes', 'si', 'sí'}
    return bool(value)


def _fecha_utc(fecha):
    if not fecha:
        return None
    if fecha.tzinfo is None:
        return f'{fecha.isoformat()}Z'
    return fecha.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def _coordenadas_punto(punto):
    """Lee un punto desde un objeto {latitud, longitud}."""
    if not isinstance(punto, dict):
        return None, None
    return (
        punto.get('latitud', punto.get('lat')),
        punto.get('longitud', punto.get('lon', punto.get('lng'))),
    )


def _coordenadas_pedido(data):
    origen = data.get('origen')
    destino = data.get('destino')

    if isinstance(origen, dict):
        lat_origen, lon_origen = _coordenadas_punto(origen)
    else:
        lat_origen = data.get('lat_origen')
        lon_origen = data.get('lon_origen')

    if isinstance(destino, dict):
        lat_destino, lon_destino = _coordenadas_punto(destino)
    else:
        lat_destino = data.get('lat_destino')
        lon_destino = data.get('lon_destino')

    return lat_origen, lon_origen, lat_destino, lon_destino


def _validar_coordenadas(latitud, longitud, nombre):
    latitud = _to_float_or_none(latitud)
    longitud = _to_float_or_none(longitud)

    if latitud is None or longitud is None:
        raise ValueError(f'{nombre} debe incluir latitud y longitud')
    if not -90 <= latitud <= 90:
        raise ValueError(f'La latitud de {nombre} debe estar entre -90 y 90')
    if not -180 <= longitud <= 180:
        raise ValueError(f'La longitud de {nombre} debe estar entre -180 y 180')

    return latitud, longitud


def _pedido_para_despachador(pedido):
    """Proyección pública para el gestor de drones.

    Expone únicamente los campos necesarios para asignar y despachar. No
    incluye categoría, costo, cliente ni datos de usuario.
    """
    return {
        'id': pedido.id,
        'peso_kg': pedido.peso_kg,
        'es_urgente': bool(pedido.es_urgente),
        'fecha_creacion': _fecha_utc(pedido.fecha_creacion),
        'es_fragil': bool(pedido.es_fragil),
        'origen': {
            'latitud': pedido.lat_origen,
            'longitud': pedido.lon_origen,
        },
        'destino': {
            'latitud': pedido.lat_destino,
            'longitud': pedido.lon_destino,
        },
    }


def crear_pedido(data, commit=True):
    """Crea un nuevo pedido a partir de un diccionario de datos.

    Devuelve tupla (pedido, error_dict, status_code).
    Si error_dict es None, el pedido se guardó exitosamente.
    """
    # Aceptamos también la grafía con acento que podría enviar un cliente
    # externo, pero la salida y el payload remoto usa "direccion".
    if not data.get('direccion') and data.get('dirección'):
        data['direccion'] = data['dirección']

    campos_obligatorios = ['cliente', 'direccion', 'peso_kg']
    for campo in campos_obligatorios:
        if campo not in data or data[campo] is None or data[campo] == '':
            return None, {
                "code": 400,
                "message": f"El campo obligatorio '{campo}' no fue provisto"
            }, 400

    try:
        peso_kg = float(data['peso_kg'])
        if not math.isfinite(peso_kg) or peso_kg <= 0:
            return None, {
                "code": 400,
                "message": "peso_kg debe ser un número mayor que cero"
            }, 400

        lat_origen, lon_origen, lat_destino, lon_destino = _coordenadas_pedido(data)
        lat_origen, lon_origen = _validar_coordenadas(
            lat_origen, lon_origen, 'origen'
        )
        lat_destino, lon_destino = _validar_coordenadas(
            lat_destino, lon_destino, 'destino'
        )

        from app.models import Usuario
        cliente = data.get('cliente') or data.get('nombre_cliente')
        direccion = data.get('direccion') or data.get('dirección')

        # Note: usuario_id handling would need the Pedido model import
        # This function is designed as a partial extraction; the full
        # creation with Usuario handling is in app.pedidos for backward compat

        # For now, return None to signal partial extraction
        return None, {
            "code": 501,
            "message": "Función en extracción progresiva - ver app.pedidos"
        }, 501

    except (TypeError, ValueError) as error:
        return None, {
            "code": 400,
            "message": f"Error de formato en los datos enviados: {str(error)}"
        }, 400
    except Exception as e:
        return None, {
            "code": 500,
            "message": f"Error interno al guardar el pedido: {str(e)}"
        }, 500