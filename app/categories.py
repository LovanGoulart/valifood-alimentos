from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Category, Product

bp = Blueprint('categories', __name__, url_prefix='/categories')

@bp.route('/')
@login_required
def list_categories():
    categories = Category.query.filter(
        (Category.user_id == current_user.id) | (Category.user_id == None)
    ).all()
    return render_template('categories.html', categories=categories)

@bp.route('/new', methods=['POST'])
@login_required
def new_category():
    name = request.form.get('name', '').strip()
    icon = request.form.get('icon', '📦').strip()
    color = request.form.get('color', '#6366f1').strip()

    if not name:
        flash('Nome da categoria é obrigatório.', 'warning')
        return redirect(url_for('categories.list_categories'))

    cat = Category(name=name, icon=icon, color=color, user_id=current_user.id)
    db.session.add(cat)
    db.session.commit()
    flash('Categoria criada!', 'success')
    return redirect(url_for('categories.list_categories'))

@bp.route('/<int:id>/edit', methods=['POST'])
@login_required
def edit_category(id):
    cat = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    cat.name = request.form.get('name', '').strip()
    cat.icon = request.form.get('icon', '📦').strip()
    cat.color = request.form.get('color', '#6366f1').strip()
    db.session.commit()
    flash('Categoria atualizada!', 'success')
    return redirect(url_for('categories.list_categories'))

@bp.route('/<int:id>/delete', methods=['POST'])
@login_required
def delete_category(id):
    cat = Category.query.filter_by(id=id, user_id=current_user.id).first_or_404()
    # Reatribuir produtos para "Outros" (id 13 geralmente)
    others = Category.query.filter_by(name='Outros').first()
    if others:
        Product.query.filter_by(category_id=id).update({'category_id': others.id})
    db.session.delete(cat)
    db.session.commit()
    flash('Categoria removida.', 'info')
    return redirect(url_for('categories.list_categories'))
