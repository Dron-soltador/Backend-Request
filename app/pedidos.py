from flask import Blueprint, request, jsonify
from app.models import db, Pedido
from app.cotizador import calcular_cotizacion

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/api/v1/pedidos')

# ... Endpoint de cotizar (Issue #03) continúa aquí ...

@pedidos_bp.route('', methods=['POST'])
def crear_pedido():
    """
    Registrar un nuevo pedido de envío
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
            - usuario_id
            - lat_origen
            - lon_origen
            - lat_destino
            - lon_destino
            - peso_kg
            - costo_total
          properties:
            usuario_id:
              type: integer
              example: 1
            lat_origen:
              type: number
              example: -34.6037
            lon_origen:
              type: number
              example: -58.3816
            lat_destino:
              type: number
              example: -34.7205
            lon_destino:
              type: number
              example: -58.2541
            peso_kg:
              type: number
              example: 2.5
            categoria:
              type: string
              example: "Electrónica"
            es_fragil:
              type: boolean
              example: true
            es_urgente:
              type: boolean
              example: false
            costo_total:
              type: number
              example: 4125.0
            fecha_programada:
              type: string
              example: "2026-09-05 14:00"
    responses:
      201:
        description: Pedido creado exitosamente con estado PENDIENTE
      400:
        description: Campos obligatorios faltantes o tipos de datos inválidos
    """
    data = request.get_json() or {}

    # Validar campos obligatorios según alcance de la issue
    campos_obligatorios = [
        'usuario_id', 'lat_origen', 'lon_origen', 
        'lat_destino', 'lon_destino', 'peso_kg', 'costo_total'
    ]
    
    for campo in campos_obligatorios:
        if campo not in data or data[campo] is None:
            return jsonify({
                "code": 400,
                "message": f"El campo obligatorio '{campo}' no fue provisto"
            }), 400

    try:
        nuevo_pedido = Pedido(
            usuario_id=int(data['usuario_id']),
            lat_origen=float(data['lat_origen']),
            lon_origen=float(data['lon_origen']),
            lat_destino=float(data['lat_destino']),
            lon_destino=float(data['lon_destino']),
            peso_kg=float(data['peso_kg']),
            categoria=data.get('categoria', 'Estándar'),
            es_fragil=bool(data.get('es_fragil', False)),
            es_urgente=bool(data.get('es_urgente', False)),
            costo_total=float(data['costo_total']),
            fecha_programada=data.get('fecha_programada', None),
            estado='PENDIENTE'  # Requisito explícito de la issue
        )

        db.session.add(nuevo_pedido)
        db.session.commit()

        return jsonify({
            "message": "Pedido creado exitosamente",
            "pedido": nuevo_pedido.to_dict()
        }), 201

    except ValueError:
        db.session.rollback()
        return jsonify({
            "code": 400,
            "message": "Error de formato en los datos numéricos enviados"
        }), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({
            "code": 500,
            "message": f"Error interno al guardar el pedido: {str(e)}"
        }), 500

# Conjunto de estados permitidos según la especificación de la issue
ESTADOS_VALIDOS = {'PENDIENTE', 'EN_CAMINO', 'ENTREGADO', 'RECHAZADO'}

@pedidos_bp.route('/usuario/<int:usuario_id>', methods=['GET'])
def obtener_pedidos_usuario(usuario_id):
    """
    Obtener el historial de pedidos de un usuario
    ---
    tags:
      - Pedidos
    parameters:
      - in: path
        name: usuario_id
        type: integer
        required: true
        description: ID del usuario para filtrar su historial
    responses:
      200:
        description: Lista de pedidos del usuario
    """
    # Consulta a PostgreSQL filtrando únicamente los paquetes de este usuario
    pedidos = Pedido.query.filter_by(usuario_id=usuario_id).order_by(Pedido.fecha_creacion.desc()).all()
    
    # Convertimos la lista de objetos SQLAlchemy a un arreglo de diccionarios JSON
    return jsonify([pedido.to_dict() for pedido in pedidos]), 200


@pedidos_bp.route('/<int:pedido_id>/estado', methods=['PUT'])
def actualizar_estado_pedido(pedido_id):
    """
    Actualizar el estado operativo de una orden
    ---
    tags:
      - Pedidos
    parameters:
      - in: path
        name: pedido_id
        type: integer
        required: true
        description: ID del pedido a modificar
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - estado
          properties:
            estado:
              type: string
              enum: [PENDIENTE, EN_CAMINO, ENTREGADO, RECHAZADO]
              example: EN_CAMINO
    responses:
      200:
        description: Estado actualizado correctamente
      400:
        description: El estado proporcionado no es válido
      404:
        description: No se encontró el pedido
    """
    data = request.get_json() or {}
    nuevo_estado = data.get('estado')

    # Validar que el estado enviado no sea nulo y pertenezca al catálogo permitido
    if not nuevo_estado or nuevo_estado not in ESTADOS_VALIDOS:
        return jsonify({
            "code": 400,
            "message": f"Estado inválido. Valores permitidos: {', '.join(sorted(ESTADOS_VALIDOS))}"
        }), 400

    # Buscar el pedido por su ID
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        return jsonify({
            "code": 404,
            "message": f"No se encontró ningún pedido con el ID {pedido_id}"
        }), 404

    try:
        # Actualización del campo y persistencia en la base de datos
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