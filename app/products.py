from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from datetime import datetime, timedelta
import pytz
from app import db
from app.models import Product, Category, History, StorageLocation

bp = Blueprint('products', __name__)


@bp.route('/produtos')
@login_required
def list_products():
    tz = pytz.timezone('America/Sao_Paulo')
    today = datetime.now(tz).date()

    status = request.args.get('status', 'todos')
    search = request.args.get('search', '')
    category_id = request.args.get('category', type=int)

    query = Product.query.filter_by(user_id=current_user.id, active=True)

    if search:
        query = query.filter(Product.name.ilike(f'%{search}%'))

    if category_id:
        query = query.filter_by(category_id=category_id)

    if status == 'vencido':
        query = query.filter(
            Product.expiration_date.isnot(None),
            Product.no_expiration == False,
            Product.expiration_date < today
        )
    elif status == 'vence_hoje':
        query = query.filter(
            Product.expiration_date.isnot(None),
            Product.no_expiration == False,
            Product.expiration_date == today
        )
    elif status == 'atencao':
        date_7 = today + timedelta(days=7)
        query = query.filter(
            Product.expiration_date.isnot(None),
            Product.no_expiration == False,
            Product.expiration_date >= today,
            Product.expiration_date <= date_7
        )
    elif status == 'proximo':
        date_30 = today + timedelta(days=30)
        query = query.filter(
            Product.expiration_date.isnot(None),
            Product.no_expiration == False,
            Product.expiration_date >= today,
            Product.expiration_date <= date_30
        )
    elif status == 'sem_validade':
        query = query.filter(
            (Product.expiration_date.is_(None)) | (Product.no_expiration == True)
        )

    products = query.order_by(Product.expiration_date.asc().nullslast(), Product.name.asc()).all()

    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()

    return render_template('products.html',
        products=products,
        categories=categories,
        filter_status=status,
        search=search
    )


@bp.route('/produtos/<int:id>')
@login_required
def detail(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    history = History.query.filter_by(product_id=id).order_by(History.created_at.desc()).all()
    return render_template('product_detail.html', product=product, history=history)


@bp.route('/produtos/novo', methods=['GET', 'POST'])
@bp.route('/produtos/novo/<barcode>', methods=['GET', 'POST'])
@login_required
def new_product(barcode=None):
    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()
    
    locations = StorageLocation.query.filter_by(user_id=current_user.id).all()

    existing = None
    reactivate = None
    if barcode:
        existing = Product.query.filter_by(
            barcode=barcode, user_id=current_user.id
        ).first()
        if existing and existing.active:
            # Produto ativo com este código: mostra o cartão de "já cadastrado"
            return render_template('product_form.html',
                barcode=barcode,
                existing=existing,
                categories=categories,
                locations=locations
            )
        if existing and not existing.active:
            # Produto excluído: pré-preenche nome, marca, categoria e código;
            # o usuário completa quantidade, validade e o restante.
            reactivate = existing
            existing = None

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        brand = request.form.get('brand', '').strip()
        barcode_input = request.form.get('barcode', '').strip()
        category_id = request.form.get('category_id', type=int)
        location_id = request.form.get('location_id', type=int)
        quantity = request.form.get('quantity', type=float, default=1)
        unit = request.form.get('unit', 'unidade')
        no_expiration = bool(request.form.get('no_expiration'))
        notes = request.form.get('notes', '').strip()
        reactivate_id = request.form.get('reactivate_id', type=int)

        expiration_date = None
        if not no_expiration:
            date_str = request.form.get('expiration_date', '')
            if date_str:
                try:
                    expiration_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Data de validade inválida.', 'danger')
                    return redirect(url_for('products.new_product', barcode=barcode_input))

        # Recadastro de um produto excluído: reativa o registro antigo
        # em vez de criar duplicata.
        if reactivate_id:
            product = Product.query.filter_by(
                id=reactivate_id, user_id=current_user.id, active=False
            ).first()
            if product:
                product.name = name
                product.brand = brand or None
                product.barcode = barcode_input or None
                product.category_id = category_id or None
                product.storage_location_id = location_id or None
                product.quantity = quantity
                product.unit = unit
                product.expiration_date = expiration_date
                product.no_expiration = no_expiration
                product.notes = notes or None
                product.active = True
                db.session.commit()

                history = History(
                    user_id=current_user.id,
                    product_id=product.id,
                    product_name=product.name,
                    action='cadastrado',
                    quantity_change=quantity,
                    notes='Recadastrado a partir de produto excluído'
                )
                db.session.add(history)
                db.session.commit()

                flash(f'"{name}" cadastrado com sucesso!', 'success')
                return redirect(url_for('dashboard.index'))

        product = Product(
            user_id=current_user.id,
            name=name,
            brand=brand or None,
            barcode=barcode_input or None,
            category_id=category_id or None,
            storage_location_id=location_id or None,
            quantity=quantity,
            unit=unit,
            expiration_date=expiration_date,
            no_expiration=no_expiration,
            notes=notes or None
        )
        db.session.add(product)
        db.session.commit()

        history = History(
            user_id=current_user.id,
            product_id=product.id,
            product_name=product.name,
            action='cadastrado',
            quantity_change=quantity
        )
        db.session.add(history)
        db.session.commit()

        flash(f'"{name}" cadastrado com sucesso!', 'success')
        return redirect(url_for('dashboard.index'))

    return render_template('product_form.html',
        barcode=barcode,
        existing=None,
        reactivate=reactivate,
        categories=categories,
        locations=locations
    )


@bp.route('/produtos/<int:id>/editar', methods=['GET', 'POST'])
@login_required
def edit(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()
    
    locations = StorageLocation.query.filter_by(user_id=current_user.id).all()

    if request.method == 'POST':
        product.name = request.form.get('name', '').strip()
        product.brand = request.form.get('brand', '').strip() or None
        product.barcode = request.form.get('barcode', '').strip() or None
        product.category_id = request.form.get('category_id', type=int) or None
        product.storage_location_id = request.form.get('location_id', type=int) or None
        product.quantity = request.form.get('quantity', type=float, default=1)
        product.unit = request.form.get('unit', 'unidade')
        product.no_expiration = bool(request.form.get('no_expiration'))
        product.notes = request.form.get('notes', '').strip() or None

        if not product.no_expiration:
            date_str = request.form.get('expiration_date', '')
            if date_str:
                try:
                    product.expiration_date = datetime.strptime(date_str, '%Y-%m-%d').date()
                except ValueError:
                    flash('Data de validade inválida.', 'danger')
                    return redirect(url_for('products.edit', id=id))
            else:
                product.expiration_date = None
        else:
            product.expiration_date = None

        db.session.commit()

        history = History(
            user_id=current_user.id,
            product_id=product.id,
            product_name=product.name,
            action='editado'
        )
        db.session.add(history)
        db.session.commit()

        flash(f'"{product.name}" atualizado com sucesso!', 'success')
        return redirect(url_for('products.detail', id=id))

    return render_template('product_form.html',
        product=product,
        categories=categories,
        locations=locations
    )


@bp.route('/produtos/<int:id>/consumir', methods=['POST'])
@login_required
def consume(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    amount = request.form.get('amount', type=float, default=1)

    if product.quantity >= amount:
        product.quantity -= amount
        if product.quantity <= 0:
            product.active = False

        db.session.commit()

        history = History(
            user_id=current_user.id,
            product_id=product.id,
            product_name=product.name,
            action='consumido',
            quantity_change=-amount,
            notes=f'{amount} {product.unit}'
        )
        db.session.add(history)
        db.session.commit()

        flash(f'Consumido {int(amount)} {product.unit} de "{product.name}"', 'success')
    else:
        flash('Quantidade insuficiente em estoque.', 'danger')

    return redirect(url_for('products.detail', id=id))


@bp.route('/produtos/<int:id>/estoque', methods=['POST'])
@login_required
def add_stock(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    amount = request.form.get('amount', type=float, default=1)

    product.quantity += amount
    if not product.active:
        product.active = True

    db.session.commit()

    history = History(
        user_id=current_user.id,
        product_id=product.id,
        product_name=product.name,
        action='estoque_adicionado',
        quantity_change=amount,
        notes=f'{amount} {product.unit}'
    )
    db.session.add(history)
    db.session.commit()

    flash(f'Adicionado {int(amount)} {product.unit} de "{product.name}"', 'success')
    return redirect(url_for('products.detail', id=id))


@bp.route('/produtos/<int:id>/excluir', methods=['POST'])
@login_required
def delete(id):
    product = Product.query.filter_by(id=id, user_id=current_user.id).first_or_404()

    history = History(
        user_id=current_user.id,
        product_id=product.id,
        product_name=product.name,
        action='excluido',
        quantity_change=-product.quantity
    )
    db.session.add(history)

    # Mantém nome, marca, categoria e código de barras para pré-preencher
    # um futuro recadastro; zera quantidade e remove a validade.
    product.quantity = 0
    product.expiration_date = None
    product.active = False
    db.session.commit()

    flash(f'"{product.name}" removido com sucesso.', 'success')
    return redirect(url_for('products.list_products'))


@bp.route('/produtos/excluir-por-codigo', methods=['POST'])
@login_required
def delete_by_barcode():
    barcode = request.form.get('barcode', '').strip()
    if not barcode:
        flash('Código de barras não informado.', 'warning')
        return redirect(url_for('products.list_products'))

    product = Product.query.filter_by(
        barcode=barcode, user_id=current_user.id, active=True
    ).first()

    if not product:
        flash('Nenhum produto ativo encontrado com este código de barras.', 'warning')
        return redirect(url_for('products.list_products'))

    history = History(
        user_id=current_user.id,
        product_id=product.id,
        product_name=product.name,
        action='excluido',
        quantity_change=-product.quantity
    )
    db.session.add(history)

    # Mantém nome, marca, categoria e código de barras para pré-preencher
    # um futuro recadastro; zera quantidade e remove a validade.
    product.quantity = 0
    product.expiration_date = None
    product.active = False
    db.session.commit()

    flash(f'"{product.name}" removido com sucesso.', 'success')
    return redirect(url_for('products.list_products'))


@bp.route('/produtos/consumir-por-codigo', methods=['POST'])
@login_required
def consume_by_barcode():
    barcode = request.form.get('barcode', '').strip()
    amount = request.form.get('amount', type=float, default=1)

    if not barcode:
        flash('Código de barras não informado.', 'warning')
        return redirect(url_for('products.list_products'))

    product = Product.query.filter_by(
        barcode=barcode, user_id=current_user.id, active=True
    ).first()

    if not product:
        flash('Nenhum produto ativo encontrado com este código de barras.', 'warning')
        return redirect(url_for('products.list_products'))

    if product.quantity >= amount:
        product.quantity -= amount
        if product.quantity <= 0:
            product.active = False

        db.session.commit()

        history = History(
            user_id=current_user.id,
            product_id=product.id,
            product_name=product.name,
            action='consumido',
            quantity_change=-amount,
            notes=f'{amount} {product.unit}'
        )
        db.session.add(history)
        db.session.commit()

        flash(f'Baixa de {int(amount)} {product.unit} de "{product.name}" realizada!', 'success')
    else:
        flash('Quantidade insuficiente em estoque.', 'danger')

    return redirect(url_for('products.list_products'))