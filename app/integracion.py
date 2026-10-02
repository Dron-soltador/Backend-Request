"""Cliente HTTP para notificar pedidos al despachador del administrador."""

from typing import Any, Dict, Optional

import requests
from flask import current_app


DEFAULT_DESPACHADOR_SERVICE_URL = "http://192.168.220.131:5002"


class IntegracionRemotaError(Exception):
    """Error controlado al consumir un microservicio externo."""

    def __init__(
        self,
        message: str,
        *,
        status_code: Optional[int] = None,
        url: Optional[str] = None,
        detalle: Any = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.url = url
        self.detalle = detalle

    def as_dict(self) -> Dict[str, Any]:
        return {
            "exito": False,
            "mensaje": self.message,
            "url": self.url,
            "status_code": self.status_code,
            "detalle": self.detalle,
        }


def _timeout() -> float:
    try:
        timeout = float(current_app.config.get("REMOTE_API_TIMEOUT", 5))
        return timeout if timeout > 0 else 5.0
    except (TypeError, ValueError):
        return 5.0


def _headers(pedido_id: int) -> Dict[str, str]:
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "Idempotency-Key": f"pedido-{pedido_id}",
    }
    token = current_app.config.get("REMOTE_API_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"
    return headers


def _response_body(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return response.text.strip() or None


def notificar_pedido_al_despachador(pedido_id: int) -> Dict[str, Any]:
    """Notifica al despachador que existe un pedido nuevo.

    El servicio remoto publica ``POST /despachar`` y recibe el cuerpo
    ``{"pedido_id": <id>}``.
    """
    base_url = (
        current_app.config.get("DESPACHADOR_SERVICE_URL")
        or DEFAULT_DESPACHADOR_SERVICE_URL
    ).rstrip("/")
    url = f"{base_url}/despachar"
    payload = {"pedido_id": pedido_id}

    try:
        response = requests.post(
            url,
            json=payload,
            headers=_headers(pedido_id),
            timeout=_timeout(),
        )
    except requests.RequestException as exc:
        raise IntegracionRemotaError(
            "No se pudo notificar el pedido al microservicio despachador",
            url=url,
            detalle=str(exc),
        ) from exc

    detalle = _response_body(response)
    if not 200 <= response.status_code < 300:
        raise IntegracionRemotaError(
            "El microservicio despachador rechazó la notificación",
            status_code=response.status_code,
            url=url,
            detalle=detalle,
        )

    return {
        "exito": True,
        "url": url,
        "status_code": response.status_code,
        "respuesta": detalle,
    }
