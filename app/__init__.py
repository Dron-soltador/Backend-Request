import os
from flask import Flask
from flask_cors import CORS
from flasgger import Swagger
from app.models import db
from app.auth import auth_bp
from app.pedidos import pedidos_bp


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

    db.init_app(app)

    # Asegúrate de que ambas líneas tengan exactamente 4 espacios de sangría
    app.register_blueprint(auth_bp)
    app.register_blueprint(pedidos_bp)

    with app.app_context():
        db.create_all()

    return app