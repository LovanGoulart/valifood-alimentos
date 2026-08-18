from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import pytz
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')))
    active = db.Column(db.Boolean, default=True)

    # Preferências de notificação
    alert_day_of = db.Column(db.Boolean, default=True)
    alert_1_day = db.Column(db.Boolean, default=True)
    alert_3_days = db.Column(db.Boolean, default=True)
    alert_7_days = db.Column(db.Boolean, default=True)
    alert_14_days = db.Column(db.Boolean, default=False)
    alert_30_days = db.Column(db.Boolean, default=False)

    products = db.relationship('Product', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    categories = db.relationship('Category', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    locations = db.relationship('StorageLocation', backref='owner', lazy='dynamic', cascade='all, delete-orphan')
    history = db.relationship('History', backref='user', lazy='dynamic', cascade='all, delete-orphan')

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Category(db.Model):
    __tablename__ = 'categories'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(10), default='📦')
    color = db.Column(db.String(20), default='#6366f1')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')))

    products = db.relationship('Product', backref='category', lazy='dynamic')

class StorageLocation(db.Model):
    __tablename__ = 'storage_locations'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), nullable=False)
    icon = db.Column(db.String(10), default='📍')
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')))

    products = db.relationship('Product', backref='location', lazy='dynamic')

class Product(db.Model):
    __tablename__ = 'products'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    barcode = db.Column(db.String(50), nullable=True)
    name = db.Column(db.String(150), nullable=False)
    brand = db.Column(db.String(100), nullable=True)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    quantity = db.Column(db.Float, default=1)
    unit = db.Column(db.String(20), default='unidade')
    purchase_date = db.Column(db.Date, nullable=True)
    expiration_date = db.Column(db.Date, nullable=True)
    no_expiration = db.Column(db.Boolean, default=False)
    storage_location_id = db.Column(db.Integer, db.ForeignKey('storage_locations.id'), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    image = db.Column(db.String(255), nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')), onupdate=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')))
    active = db.Column(db.Boolean, default=True)

    def get_status(self):
        if self.no_expiration or not self.expiration_date:
            return 'sem_validade'

        today = datetime.now(pytz.timezone('America/Sao_Paulo')).date()
        days = (self.expiration_date - today).days

        if days < 0:
            return 'vencido'
        elif days == 0:
            return 'vence_hoje'
        elif days <= 3:
            return 'urgente'
        elif days <= 7:
            return 'atencao'
        elif days <= 30:
            return 'proximo'
        else:
            return 'normal'

    def get_days_remaining(self):
        if self.no_expiration or not self.expiration_date:
            return None
        today = datetime.now(pytz.timezone('America/Sao_Paulo')).date()
        return (self.expiration_date - today).days

    def to_dict(self):
        return {
            'id': self.id,
            'barcode': self.barcode,
            'name': self.name,
            'brand': self.brand,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'category_icon': self.category.icon if self.category else '📦',
            'quantity': self.quantity,
            'unit': self.unit,
            'purchase_date': self.purchase_date.strftime('%d/%m/%Y') if self.purchase_date else None,
            'expiration_date': self.expiration_date.strftime('%d/%m/%Y') if self.expiration_date else None,
            'expiration_date_iso': self.expiration_date.isoformat() if self.expiration_date else None,
            'no_expiration': self.no_expiration,
            'storage_location': self.location.name if self.location else None,
            'storage_location_id': self.storage_location_id,
            'notes': self.notes,
            'status': self.get_status(),
            'days_remaining': self.get_days_remaining(),
            'created_at': self.created_at.strftime('%d/%m/%Y %H:%M'),
        }

class PushSubscription(db.Model):
    __tablename__ = 'push_subscriptions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    endpoint = db.Column(db.Text, nullable=False, unique=True)
    p256dh = db.Column(db.String(255), nullable=False)
    auth = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')))


class AlertLog(db.Model):
    """Evita enviar o mesmo alerta de vencimento mais de uma vez por dia."""
    __tablename__ = 'alert_logs'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    alert_key = db.Column(db.String(100), nullable=False)  # ex: 'vencidos_2026-08-19' ou 'prod_12_d3_2026-08-19'
    sent_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')))


class History(db.Model):
    __tablename__ = 'history'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product_id = db.Column(db.Integer, db.ForeignKey('products.id'), nullable=True)
    product_name = db.Column(db.String(150), nullable=False)
    action = db.Column(db.String(50), nullable=False)  # cadastrado, consumido, editado, excluido, estoque_adicionado
    quantity_change = db.Column(db.Float, default=0)
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(pytz.timezone('America/Sao_Paulo')))
