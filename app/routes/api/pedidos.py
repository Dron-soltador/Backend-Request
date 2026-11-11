"""Vistas (controladores) de pedidos API v1.

Define los endpoints HTTP /api/v1/pedidos. La validación y la lógica de
negocio viven en ``app.services`` para mantener las capas separadas.
"""

from flask import Blueprint, jsonify, request

from app.models import db, Pedido
from app.services.cotizador_service import cotizar_desde_payload
from app.services.pedido_service import (
    ESTADOS_VALIDOS,
    _pedido_para_despachador,
    crear_pedido,
)


pedidos_bp = Blueprint('pedidos', __name__, url_prefix='/api/v1/pedidos')


def _json_body():
    """Devuelve el cuerpo JSON como dict, o ``None`` si no es un objeto."""
    data = request.get_json(silent=True) or {}
    return data if isinstance(data, dict) else None


def _error(message, code):
    return jsonify({"code": code, "message": message}), code


def _no_encontrado(pedido_id):
    return jsonify({
        "error": "Not Found",
        "message": f"No se encontró el pedido con ID {pedido_id}.",
    }), 404


def _buscar_pedido(pedido_id):
    return db.session.get(Pedido, pedido_id)


def _notificar(pedido_id):
    """Notifica al despachador delegando en el módulo de compatibilidad.

    Se importa el módulo (no la función) para que los tests puedan parchear
    ``app.pedidos.notificar_pedido_al_despachador``.
    """
    from app import pedidos as pedidos_compat

    return pedidos_compat.notificar_pedido_al_despachador(pedido_id)


def _detalle_error_notificacion(error):
    """Normaliza el detalle del error de notificación."""
    if hasattr(error, 'as_dict'):
        return error.as_dict()
    return {"exito": False, "mensaje": str(error)}


def _cotizar(data):
    try:
        cotizacion = cotizar_desde_payload(data)
        return jsonify({
            "message": "Cotización calculada exitosamente",
            "cotizacion": cotizacion,
        }), 200
    except (TypeError, ValueError) as error:
        return _error(
            f'Error de formato en los datos enviados: {str(error)}', 400
        )
    except Exception as error:
        return _error(
            f'Error interno al cotizar el envío: {str(error)}', 500
        )


# 1.b POST /api/v1/pedidos/cotizar -> Cotización sin persistir el pedido
@pedidos_bp.route('/cotizar', methods=['POST'])
def cotizar_pedido():
    data = _json_body()
    if data is None:
        return _error(
            'El cuerpo de la petición debe ser un objeto JSON', 400
        )
    return _cotizar(data)


# 2. POST /api/v1/pedidos -> Registrar un nuevo pedido
@pedidos_bp.route('', methods=['POST'])
def crear_pedido_route():
    data = _json_body()
    if data is None:
        return _error(
            'El cuerpo de la petición debe ser un objeto JSON', 400
        )

    pedido, error = crear_pedido(data)
    if error:
        return jsonify(error), 400 if error.get('code') == 400 else 500

    return _respuesta_creacion(pedido)


def _respuesta_notificacion_fallida(pedido, error):
    return jsonify({
        "message": (
            "Pedido creado localmente, pero falló la notificación "
            "al despachador"
        ),
        "pedido": pedido.to_dict(),
        "notificacion": _detalle_error_notificacion(error),
    }), 502


def _respuesta_creacion(pedido):
    """Responde al alta de un pedido notificando al despachador."""
    try:
        notificacion = _notificar(pedido.id)
    except Exception as error:
        # Incluso si falla la notificación, el pedido quedó creado.
        return _respuesta_notificacion_fallida(pedido, error)

    return jsonify({
        "message": "Pedido creado exitosamente",
        "pedido": pedido.to_dict(),
        "notificacion": notificacion,
    }), 201


# 3. GET /api/v1/pedidos/para-despachador -> Datos de envíos para el gestor
@pedidos_bp.route('/para-despachador', methods=['GET'])
def listar_pedidos_para_despachador_route():
    pedidos = Pedido.query.order_by(Pedido.fecha_creacion.asc()).all()
    return jsonify([_pedido_para_despachador(p) for p in pedidos]), 200


# 4. GET /api/v1/pedidos/para-despachador/:id -> Un envío para despachar
@pedidos_bp.route('/para-despachador/<int:pedido_id>', methods=['GET'])
def obtener_pedido_para_despachador_route(pedido_id):
    pedido = _buscar_pedido(pedido_id)
    if not pedido:
        return _no_encontrado(pedido_id)
    return jsonify(_pedido_para_despachador(pedido)), 200


# 5. GET /api/v1/pedidos/:id -> Obtener detalle de un pedido
@pedidos_bp.route('/<int:pedido_id>', methods=['GET'])
def get_pedido_by_id_route(pedido_id):
    pedido = _buscar_pedido(pedido_id)
    if not pedido:
        return _no_encontrado(pedido_id)
    return jsonify(pedido.to_dict()), 200


# 6. GET /api/v1/pedidos/:id/estado -> Consultar estado del pedido
@pedidos_bp.route('/<int:pedido_id>/estado', methods=['GET'])
def consultar_estado_pedido_route(pedido_id):
    pedido = _buscar_pedido(pedido_id)
    if not pedido:
        return _no_encontrado(pedido_id)
    return jsonify({
        "pedido_id": pedido_id,
        "estado": pedido.estado,
    }), 200


# Notificación de un pedido existente (solo para testeo/desarrollo)
@pedidos_bp.route('/<int:pedido_id>/notificar-despacho', methods=['POST'])
def notificar_despacho_route(pedido_id):
    try:
        notificacion = _notificar(pedido_id)
        return jsonify({
            "message": "Notificación enviada exitosamente",
            "pedido_id": pedido_id,
            "notificacion": notificacion,
        }), 200
    except Exception as error:
        return jsonify({
            "message": "Falló la notificación al despachador",
            "pedido_id": pedido_id,
            "error": str(error),
        }), 500


# 7. PUT /api/v1/pedidos/:id/estado -> Integración del administrador
@pedidos_bp.route('/<int:pedido_id>/estado', methods=['PUT'])
def actualizar_estado_pedido_route(pedido_id):
    data = _json_body() or {}
    nuevo_estado = data.get('estado')

    if not nuevo_estado or nuevo_estado not in ESTADOS_VALIDOS:
        return _error(
            f"Estado inválido. Valores permitidos: {', '.join(ESTADOS_VALIDOS)}",
            400,
        )

    pedido = _buscar_pedido(pedido_id)
    if not pedido:
        return _no_encontrado(pedido_id)

    return _guardar_estado(pedido, nuevo_estado)


def _guardar_estado(pedido, nuevo_estado):
    """Persiste el nuevo estado del pedido y responde el resultado."""
    try:
        pedido.estado = nuevo_estado
        db.session.commit()
        return jsonify({
            "message": "Estado del pedido actualizado exitosamente",
            "pedido": pedido.to_dict(),
        }), 200
    except Exception as error:
        db.session.rollback()
        return _error(
            f'Error interno al actualizar el estado: {str(error)}', 500
        )


# 8. GET /api/v1/pedidos/usuario/:usuario_id -> Historial del usuario
@pedidos_bp.route('/usuario/<int:usuario_id>', methods=['GET'])
def obtener_pedidos_usuario_route(usuario_id):
    pedidos = (
        Pedido.query
        .filter_by(usuario_id=usuario_id)
        .order_by(Pedido.fecha_creacion.desc())
        .all()
    )
    return jsonify([p.to_dict() for p in pedidos]), 200
