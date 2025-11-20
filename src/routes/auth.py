"""
Authentication Routes
Handles user login, logout, and registration
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from models.user import User

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        return redirect(url_for('web.dashboard'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Username and password are required.', 'error')
            return redirect(url_for('auth.login'))

        user = User.verify_credentials(username, password)

        if user is None:
            flash('Invalid username or password.', 'error')
            return redirect(url_for('auth.login'))

        login_user(user, remember=request.form.get('remember_me'))
        next_page = request.args.get('next')

        if not next_page or not next_page.startswith('/'):
            next_page = url_for('web.dashboard')

        return redirect(next_page)

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration (admin only)"""
    # TODO: Implement admin-only registration
    # For now, return 404
    return render_template('error.html', error='Registration disabled'), 404
