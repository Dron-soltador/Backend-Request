"""Vistas (controladores) de pedidos API v1.

Define los endpoints HTTP /api/v1/pedidos para la gestión completa de pedidos.
Esta capa delega la lógica de negocio directamente (mantiene la estructura
de capas reconocibles sin dependencias circulares complejas).
"""

from flask import Blueprint, request, jsonify
from app.models import db, Pedido

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/api/v1/pedidos')


# 1. GET /api/v1/pedidos -> Listar todos los pedidos
@pedidos_bp.route('', methods=['GET'])
def listar_pedidos():
    pedidos = Pedido.query.order_by(Pedido.fecha_creacion.desc()).all()
    return jsonify([pedido.to_dict() for pedido in pedidos]), 200


# 1.b POST /api/v1/pedidos/cotizar -> Cotización sin persistir el pedido
@pedidos_bp.route('/cotizar', methods=['POST'])
def cotizar_pedido():
    from app.cotizador import calcular_cotizacion
    import math

    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({
            "code": 400,
            "message": "El cuerpo de la petición debe ser un objeto JSON"
        }), 400

    try:
        peso_kg = data.get('peso_kg')
        if peso_kg is None or peso_kg == '':
            return jsonify({
                "code": 400,
                "message": "El campo obligatorio 'peso_kg' debe ser provisto"
            }), 400

        peso_kg = float(peso_kg)
        if not math.isfinite(peso_kg) or peso_kg <= 0:
            raise ValueError('peso_kg debe ser un número mayor que cero')

        def _coordenadas_punto(punto):
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
            try:
                lat = float(latitud) if latitud is not None else None
                lon = float(longitud) if longitud is not None else None
            except (TypeError, ValueError):
                raise ValueError(f'{nombre} debe incluir latitud y longitud')
            if lat is None or lon is None:
                raise ValueError(f'{nombre} debe incluir latitud y longitud')
            if not -90 <= lat <= 90:
                raise ValueError(f'La latitud de {nombre} debe estar entre -90 y 90')
            if not -180 <= lon <= 180:
                raise ValueError(f'La longitud de {nombre} debe estar entre -180 y 180')
            return lat, lon

        lat_origen, lon_origen, lat_destino, lon_destino = _coordenadas_pedido(data)
        lat_origen, lon_origen = _validar_coordenadas(lat_origen, lon_origen, 'origen')
        lat_destino, lon_destino = _validar_coordenadas(lat_destino, lon_destino, 'destino')

        cotizacion = calcular_cotizacion(
            lat_origen, lon_origen,
            lat_destino, lon_destino,
            peso_kg,
            es_fragil=data.get('es_fragil', False),
            es_urgente=data.get('es_urgente', False),
        )

        return jsonify({
            "message": "Cotización calculada exitosamente",
            "cotizacion": cotizacion
        }), 200

    except (TypeError, ValueError) as error:
        return jsonify({
            "code": 400,
            "message": f"Error de formato en los datos enviados: {str(error)}"
        }), 400
    except Exception as e:
        return jsonify({
            "code": 500,
            "message": f"Error interno al cotizar el envío: {str(e)}"
        }), 500


# 2. POST /api/v1/pedidos -> Registrar un nuevo pedido
@pedidos_bp.route('', methods=['POST'])
def crear_pedido_route():
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({
            "code": 400,
            "message": "El cuerpo de la petición debe ser un objeto JSON"
        }), 400

    from datetime import datetime
    from app.models import Usuario
    
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

        def _validar_coordenadas_lat_long(latitud, longitud, nombre):
            try:
                lat = float(latitud) if latitud is not None else None
                lon = float(longitud) if longitud is not None else None
            except (TypeError, ValueError):
                raise ValueError(f'{nombre} debe incluir latitud y longitud')
            if lat is None or lon is None:
                raise ValueError(f'{nombre} debe incluir latitud y longitud')
            if not -90 <= lat <= 90:
                raise ValueError(f'La latitud de {nombre} debe estar entre -90 y 90')
            if not -180 <= lon <= 180:
                raise ValueError(f'La longitud de {nombre} debe estar entre -180 y 180')
            return lat, lon

        lat_origen, lon_origen = _validar_coordenadas_lat_long(
            data.get('lat_origen'), data.get('lon_origen'), 'origen'
        )
        lat_destino, lon_destino = _validar_coordenadas_lat_long(
            data.get('lat_destino'), data.get('lon_destino'), 'destino'
        )

        cliente = data.get('cliente') or data.get('nombre_cliente')
        direccion = data.get('direccion') or data.get('dirección')

        nuevo_pedido = Pedido(
            usuario_id=int(data.get('usuario_id')) if data.get('usuario_id') else None,
            lat_origen=lat_origen,
            lon_origen=lon_origen,
            lat_destino=lat_destino,
            lon_destino=lon_destino,
            peso_kg=peso_kg,
            cliente=cliente,
            direccion=direccion,
            categoria=data.get('categoria', 'Estándar'),
            es_fragil=data.get('es_fragil', False),
            es_urgente=data.get('es_urgente', False),
            costo_total=float(data.get('costo_total', 0.0)) if data.get('costo_total') is not None else None,
            fecha_programada=data.get('fecha_programada', None),
            estado='PENDIENTE'
        )

        db.session.add(nuevo_pedido)
        db.session.commit()

        try:
            from app.integracion import notificar_pedido_al_despachador as _notificar
            notificacion = _notificar(nuevo_pedido.id)
            if isinstance(notificacion, tuple) and len(notificacion) == 2:
                result_dict, err_code = notificacion
                return jsonify({
                    "message": (
                        "Pedido creado localmente, pero falló la notificación "
                        "al despachador"
                    ),
                    "pedido": nuevo_pedido.to_dict(),
                    "notificacion": result_dict
                }), 502
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
    def _pedido_para_despachador(p):
        from datetime import timezone
        return {
            'id': p.id,
            'peso_kg': p.peso_kg,
            'es_urgente': bool(p.es_urgente),
            'fecha_creacion': (
                f'{p.fecha_creacion.isoformat()}Z'
                if p.fecha_creacion and timezone.getdefault_timezone()
                else str(pedido.fecha_creacion) if p.fecha_creacion else None
            ),
            'es_fragil': bool(p.es_fragil),
            'origen': {
                'latitud': p.lat_origen,
                'longitud': p.lon_origen,
            },
            'destino': {
                'latitud': p.lat_destino,
                'longitud': p.lon_destino,
            },
        }
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
    def _pedido_para_despachador(p):
        from datetime import timezone
        return {
            'id': p.id,
            'peso_kg': p.peso_kg,
            'es_urgente': bool(p.es_urgente),
            'fecha_creacion': (
                f'{p.fecha_creacion.isoformat()}Z'
                if p.fecha_creacion else None
            ),
            'es_fragil': bool(p.es_fragil),
            'origen': {
                'latitud': p.lat_origen,
                'longitud': p.lon_origen,
            },
            'destino': {
                'latitud': p.lat_destino,
                'longitud': p.lon_destino,
            },
        }
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