import os

from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from sqlalchemy import inspect, text

from app.models import db
from app.auth import auth_bp
from app.pedidos import pedidos_bp


def _ensure_pedidos_columns(app):
    """Mantiene compatibilidad con la base de datos creada por versiones anteriores.

    ``db.create_all()`` no agrega columnas a una tabla existente. Por eso se
    agregan aquí los campos de cliente y dirección. Luego se mantiene la
    compatibilidad con las bases antiguas: usuario y costo pueden ser nulos,
    mientras que origen y destino son obligatorios para el despachador.
    """
    inspector = inspect(db.engine)
    if "pedidos" not in inspector.get_table_names():
        return

    columns = {
        column["name"]: column
        for column in inspector.get_columns("pedidos")
    }
    additions = {
        "cliente": "ALTER TABLE pedidos ADD COLUMN cliente VARCHAR(100)",
        "direccion": "ALTER TABLE pedidos ADD COLUMN direccion VARCHAR(200)",
    }

    with db.engine.begin() as connection:
        for column_name, statement in additions.items():
            if column_name not in columns:
                connection.execute(text(statement))

        # El proyecto usa PostgreSQL. Usuario y costo no son parte del
        # contrato mínimo, pero origen y destino sí son obligatorios.
        if connection.dialect.name == "postgresql":
            for column_name in ("usuario_id", "costo_total"):
                if not columns.get(column_name, {}).get("nullable", True):
                    connection.execute(
                        text(
                            f'ALTER TABLE pedidos ALTER COLUMN "{column_name}" DROP NOT NULL'
                        )
                    )

            required_coordinates = (
                "lat_origen",
                "lon_origen",
                "lat_destino",
                "lon_destino",
            )
            for column_name in required_coordinates:
                if columns.get(column_name, {}).get("nullable", False):
                    connection.execute(
                        text(
                            f'ALTER TABLE pedidos ALTER COLUMN "{column_name}" SET NOT NULL'
                        )
                    )


def create_app():
    app = Flask(__name__)
    CORS(app)

    app.config['SWAGGER'] = {
        'title': 'API de Pedidos - Autenticación y Cotización',
        'uiversion': 3
    }
    Swagger(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DESPACHADOR_SERVICE_URL'] = os.getenv(
        'DESPACHADOR_SERVICE_URL', 'http://192.168.220.131:5002'
    )
    app.config['REMOTE_API_TIMEOUT'] = os.getenv('REMOTE_API_TIMEOUT', '5')
    app.config['REMOTE_API_TOKEN'] = os.getenv('REMOTE_API_TOKEN')

    db.init_app(app)

    # Asegúrate de que ambas líneas tengan exactamente 4 espacios de sangría
    app.register_blueprint(auth_bp)
    app.register_blueprint(pedidos_bp)

    with app.app_context():
        db.create_all()
        _ensure_pedidos_columns(app)

    return app