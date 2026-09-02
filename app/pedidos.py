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