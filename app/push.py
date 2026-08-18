import json
import os
import threading
import time
from datetime import datetime

import pytz
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from pywebpush import webpush, WebPushException

from app import db
from app.models import User, Product, PushSubscription, AlertLog

bp = Blueprint('push', __name__, url_prefix='/api/push')

# Chave pública VAPID (a privada fica em arquivo, fora do código servido)
VAPID_PUBLIC_KEY = 'BEs0UBF3gFnd1a20qph1ZODsfXoyFDXVGn_JaJOYeKXcaPUoeho8BCDQ3BdR6LZyNjTVqpb7lny3x9xqO-oKnjM='
VAPID_CLAIMS = {'sub': 'mailto:contato@valifood.app'}

_PRIVATE_PEM = """-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg1caFzsPcLuCYk09q
7/ColUpwRkZjVvbmxrxgTlwzIUmhRANCAARLNFARd4BZ3dWttKqYdWTg7H16MhQ1
1Rp/yWiTmHil3Gj1KHoaPAQg0NwXUei2cjY01aqW+5Z8t8fcajvqCp4z
-----END PRIVATE KEY-----
"""


def _vapid_private_key_path():
    path = os.path.join(current_app.instance_path, 'vapid_private.pem')
    if not os.path.exists(path):
        os.makedirs(current_app.instance_path, exist_ok=True)
        with open(path, 'w') as f:
            f.write(_PRIVATE_PEM)
    return path


@bp.route('/public-key')
@login_required
def public_key():
    return jsonify({'publicKey': VAPID_PUBLIC_KEY})


@bp.route('/subscribe', methods=['POST'])
@login_required
def subscribe():
    data = request.get_json(silent=True) or {}
    subscription = data.get('subscription') or {}
    endpoint = subscription.get('endpoint')
    keys = subscription.get('keys') or {}
    p256dh = keys.get('p256dh')
    auth = keys.get('auth')

    if not endpoint or not p256dh or not auth:
        return jsonify({'error': 'Inscrição inválida'}), 400

    sub = PushSubscription.query.filter_by(endpoint=endpoint).first()
    if sub:
        sub.user_id = current_user.id
        sub.p256dh = p256dh
        sub.auth = auth
    else:
        sub = PushSubscription(
            user_id=current_user.id, endpoint=endpoint, p256dh=p256dh, auth=auth
        )
        db.session.add(sub)
    db.session.commit()
    return jsonify({'success': True})


@bp.route('/unsubscribe', methods=['POST'])
@login_required
def unsubscribe():
    data = request.get_json(silent=True) or {}
    endpoint = data.get('endpoint')
    if endpoint:
        PushSubscription.query.filter_by(endpoint=endpoint, user_id=current_user.id).delete()
        db.session.commit()
    return jsonify({'success': True})


@bp.route('/status')
@login_required
def status():
    data = request.get_json(silent=True) or {}
    endpoint = request.args.get('endpoint', '')
    exists = PushSubscription.query.filter_by(
        endpoint=endpoint, user_id=current_user.id
    ).first() is not None
    return jsonify({'subscribed': exists})


@bp.route('/test', methods=['POST'])
@login_required
def test_push():
    sent = send_push_to_user(
        current_user.id,
        title='ValiFood 🔔',
        body='Notificações ativadas! Você receberá alertas de vencimento aqui.',
        url='/'
    )
    if sent:
        return jsonify({'success': True, 'sent': sent})
    has_sub = PushSubscription.query.filter_by(user_id=current_user.id).first() is not None
    if has_sub:
        return jsonify({'error': 'Não foi possível entregar no dispositivo. Desative e ative as notificações novamente.'}), 400
    return jsonify({'error': 'Nenhum dispositivo inscrito. Ative as notificações primeiro.'}), 400


def send_push_to_user(user_id, title, body, url='/', tag='valifood'):
    """Envia push para todos os dispositivos inscritos do usuário."""
    subs = PushSubscription.query.filter_by(user_id=user_id).all()
    sent = 0
    for sub in subs:
        try:
            webpush(
                subscription_info={
                    'endpoint': sub.endpoint,
                    'keys': {'p256dh': sub.p256dh, 'auth': sub.auth},
                },
                data=json.dumps({'title': title, 'body': body, 'url': url, 'tag': tag}),
                vapid_private_key=_vapid_private_key_path(),
                vapid_claims=VAPID_CLAIMS,
            )
            sent += 1
        except WebPushException as e:
            # Inscrição expirada/inválida: remove
            status_code = getattr(e.response, 'status_code', None)
            if status_code in (404, 410):
                db.session.delete(sub)
                db.session.commit()
        except Exception:
            pass
    return sent


def _user_wants_alert(user, days):
    if days < 0:
        return user.alert_day_of  # vencidos entram junto com "no dia"
    return {
        0: user.alert_day_of,
        1: user.alert_1_day,
        3: user.alert_3_days,
        7: user.alert_7_days,
        14: user.alert_14_days,
        30: user.alert_30_days,
    }.get(days, False)


def check_and_send_alerts(app):
    """Verifica vencimentos de todos os usuários e envia pushes (1x ao dia cada)."""
    with app.app_context():
        tz = pytz.timezone('America/Sao_Paulo')
        today = datetime.now(tz).date()
        today_str = today.isoformat()

        users = User.query.filter_by(active=True).all()
        for user in users:
            products = Product.query.filter_by(user_id=user.id, active=True).all()

            # Agrupa produtos por janela de alerta
            buckets = {}  # days -> [nomes]
            for p in products:
                if p.no_expiration or not p.expiration_date:
                    continue
                days = (p.expiration_date - today).days
                key = days if days >= 0 else -1
                if _user_wants_alert(user, key):
                    buckets.setdefault(key, []).append(p.name)

            for days, names in buckets.items():
                alert_key = f'u{user.id}_d{days}_{today_str}'
                already = AlertLog.query.filter_by(user_id=user.id, alert_key=alert_key).first()
                if already:
                    continue

                count = len(names)
                if days < 0:
                    title = f'⚠️ {count} alimento(s) vencido(s)!'
                    body = ', '.join(names[:3]) + ('...' if count > 3 else '')
                elif days == 0:
                    title = f'🚨 {count} alimento(s) vencem HOJE!'
                    body = ', '.join(names[:3]) + ('...' if count > 3 else '')
                else:
                    title = f'⏰ {count} alimento(s) vencem em {days} dia(s)'
                    body = ', '.join(names[:3]) + ('...' if count > 3 else '')

                if send_push_to_user(user.id, title, body, url='/notifications/', tag=alert_key):
                    db.session.add(AlertLog(user_id=user.id, alert_key=alert_key))
                    db.session.commit()


def start_alert_scheduler(app, interval_seconds=3600):
    """Roda a verificação de alertas em background (a cada hora)."""
    def loop():
        while True:
            try:
                check_and_send_alerts(app)
            except Exception:
                pass
            time.sleep(interval_seconds)

    thread = threading.Thread(target=loop, daemon=True)
    thread.start()
    return thread
