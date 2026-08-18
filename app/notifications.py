from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import Product, History
from datetime import datetime, timedelta
import pytz

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

@bp.route('/')
@login_required
def index():
    tz = pytz.timezone('America/Sao_Paulo')
    today = datetime.now(tz).date()

    products = Product.query.filter_by(user_id=current_user.id, active=True).all()
    alerts = []

    for p in products:
        if p.no_expiration or not p.expiration_date:
            continue
        days = (p.expiration_date - today).days

        alert_level = None
        if days < 0:
            alert_level = 'vencido'
        elif days == 0:
            alert_level = 'vence_hoje'
        elif days <= 3:
            alert_level = 'urgente'
        elif days <= 7:
            alert_level = 'atencao'
        elif days <= 30:
            alert_level = 'proximo'

        if alert_level:
            alerts.append({
                'product': p,
                'days': days,
                'level': alert_level
            })

    alerts.sort(key=lambda x: x['days'])

    return render_template('notifications.html', alerts=alerts)

@bp.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    if request.method == 'POST':
        current_user.alert_day_of = request.form.get('alert_day_of') == 'on'
        current_user.alert_1_day = request.form.get('alert_1_day') == 'on'
        current_user.alert_3_days = request.form.get('alert_3_days') == 'on'
        current_user.alert_7_days = request.form.get('alert_7_days') == 'on'
        current_user.alert_14_days = request.form.get('alert_14_days') == 'on'
        current_user.alert_30_days = request.form.get('alert_30_days') == 'on'
        db.session.commit()
        flash('Preferências de notificação salvas!', 'success')
        return redirect(url_for('notifications.settings'))

    return render_template('settings.html')
