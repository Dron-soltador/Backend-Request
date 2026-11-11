"""Orquestador HTTP de despacho entre los microservicios de drones y pedidos."""

import logging
import os

import requests
from flask import Blueprint, jsonify, request


despacho_bp = Blueprint('despacho', __name__, url_prefix='/despacho')

PEDIDOS_SERVICE_URL = os.getenv(
    'PEDIDOS_SERVICE_URL', 'http://api-pedidos:5000/api/v1/pedidos'
)
DRONES_SERVICE_URL = os.getenv(
    'DRONES_SERVICE_URL', 'http://192.168.220.131:5000'
)
TIMEOUT_SEGUNDOS = 5

logger = logging.getLogger('Despachador')


def _log_fallo(etiqueta, error):
    logger.error(
        "[FALLA TRANSACCIONAL] No se pudo cambiar el estado de %s: %s",
        etiqueta,
        error,
    )


def _respuesta_exitosa(respuesta, etiqueta):
    logger.info(
        "[HTTP IN] Servicio %s respondió con HTTP %s",
        etiqueta,
        respuesta.status_code,
    )
    if respuesta.status_code == 200:
        return True
    _log_fallo(
        etiqueta,
        f"código {respuesta.status_code}: {respuesta.text}",
    )
    return False


def _actualizar_estado(url, payload, etiqueta):
    """Actualiza un estado remoto por HTTP y devuelve si tuvo éxito."""
    logger.info(
        "[HTTP OUT] Enviando PUT %s con estado '%s'...",
        url,
        payload.get('estado'),
    )
    try:
        respuesta = requests.put(url, json=payload, timeout=TIMEOUT_SEGUNDOS)
    except Exception as error:
        _log_fallo(etiqueta, error)
        return False
    return _respuesta_exitosa(respuesta, etiqueta)


def _actualizar_estado_dron(dron_id, estado_nuevo):
    """Actualiza el estado de un dron mediante llamada HTTP al servicio."""
    return _actualizar_estado(
        f"{DRONES_SERVICE_URL}/despachar",
        {"dron_id": dron_id, "estado": estado_nuevo},
        f"Dron #{dron_id}",
    )


def _actualizar_estado_pedido(pedido_id, estado_nuevo):
    """Actualiza el estado de un pedido mediante llamada HTTP al servicio."""
    return _actualizar_estado(
        f"{PEDIDOS_SERVICE_URL}/{pedido_id}/estado",
        {"estado": estado_nuevo},
        f"Pedido #{pedido_id}",
    )


def _pedir_reversion(dron_id):
    return requests.put(
        f"{DRONES_SERVICE_URL}/despachar",
        json={"estado": "DISPONIBLE"},
        timeout=TIMEOUT_SEGUNDOS,
    )


def _revertir_estado_dron(dron_id):
    """Revierte el estado del dron a DISPONIBLE en caso de fallo."""
    logger.info(
        "[REVERSION] Revirtiendo Dron #%s a estado DISPONIBLE...", dron_id
    )
    try:
        _pedir_reversion(dron_id)
    except Exception as error:
        logger.critical(
            "[ERROR CRITICO REVERSION] No se pudo revertir el Dron #%s: %s",
            dron_id,
            error,
        )
        return False

    logger.info(
        "[REVERSION OK] Dron #%s devuelto a estado DISPONIBLE", dron_id
    )
    return True


def _cuerpo_despacho():
    data = request.get_json() or {}
    return data.get('pedido_id'), data.get('dron_id')


def _error(message, code):
    return jsonify({"code": code, "message": message}), code


def _respuesta_despacho(pedido_id, dron_id):
    return jsonify({
        "message": "Despacho procesado exitosamente en ambos microservicios",
        "pedido_id": pedido_id,
        "dron_id": dron_id,
        "estado_pedido": "EN_CAMINO",
        "estado_dron": "EN_MISION",
    }), 200


def _coordinar_despacho(pedido_id, dron_id):
    if not _actualizar_estado_dron(dron_id, "EN_MISION"):
        return _error(
            "Falla en microservicio Drones. Operacion cancelada.", 500
        )

    if not _actualizar_estado_pedido(pedido_id, "EN_CAMINO"):
        _revertir_estado_dron(dron_id)
        return _error(
            "Falla al actualizar el pedido. Se ha revertido el estado "
            "del dron correctamente.",
            500,
        )

    logger.info(
        "=== DESPACHO COMPLETADO CON EXITO (Pedido #%s y Dron #%s) ===",
        pedido_id,
        dron_id,
    )
    return _respuesta_despacho(pedido_id, dron_id)


@despacho_bp.route('/despachar', methods=['POST'])
def despachar_envio():
    """Aprueba y despacha un pedido asignando un dron."""
    pedido_id, dron_id = _cuerpo_despacho()

    if not pedido_id or not dron_id:
        return _error(
            "Los campos 'pedido_id' y 'dron_id' son obligatorios", 400
        )

    logger.info(
        "=== INICIANDO PROCESO DE DESPACHO (Pedido #%s -> Dron #%s) ===",
        pedido_id,
        dron_id,
    )
    return _coordinar_despacho(pedido_id, dron_id)
