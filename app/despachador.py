import os
import logging
import requests
from flask import Blueprint, request, jsonify

despacho_bp = Blueprint('despacho', __name__, url_prefix='/despacho')

# URLs de comunicación interna dentro de la red Docker ('red-logistica')
import os

PEDIDOS_SERVICE_URL = os.getenv('PEDIDOS_SERVICE_URL', 'http://api-pedidos:5000/api/v1/pedidos')
DRONES_SERVICE_URL = os.getenv('DRONES_SERVICE_URL', 'http://192.168.220.131:5000')


# Configuración de logs para cumplir con las evidencias requeridas
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("Despachador")

@despacho_bp.route('/despachar', methods=['POST'])
def despachar_envio():
    """
    Aprobar y despachar un pedido asignando un dron
    ---
    tags:
      - Despacho
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - pedido_id
            - dron_id
          properties:
            pedido_id:
              type: integer
              example: 1
            dron_id:
              type: integer
              example: 10
    responses:
      200:
        description: Despacho coordinado exitosamente en ambos microservicios
      400:
        description: Datos de entrada faltantes o invalidos
      500:
        description: Error de transaccionalidad logica o falla de comunicacion
    """
    data = request.get_json() or {}
    pedido_id = data.get('pedido_id')
    dron_id = data.get('dron_id')

    if not pedido_id or not dron_id:
        return jsonify({
            "code": 400,
            "message": "Los campos 'pedido_id' y 'dron_id' son obligatorios"
        }), 400

    logger.info(f"=== INICIANDO PROCESO DE DESPACHO (Pedido #{pedido_id} -> Dron #{dron_id}) ===")

    # PASO A: Actualizar estado del Dron a EN_MISION
    url_dron = f"{DRONES_SERVICE_URL}/despachar"
    logger.info(f"[HTTP OUT] Enviando PUT {url_dron} con estado 'EN_MISION'...")
    
    try:
        resp_dron = requests.put(url_dron, json={"dron_id": dron_id, "estado": "EN_MISION"}, timeout=5)
        logger.info(f"[HTTP IN] Servicio Drones respondio con HTTP {resp_dron.status_code}")
        
        if resp_dron.status_code != 200:
            raise Exception(f"Servicio Drones devolvio codigo {resp_dron.status_code}: {resp_dron.text}")

    except Exception as e:
        logger.error(f"[FALLA TRANSACCIONAL] No se pudo cambiar el estado del Dron #{dron_id}: {str(e)}")
        return jsonify({
            "code": 500,
            "message": f"Falla en microservicio Drones. Operacion cancelada: {str(e)}"
        }), 500

    # PASO B: Actualizar estado del Pedido a EN_CAMINO
    url_pedido = f"{PEDIDOS_SERVICE_URL}/{pedido_id}/estado"
    logger.info(f"[HTTP OUT] Enviando PUT {url_pedido} con estado 'EN_CAMINO'...")
    
    try:
        resp_pedido = requests.put(url_pedido, json={"estado": "EN_CAMINO"}, timeout=5)
        logger.info(f"[HTTP IN] Servicio Pedidos respondio con HTTP {resp_pedido.status_code}")

        if resp_pedido.status_code != 200:
            raise Exception(f"Servicio Pedidos devolvio codigo {resp_pedido.status_code}: {resp_pedido.text}")

    except Exception as e:
        logger.error(f"[FALLA TRANSACCIONAL] No se pudo cambiar el estado del Pedido #{pedido_id}: {str(e)}")
        logger.warning(f"[REVERSION / ROLLBACK] Iniciando compensacion: Revertiendo Dron #{dron_id} a DISPONIBLE...")
        
        # OPERACIÓN DE COMPENSACIÓN (Revertir cambio en Drones)
        try:
            requests.put(url_dron, json={"estado": "DISPONIBLE"}, timeout=5)
            logger.info(f"[REVERSION OK] Dron #{dron_id} devuelto exitosamente a estado DISPONIBLE")
        except Exception as err_rollback:
            logger.critical(f"[ERROR CRITICO REVERSION] No se pudo revertir el Dron #{dron_id}: {str(err_rollback)}")

        return jsonify({
            "code": 500,
            "message": "Falla al actualizar el pedido. Se ha revertido el estado del dron correctamente."
        }), 500

    logger.info(f"=== DESPACHO COMPLETADO CON EXITO (Pedido #{pedido_id} y Dron #{dron_id}) ===")

    return jsonify({
        "message": "Despacho procesado exitosamente en ambos microservicios",
        "pedido_id": pedido_id,
        "dron_id": dron_id,
        "estado_pedido": "EN_CAMINO",
        "estado_dron": "EN_MISION"
    }), 200