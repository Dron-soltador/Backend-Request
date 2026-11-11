import os

from flask import Flask
from flask_cors import CORS
from flasgger import Swagger

from app.models import db


def _configurar_app(app):
    """Carga la configuración de la aplicación desde el entorno."""
    app.config['SWAGGER'] = {
        'title': 'API de Pedidos - Autenticación y Cotización',
        'uiversion': 3,
    }
    Swagger(app)

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['DESPACHADOR_SERVICE_URL'] = os.getenv(
        'DESPACHADOR_SERVICE_URL', 'http://192.168.220.131:5002'
    )
    app.config['REMOTE_API_TIMEOUT'] = os.getenv('REMOTE_API_TIMEOUT', '5')
    app.config['REMOTE_API_TOKEN'] = os.getenv('REMOTE_API_TOKEN')


def _registrar_blueprints(app):
    """Registra los blueprints de la capa de presentación."""
    from app.routes.api.auth import auth_bp
    from app.routes.api.pedidos import pedidos_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(pedidos_bp)


def create_app():
    app = Flask(__name__)
    CORS(app)

    _configurar_app(app)
    db.init_app(app)
    _registrar_blueprints(app)

    with app.app_context():
        db.create_all()

    return app
