from flask import Blueprint, request, jsonify
from app.cotizador import calcular_cotizacion

pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/api/v1/pedidos')

@pedidos_bp.route('/cotizar', methods=['POST'])
def cotizar():
    """
    Cotización instantánea de tarifa de envío
    ---
    tags:
      - Cotizaciones
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - lat_origen
            - lon_origen
            - lat_destino
            - lon_destino
            - peso_kg
          properties:
            lat_origen:
              type: number
              example: -34.6037
            lon_origen:
              type: number
              example: -58.3816
            lat_destino:
              type: number
              example: -34.7000
            lon_destino:
              type: number
              example: -58.5000
            peso_kg:
              type: number
              example: 2.5
            es_fragil:
              type: boolean
              example: true
            es_urgente:
              type: boolean
              example: false
    responses:
      200:
        description: Desglose del costo calculado exitosamente
      400:
        description: Parámetros obligatorios faltantes o inválidos
    """
    data = request.get_json() or {}

    campos_obligatorios = ['lat_origen', 'lon_origen', 'lat_destino', 'lon_destino', 'peso_kg']
    for campo in campos_obligatorios:
        if campo not in data:
            return jsonify({"message": f"El campo '{campo}' es obligatorio"}), 400

    try:
        resultado = calcular_cotizacion(
            lat_a=float(data['lat_origen']),
            lon_a=float(data['lon_origen']),
            lat_b=float(data['lat_destino']),
            lon_b=float(data['lon_destino']),
            peso_kg=float(data['peso_kg']),
            es_fragil=bool(data.get('es_fragil', False)),
            es_urgente=bool(data.get('es_urgente', False))
        )
        return jsonify(resultado), 200
    except ValueError:
        return jsonify({"message": "Los datos numéricos ingresados no son válidos"}), 400