from flask import Blueprint, render_template, redirect, url_for, flash, request, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db
from app.models import User

bp = Blueprint('auth', __name__, url_prefix='/auth')

@bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        user = User.query.filter_by(email=email).first()
        if user and user.check_password(password):
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            return redirect(next_page if next_page else url_for('dashboard.index'))
        else:
            flash('E-mail ou senha incorretos.', 'danger')

    return render_template('login.html')

@bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard.index'))

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm = request.form.get('confirm', '')

        if not name or not email or not password:
            flash('Preencha todos os campos obrigatórios.', 'warning')
            return render_template('register.html')

        if password != confirm:
            flash('As senhas não coincidem.', 'warning')
            return render_template('register.html')

        if len(password) < 6:
            flash('A senha deve ter pelo menos 6 caracteres.', 'warning')
            return render_template('register.html')

        if User.query.filter_by(email=email).first():
            flash('Este e-mail já está cadastrado.', 'warning')
            return render_template('register.html')

        user = User(name=name, email=email)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        # Criar locais padrão
        from app.models import StorageLocation
        default_locations = [
            ('Geladeira', '🧊'),
            ('Freezer', '❄️'),
            ('Armário', '🚪'),
            ('Despensa', '📦'),
            ('Prateleira', '📚'),
        ]
        for loc_name, loc_icon in default_locations:
            db.session.add(StorageLocation(name=loc_name, icon=loc_icon, user_id=user.id))
        db.session.commit()

        flash('Conta criada com sucesso! Faça login.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('register.html')

@bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você saiu da conta.', 'info')
    return redirect(url_for('auth.login'))
