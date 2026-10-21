"""Vistas (controladores) de pedidos API v1.

Define los endpoints HTTP /api/v1/pedidos para la gestión completa de pedidos.
"""

import math
from flask import Blueprint, request, jsonify
from app.models import db, Pedido

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/api/v1/pedidos')


# Helper: formatear fecha en formato ISO con sufijo Z
def _formatear_fecha_iso(fecha):
    """Formatea una fecha datetime a formato ISO 8601 con sufijo Z."""
    if not fecha:
        return None
    iso = fecha.isoformat()
    if not iso.endswith('Z') and not iso.endswith('+00:00'):
        iso += 'Z'
    return iso


# Helper: proyección para despachador
def _pedido_para_despachador(pedido):
    """Proyección pública para el gestor de drones.

    Expone únicamente los campos necesarios para asignar y despachar. No
    incluye categoría, costo, cliente ni datos de usuario.
    """
    return {
        'id': pedido.id,
        'peso_kg': pedido.peso_kg,
        'es_urgente': bool(pedido.es_urgente),
        'fecha_creacion': _formatear_fecha_iso(pedido.fecha_creacion),
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


# Helper: validar coordenadas y devolver ValueError si inválidas
def _validar_coordenadas(data, nombre):
    """Valida que las coordenadas vengan informadas y estén en rangos válidos.

    Retorna (lat, lon) en caso exitoso.
    """
    lat = data.get('lat_origen') if nombre == 'origen' else data.get('lat_destino')
    lon = data.get('lon_origen') if nombre == 'origen' else data.get('lon_destino')

    if lat is None or lon is None:
        raise ValueError(f'{nombre} debe incluir latitud y longitud')

    try:
        lat_f = float(lat)
        lon_f = float(lon)
    except (TypeError, ValueError):
        raise ValueError(f'{nombre} debe incluir latitud y longitud')

    if not -90 <= lat_f <= 90:
        raise ValueError(f'La latitud de {nombre} debe estar entre -90 y 90')
    if not -180 <= lon_f <= 180:
        raise ValueError(f'La longitud de {nombre} debe estar entre -180 y 180')

    return lat_f, lon_f


# Helper: convertir a bool
def _to_bool(value):
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {'1', 'true', 't', 'yes', 'si', 'sí'}
    return bool(value)


# Helper: convertir a int o None
def _to_int_or_none(value):
    if value is None or value == '':
        return None
    return int(value)


# 2. POST /api/v1/pedidos -> Registrar un nuevo pedido
@pedidos_bp.route('', methods=['POST'])


#: Función de notificación al despachador.
#: Las pruebas parchean este nombre: patch('app.pedidos.notificar_pedido_al_despachador', ...)
def notificar_pedido_al_despachador(pedido_id):
    """Enviar notificación al servicio de despachador."""
    # La prueba parchea app.pedidos.notificar_pedido_al_despachador
    # y esta función debe ser reemplazada por el parche
    from app.integracion import notificar_pedido_al_despachador as _notificar
    return _notificar(pedido_id)
def crear_pedido_route():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({
            "code": 400,
            "message": "El cuerpo de la petición debe ser un objeto JSON"
        }), 400

    # Validación anticipada de campos obligatorios
    if not data.get('direccion') and data.get('dirección'):
        data['direccion'] = data['dirección']

    campos_obligatorios = ['cliente', 'direccion', 'peso_kg']
    for campo in campos_obligatorios:
        if campo not in data or data[campo] is None or data[campo] == '':
            return jsonify({
                "code": 400,
                "message": f"El campo obligatorio '{campo}' no fue provisto"
            }), 400

    try:
        peso_kg = float(data['peso_kg'])
        if not math.isfinite(peso_kg) or peso_kg <= 0:
            raise ValueError('peso_kg debe ser un número mayor que cero')

        # Validar coordenadas de origen (lanzamos ValueError si faltan)
        try:
            lat_origen, lon_origen = _validar_coordenadas(data, 'origen')
        except ValueError as e:
            return jsonify({
                "code": 400,
                "message": f"Error de formato en los datos enviados: {str(e)}"
            }), 400

        # Validar coordenadas de destino
        try:
            lat_destino, lon_destino = _validar_coordenadas(data, 'destino')
        except ValueError as e:
            return jsonify({
                "code": 400,
                "message": f"Error de formato en los datos enviados: {str(e)}"
            }), 400

        cliente = data.get('cliente') or data.get('nombre_cliente')
        direccion = data.get('direccion') or data.get('dirección')

        nuevo_pedido = Pedido(
            usuario_id=_to_int_or_none(data.get('usuario_id')),
            lat_origen=lat_origen,
            lon_origen=lon_origen,
            lat_destino=lat_destino,
            lon_destino=lon_destino,
            peso_kg=peso_kg,
            cliente=cliente,
            direccion=direccion,
            categoria=data.get('categoria', 'Estándar'),
            es_fragil=_to_bool(data.get('es_fragil', False)),
            es_urgente=_to_bool(data.get('es_urgente', False)),
            costo_total=_to_float_or_none(data.get('costo_total', 0.0)),
            fecha_programada=data.get('fecha_programada', None),
            estado='PENDIENTE'
        )

        db.session.add(nuevo_pedido)
        db.session.commit()

        # Notificar al despachador
        from app.integracion import notificar_pedido_al_despachador as _notificar
        try:
            notificacion = _notificar(nuevo_pedido.id)
            return jsonify({
                "message": "Pedido creado exitosamente",
                "pedido": nuevo_pedido.to_dict(),
                "notificacion": notificacion
            }), 201
        except Exception:
            return jsonify({
                "message": "Pedido creado localmente, pero falló la notificación al despachador"
            }), 502

    except (TypeError, ValueError) as error:
        db.session.rollback()
        return jsonify({
            "code": 400,
            "message": f"Error de formato en los datos enviados: {str(error)}"
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "code": 500,
            "message": f"Error interno al guardar el pedido: {str(e)}"
        }), 500


# 3. GET /api/v1/pedidos/para-despachador -> Datos de envíos para el gestor
@pedidos_bp.route('/para-despachador', methods=['GET'])
def listar_pedidos_para_despachador_route():
    pedidos = Pedido.query.order_by(Pedido.fecha_creacion.asc()).all()
    return jsonify([_pedido_para_despachador(p) for p in pedidos]), 200


# 4. GET /api/v1/pedidos/para-despachador/:id -> Un envío para despachar
@pedidos_bp.route('/para-despachador/<int:pedido_id>', methods=['GET'])
def obtener_pedido_para_despachador_route(pedido_id):
    pedido = db.session.get(Pedido, pedido_id)
    if not pedido:
        return jsonify({
            "error": "Not Found",
            "message": f"No se encontró el pedido con ID {pedido_id}."
        }), 404
    return jsonify(_pedido_para_despachador(pedido)), 200


# 5. GET /api/v1/pedidos/:id -> Obtener detalle de un pedido
@pedidos_bp.route('/<int:pedido_id>', methods=['GET'])
def get_pedido_by_id_route(pedido_id):
    pedido = db.session.get(Pedido, pedido_id)
    if not pedido:
        return jsonify({
            "error": "Not Found",
            "message": f"No se encontró el pedido con ID {pedido_id}."
        }), 404
    return jsonify(pedido.to_dict()), 200


# 6. GET /api/v1/pedidos/:id/estado -> Consultar estado del pedido
@pedidos_bp.route('/<int:pedido_id>/estado', methods=['GET'])
def consultar_estado_pedido_route(pedido_id):
    pedido = db.session.get(Pedido, pedido_id)
    if not pedido:
        return jsonify({
            "error": "Not Found",
            "message": f"No se encontró el pedido con ID {pedido_id}."
        }), 404
    return jsonify({
        "pedido_id": pedido_id,
        "estado": pedido.estado
    }), 200

# Notificación de un pedido existente (solo para testeo/desarrollo)
@pedidos_bp.route('/<int:pedido_id>/notificar-despacho', methods=['POST'])
def notificar_despacho_route(pedido_id):
    from app.integracion import notificar_pedido_al_despachador as _notificar
    try:
        notificacion = _notificar(pedido_id)
        return jsonify({
            "message": "Notificación enviada exitosamente",
            "pedido_id": pedido_id,
            "notificacion": notificacion
        }), 200
    except Exception as e:
        return jsonify({
            "message": "Falló la notificación al despachador",
            "pedido_id": pedido_id,
            "error": str(e)
        }), 500


# 7. PUT /api/v1/pedidos/:id/estado -> Integración del administrador
@pedidos_bp.route('/<int:pedido_id>/estado', methods=['PUT'])
def actualizar_estado_pedido_route(pedido_id):
    data = request.get_json() or {}
    nuevo_estado = data.get('estado')

    ESTADOS_VALIDOS = {'PENDIENTE', 'EN_CAMINO', 'ENTREGADO', 'RECHAZADO'}

    if not nuevo_estado or nuevo_estado not in ESTADOS_VALIDOS:
        return jsonify({
            "code": 400,
            "message": f"Estado inválido. Valores permitidos: {', '.join(ESTADOS_VALIDOS)}"
        }), 400

    pedido = db.session.get(Pedido, pedido_id)
    if not pedido:
        return jsonify({
            "error": "Not Found",
            "message": f"No se encontró el pedido con ID {pedido_id}."
        }), 404

    try:
        pedido.estado = nuevo_estado
        db.session.commit()
        return jsonify({
            "message": "Estado del pedido actualizado exitosamente",
            "pedido": pedido.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "code": 500,
            "message": f"Error interno al actualizar el estado: {str(e)}"
        }), 500


# 8. GET /api/v1/pedidos/usuario/:usuario_id -> Historial del usuario
@pedidos_bp.route('/usuario/<int:usuario_id>', methods=['GET'])
def obtener_pedidos_usuario_route(usuario_id):
    pedidos = Pedido.query.filter_by(usuario_id=usuario_id).order_by(Pedido.fecha_creacion.desc()).all()
    return jsonify([pedido.to_dict() for p in pedidos]), 200
