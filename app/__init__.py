import os
from flask import Flask
from flask_cors import CORS
from flasgger import Swagger  # <--- 1. Importamos Flasgger
from app.models import db
from app.auth import auth_bp

def create_app():
    app = Flask(__name__)
    CORS(app)

    # Configuración e inicialización de Swagger
    app.config['SWAGGER'] = {
        'title': 'API de Pedidos - Autenticación',
        'uiversion': 3
    }
    Swagger(app)  # <--- 2. Le decimos a Flask que levante la interfaz de Swagger

    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    app.register_blueprint(auth_bp)

    with app.app_context():
        db.create_all()

    return app