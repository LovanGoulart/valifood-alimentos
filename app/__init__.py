import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'valifood-dev-secret-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
        'DATABASE_URL', 'sqlite:///valifood.db'
    )
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Faça login para continuar.'
    login_manager.login_message_category = 'info'

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    from app import auth, products, categories, dashboard, notifications, api, push
    app.register_blueprint(auth.bp)
    app.register_blueprint(products.bp)
    app.register_blueprint(categories.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(api.bp)
    app.register_blueprint(push.bp)

    # Service worker precisa ser servido na raiz para controlar o app inteiro
    from flask import send_from_directory

    @app.route('/service-worker.js')
    def service_worker():
        return send_from_directory(
            app.static_folder, 'service-worker.js',
            mimetype='application/javascript'
        )

    with app.app_context():
        db.create_all()
        _seed_default_categories()

    # Agendador de alertas push (1x por hora)
    if os.environ.get('VALIFOOD_DISABLE_SCHEDULER') != '1':
        push.start_alert_scheduler(app)

    return app


def _seed_default_categories():
    from app.models import Category
    defaults = [
        ('Laticínios', '🥛', '#3b82f6'),
        ('Carnes', '🥩', '#ef4444'),
        ('Frutas', '🍎', '#f59e0b'),
        ('Verduras', '🥬', '#10b981'),
        ('Grãos e Cereais', '🌾', '#a16207'),
        ('Padaria', '🍞', '#d97706'),
        ('Bebidas', '🥤', '#8b5cf6'),
        ('Congelados', '🧊', '#06b6d4'),
        ('Enlatados', '🥫', '#64748b'),
        ('Temperos', '🧂', '#f97316'),
        ('Doces', '🍬', '#ec4899'),
        ('Limpeza', '🧼', '#14b8a6'),
        ('Outros', '📦', '#6366f1'),
    ]
    for name, icon, color in defaults:
        if not Category.query.filter_by(name=name, user_id=None).first():
            db.session.add(Category(name=name, icon=icon, color=color, user_id=None))
    db.session.commit()
