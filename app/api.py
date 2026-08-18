from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Product, Category, StorageLocation, History
from datetime import datetime
import pytz

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/products')
@login_required
def get_products():
    search = request.args.get('q', '').strip()
    category_id = request.args.get('category', type=int)

    query = Product.query.filter_by(user_id=current_user.id, active=True)

    if category_id:
        query = query.filter_by(category_id=category_id)
    if search:
        query = query.filter(
            db.or_(
                Product.name.ilike(f'%{search}%'),
                Product.brand.ilike(f'%{search}%'),
                Product.barcode.ilike(f'%{search}%')
            )
        )

    products = query.all()
    return jsonify([p.to_dict() for p in products])

@bp.route('/products/<int:id>')
@login_required
def get_product(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    return jsonify(product.to_dict())

@bp.route('/products', methods=['POST'])
@login_required
def create_product():
    data = request.get_json()

    name = data.get('name', '').strip()
    if not name:
        return jsonify({'error': 'Nome é obrigatório'}), 400

    expiration_str = data.get('expiration_date', '')
    expiration_date = None
    if expiration_str and not data.get('no_expiration'):
        try:
            expiration_date = datetime.strptime(expiration_str, '%d/%m/%Y').date()
        except:
            return jsonify({'error': 'Data inválida. Use DD/MM/AAAA'}), 400

    product = Product(
        user_id=current_user.id,
        barcode=data.get('barcode'),
        name=name,
        brand=data.get('brand'),
        category_id=data.get('category_id'),
        quantity=float(data.get('quantity', 1)),
        unit=data.get('unit', 'unidade'),
        expiration_date=expiration_date,
        no_expiration=data.get('no_expiration', False),
        storage_location_id=data.get('location_id'),
        notes=data.get('notes')
    )
    db.session.add(product)
    db.session.commit()

    history = History(
        user_id=current_user.id,
        product_id=product.id,
        product_name=product.name,
        action='cadastrado',
        quantity_change=product.quantity
    )
    db.session.add(history)
    db.session.commit()

    return jsonify(product.to_dict()), 201

@bp.route('/products/<int:id>/consume', methods=['POST'])
@login_required
def api_consume(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    amount = float(data.get('amount', 1))

    if product.quantity > 0:
        product.quantity = max(0, product.quantity - amount)
        db.session.commit()

        history = History(
            user_id=current_user.id,
            product_id=product.id,
            product_name=product.name,
            action='consumido',
            quantity_change=-amount
        )
        db.session.add(history)
        db.session.commit()

        return jsonify({'success': True, 'new_quantity': product.quantity})
    return jsonify({'error': 'Quantidade insuficiente'}), 400

@bp.route('/products/<int:id>/add-stock', methods=['POST'])
@login_required
def api_add_stock(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    data = request.get_json()
    amount = float(data.get('amount', 1))

    product.quantity += amount
    db.session.commit()

    history = History(
        user_id=current_user.id,
        product_id=product.id,
        product_name=product.name,
        action='estoque_adicionado',
        quantity_change=amount
    )
    db.session.add(history)
    db.session.commit()

    return jsonify({'success': True, 'new_quantity': product.quantity})

@bp.route('/barcode/lookup', methods=['POST'])
@login_required
def barcode_lookup():
    data = request.get_json()
    barcode = data.get('barcode', '').strip()

    if not barcode:
        return jsonify({'found': False})

    product = Product.query.filter_by(
        user_id=current_user.id, barcode=barcode, active=True
    ).first()
    if product:
        return jsonify({'found': True, 'product': product.to_dict()})

    # Produto excluído com este código: não aparece no sistema, mas devolve
    # os dados mantidos (nome, marca, categoria) para pré-preencher o cadastro.
    inactive = Product.query.filter_by(
        user_id=current_user.id, barcode=barcode, active=False
    ).first()
    if inactive:
        return jsonify({
            'found': False,
            'barcode': barcode,
            'prefill': {
                'name': inactive.name,
                'brand': inactive.brand,
                'category_id': inactive.category_id,
                'category_name': inactive.category.name if inactive.category else None,
            }
        })

    return jsonify({'found': False, 'barcode': barcode})

@bp.route('/categories')
@login_required
def get_categories():
    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()
    return jsonify([{'id': c.id, 'name': c.name, 'icon': c.icon, 'color': c.color} for c in categories])

@bp.route('/locations')
@login_required
def get_locations():
    locations = StorageLocation.query.filter_by(user_id=current_user.id).all()
    return jsonify([{'id': l.id, 'name': l.name, 'icon': l.icon} for l in locations])

@bp.route('/alerts')
@login_required
def get_alerts():
    tz = pytz.timezone('America/Sao_Paulo')
    today = datetime.now(tz).date()

    products = Product.query.filter_by(user_id=current_user.id, active=True).all()
    alerts = []

    for p in products:
        if p.no_expiration or not p.expiration_date:
            continue
        days = (p.expiration_date - today).days
        if days < 0 or days <= 7:
            alerts.append({
                'product': p.to_dict(),
                'days': days,
                'level': p.get_status()
            })

    return jsonify(alerts)
