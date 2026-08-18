from flask import Blueprint, render_template
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import pytz
from app import db
from app.models import Product, Category, History

bp = Blueprint('dashboard', __name__)

@bp.route('/')
@bp.route('/dashboard')
@login_required
def index():
    tz = pytz.timezone('America/Sao_Paulo')
    today = datetime.now(tz).date()

    products = Product.query.filter_by(user_id=current_user.id, active=True).all()

    total = len(products)
    vencidos = 0
    vence_hoje = 0
    vence_7 = 0
    vence_30 = 0
    consuma_primeiro = []

    for p in products:
        if p.no_expiration or not p.expiration_date:
            continue
        days = (p.expiration_date - today).days

        if days < 0:
            vencidos += 1
        if days == 0:
            vence_hoje += 1
        if 0 <= days <= 7:
            vence_7 += 1
        if 0 <= days <= 30:
            vence_30 += 1

        if days <= 7 and days >= 0:
            consuma_primeiro.append(p)

    consuma_primeiro.sort(key=lambda x: x.expiration_date)
    consuma_primeiro = consuma_primeiro[:5]

    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()

    # Histórico recente
    recent_history = History.query.filter_by(user_id=current_user.id).order_by(History.created_at.desc()).limit(10).all()

    return render_template('dashboard.html',
        now=datetime.now(tz),
        total=total,
        vencidos=vencidos,
        vence_hoje=vence_hoje,
        vence_7=vence_7,
        vence_30=vence_30,
        consuma_primeiro=consuma_primeiro,
        categories=categories,
        recent_history=recent_history
    )