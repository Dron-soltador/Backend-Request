import math
from datetime import timezone

from flask import Blueprint, request, jsonify

from app.integracion import (
    IntegracionRemotaError,
    notificar_pedido_al_despachador,
)
from app.models import db, Pedido

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/api/v1/pedidos')

# Conjunto de estados permitidos según la especificación del contrato
ESTADOS_VALIDOS = {'PENDIENTE', 'EN_CAMINO', 'ENTREGADO', 'RECHAZADO'}


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


def _fecha_utc(fecha):
    if not fecha:
        return None
    if fecha.tzinfo is None:
        return f'{fecha.isoformat()}Z'
    return fecha.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


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


# 1. GET /api/v1/pedidos -> Listar todos los pedidos (Soluciona el error 405)
@pedidos_bp.route('', methods=['GET'])
def listar_pedidos():
    """
    Listar todos los pedidos registrados
    ---
    tags:
      - Pedidos
    responses:
      200:
        description: Lista de todos los pedidos
    """
    pedidos = Pedido.query.order_by(Pedido.fecha_creacion.desc()).all()
    return jsonify([pedido.to_dict() for pedido in pedidos]), 200


# 2. POST /api/v1/pedidos -> Registrar un nuevo pedido
@pedidos_bp.route('', methods=['POST'])
def crear_pedido():
    """Registra el pedido y notifica al despachador del administrador.
    ---
    tags:
      - Pedidos
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - cliente
            - direccion
            - peso_kg
            - origen
            - destino
          properties:
            usuario_id:
              type: integer
              description: Necesario para construir el historial del usuario
              example: 1
            cliente:
              type: string
              example: Carlos Rossi
            direccion:
              type: string
              example: Calle Belgrano 123
            peso_kg:
              type: number
              format: float
              example: 2.2
            es_fragil:
              type: boolean
              default: false
            es_urgente:
              type: boolean
              default: false
            origen:
              type: object
              required:
                - latitud
                - longitud
              properties:
                latitud:
                  type: number
                  example: -34.6037
                longitud:
                  type: number
                  example: -58.3816
            destino:
              type: object
              required:
                - latitud
                - longitud
              properties:
                latitud:
                  type: number
                  example: -34.7205
                longitud:
                  type: number
                  example: -58.2541
    responses:
      201:
        description: Pedido registrado y notificado al despachador
      400:
        description: Payload inválido
      502:
        description: El pedido se guardó, pero no se pudo notificar al despachador
    """
    data = request.get_json(silent=True) or {}
    if not isinstance(data, dict):
        return jsonify({
            "code": 400,
            "message": "El cuerpo de la petición debe ser un objeto JSON"
        }), 400

    # Aceptamos también la grafía con acento que podría enviar un cliente
    # externo, pero la salida y el payload remoto usan "direccion".
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

        lat_origen, lon_origen, lat_destino, lon_destino = _coordenadas_pedido(data)
        lat_origen, lon_origen = _validar_coordenadas(
            lat_origen, lon_origen, 'origen'
        )
        lat_destino, lon_destino = _validar_coordenadas(
            lat_destino, lon_destino, 'destino'
        )

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

        try:
            notificacion = notificar_pedido_al_despachador(nuevo_pedido.id)
        except IntegracionRemotaError as error:
            return jsonify({
                "message": (
                    "Pedido creado localmente, pero falló la notificación "
                    "al despachador"
                ),
                "pedido": nuevo_pedido.to_dict(),
                "notificacion": error.as_dict()
            }), 502

        return jsonify({
            "message": "Pedido creado exitosamente",
            "pedido": nuevo_pedido.to_dict(),
            "notificacion": notificacion
        }), 201

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


@pedidos_bp.route('/<int:pedido_id>/notificar-despacho', methods=['POST'])
def reintentar_notificacion_despacho(pedido_id):
    """Reintenta la notificación de un pedido sin crear uno nuevo.

    Ruta de integración interna: permanece disponible, pero se omite de
    Swagger.
    """
    pedido = db.session.get(Pedido, pedido_id)
    if not pedido:
        return jsonify({
            "error": "Not Found",
            "message": f"No se encontró el pedido con ID {pedido_id}."
        }), 404

    if pedido.estado != 'PENDIENTE':
        return jsonify({
            "code": 409,
            "message": (
                f"El pedido {pedido_id} ya no está PENDIENTE "
                f"(estado actual: {pedido.estado})"
            )
        }), 409

    try:
        notificacion = notificar_pedido_al_despachador(pedido_id)
    except IntegracionRemotaError as error:
        return jsonify(error.as_dict()), (error.status_code or 502)

    return jsonify({
        "message": "Pedido notificado exitosamente",
        "pedido_id": pedido_id,
        "notificacion": notificacion
    }), 200


# 3. GET /api/v1/pedidos/para-despachador -> Datos de envíos para el gestor
@pedidos_bp.route('/para-despachador', methods=['GET'])
def listar_pedidos_para_despachador():
    """Lista únicamente los datos necesarios para despachar los envíos.

    Ruta de integración con el despachador: se omite deliberadamente de
    Swagger, pero permanece disponible para el administrador de drones.
    """
    pedidos = Pedido.query.order_by(Pedido.fecha_creacion.asc()).all()
    return jsonify([
        _pedido_para_despachador(pedido) for pedido in pedidos
    ]), 200


# 4. GET /api/v1/pedidos/para-despachador/:id -> Un envío para despachar
@pedidos_bp.route('/para-despachador/<int:pedido_id>', methods=['GET'])
def obtener_pedido_para_despachador(pedido_id):
    """Obtiene un pedido con la proyección de datos del despachador.

    Ruta de integración con el despachador: se omite deliberadamente de
    Swagger, pero permanece disponible para el administrador de drones.
    """
    pedido = db.session.get(Pedido, pedido_id)
    if not pedido:
        return jsonify({
            "error": "Not Found",
            "message": f"No se encontró el pedido con ID {pedido_id}."
        }), 404

    return jsonify(_pedido_para_despachador(pedido)), 200


# 5. GET /api/v1/pedidos/:id -> Obtener detalle de un pedido
@pedidos_bp.route('/<int:pedido_id>', methods=['GET'])
def get_pedido_by_id(pedido_id):
    """Consulta la información de un pedido por su ID.
    ---
    tags:
      - Pedidos
    parameters:
      - in: path
        name: pedido_id
        type: integer
        required: true
    responses:
      200:
        description: Información del pedido
      404:
        description: Pedido no encontrado
    """
    pedido = db.session.get(Pedido, pedido_id)
    if not pedido:
        return jsonify({
            "error": "Not Found",
            "message": f"No se encontró el pedido con ID {pedido_id}."
        }), 404

    return jsonify(pedido.to_dict()), 200


# 6. GET /api/v1/pedidos/:id/estado -> Consultar estado del pedido
@pedidos_bp.route('/<int:pedido_id>/estado', methods=['GET'])
def consultar_estado_pedido(pedido_id):
    """Consulta el estado almacenado en la base de datos de Pedidos.
    ---
    tags:
      - Pedidos
    parameters:
      - in: path
        name: pedido_id
        type: integer
        required: true
    responses:
      200:
        description: Estado actual del pedido
      404:
        description: Pedido no encontrado
    """
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
def actualizar_estado_pedido(pedido_id):
    """Permite al administrador actualizar el estado del pedido.

    Endpoint de integración entre repositorios: se omite de Swagger, pero
    permanece activo en ``PUT /api/v1/pedidos/{pedido_id}/estado``.
    """
    data = request.get_json() or {}
    nuevo_estado = data.get('estado')

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
def obtener_pedidos_usuario(usuario_id):
    """Obtiene el historial de pedidos de un usuario.
    ---
    tags:
      - Pedidos
    parameters:
      - in: path
        name: usuario_id
        type: integer
        required: true
    responses:
      200:
        description: Historial de pedidos del usuario
    """
    pedidos = Pedido.query.filter_by(usuario_id=usuario_id).order_by(Pedido.fecha_creacion.desc()).all()
    return jsonify([pedido.to_dict() for pedido in pedidos]), 200