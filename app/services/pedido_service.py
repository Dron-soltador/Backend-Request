"""Lógica de negocio y validaciones compartidas para pedidos.

Centraliza las reglas que antes estaban duplicadas en ``app.pedidos`` y en
``app.routes.api.pedidos`` para que exista una única fuente de verdad.
"""

from datetime import timezone
import math

from app.models import db, Pedido


CAMPOS_OBLIGATORIOS = ('cliente', 'direccion', 'peso_kg')
ESTADOS_VALIDOS = ('PENDIENTE', 'EN_CAMINO', 'ENTREGADO', 'RECHAZADO')


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


def _punto_para(data, nombre):
    """Devuelve (lat, lon) desde un punto anidado o desde claves planas."""
    punto = data.get(nombre)
    if isinstance(punto, dict):
        return _coordenadas_punto(punto)
    return data.get(f'lat_{nombre}'), data.get(f'lon_{nombre}')


def _coordenadas_pedido(data):
    """Devuelve las cuatro coordenadas del pedido (formato anidado o plano)."""
    lat_origen, lon_origen = _punto_para(data, 'origen')
    lat_destino, lon_destino = _punto_para(data, 'destino')
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


def validar_coordenadas_pedido(data):
    """Valida origen y destino completos y devuelve sus coordenadas."""
    lat_origen, lon_origen, lat_destino, lon_destino = _coordenadas_pedido(data)
    lat_origen, lon_origen = _validar_coordenadas(
        lat_origen, lon_origen, 'origen'
    )
    lat_destino, lon_destino = _validar_coordenadas(
        lat_destino, lon_destino, 'destino'
    )
    return lat_origen, lon_origen, lat_destino, lon_destino


def _parse_peso(peso_kg):
    """Convierte y valida el peso de un pedido."""
    if peso_kg is None or peso_kg == '':
        raise ValueError("El campo obligatorio 'peso_kg' debe ser provisto")
    peso = float(peso_kg)
    if not math.isfinite(peso) or peso <= 0:
        raise ValueError('peso_kg debe ser un número mayor que cero')
    return peso


def _punto(latitud, longitud):
    return {'latitud': latitud, 'longitud': longitud}


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
        'origen': _punto(pedido.lat_origen, pedido.lon_origen),
        'destino': _punto(pedido.lat_destino, pedido.lon_destino),
    }


def _normalizar_direccion(data):
    """Acepta la grafía con acento sin cambiar el contrato de salida."""
    if not data.get('direccion') and data.get('dirección'):
        data['direccion'] = data['dirección']


def _validar_campos_obligatorios(data):
    """Devuelve un error de validación o ``None`` si todo está presente."""
    for campo in CAMPOS_OBLIGATORIOS:
        if campo not in data or data[campo] is None or data[campo] == '':
            return {
                "code": 400,
                "message": f"El campo obligatorio '{campo}' no fue provisto",
            }
    return None


def _construir_pedido(data, coordenadas, peso_kg):
    lat_origen, lon_origen, lat_destino, lon_destino = coordenadas
    return Pedido(
        usuario_id=_to_int_or_none(data.get('usuario_id')),
        lat_origen=lat_origen,
        lon_origen=lon_origen,
        lat_destino=lat_destino,
        lon_destino=lon_destino,
        peso_kg=peso_kg,
        cliente=data.get('cliente') or data.get('nombre_cliente'),
        direccion=data.get('direccion') or data.get('dirección'),
        categoria=data.get('categoria', 'Estándar'),
        es_fragil=_to_bool(data.get('es_fragil', False)),
        es_urgente=_to_bool(data.get('es_urgente', False)),
        costo_total=_to_float_or_none(data.get('costo_total', 0.0)),
        fecha_programada=data.get('fecha_programada', None),
        estado='PENDIENTE',
    )


def _error_pedido(code, message):
    return {"code": code, "message": message}


def _guardar_pedido(data):
    """Valida los datos y persiste el pedido en la base."""
    peso_kg = _parse_peso(data['peso_kg'])
    coordenadas = validar_coordenadas_pedido(data)
    pedido = _construir_pedido(data, coordenadas, peso_kg)
    db.session.add(pedido)
    db.session.commit()
    return pedido


def crear_pedido(data):
    """Crea un nuevo pedido a partir de un diccionario de datos.

    Devuelve ``(pedido, None)`` o ``(None, error)`` si hubo un problema.
    """
    _normalizar_direccion(data)

    error = _validar_campos_obligatorios(data)
    if error:
        return None, error

    try:
        return _guardar_pedido(data), None
    except (TypeError, ValueError) as error:
        db.session.rollback()
        return None, _error_pedido(
            400, f"Error de formato en los datos enviados: {str(error)}"
        )
    except Exception as error:
        db.session.rollback()
        return None, _error_pedido(
            500, f"Error interno al guardar el pedido: {str(error)}"
        )
