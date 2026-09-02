from datetime import datetime
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Usuario(db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    rol = db.Column(db.String(20), nullable=False, default='cliente')

class Pedido(db.Model):
    __tablename__ = 'pedidos'

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'), nullable=False)
    lat_origen = db.Column(db.Float, nullable=False)
    lon_origen = db.Column(db.Float, nullable=False)
    lat_destino = db.Column(db.Float, nullable=False)
    lon_destino = db.Column(db.Float, nullable=False)
    peso_kg = db.Column(db.Float, nullable=False)
    categoria = db.Column(db.String(50), nullable=True, default='Estándar')
    es_fragil = db.Column(db.Boolean, default=False)
    es_urgente = db.Column(db.Boolean, default=False)
    costo_total = db.Column(db.Float, nullable=False)
    fecha_programada = db.Column(db.String(50), nullable=True)
    estado = db.Column(db.String(20), nullable=False, default='PENDIENTE')
    fecha_creacion = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "lat_origen": self.lat_origen,
            "lon_origen": self.lon_origen,
            "lat_destino": self.lat_destino,
            "lon_destino": self.lon_destino,
            "peso_kg": self.peso_kg,
            "categoria": self.categoria,
            "es_fragil": self.es_fragil,
            "es_urgente": self.es_urgente,
            "costo_total": self.costo_total,
            "fecha_programada": self.fecha_programada,
            "estado": self.estado,
            "fecha_creacion": self.fecha_creacion.isoformat() if self.fecha_creacion else None
        }