"""
Authentication Module
Handles user registration, login, and session management
"""

from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from datetime import datetime, timezone
from models import db, User

# Create blueprint for authentication routes
auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """
    Register a new user account
    GET: Show registration form
    POST: Process registration form
    """
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        if not all([username, email, password, confirm_password]):
            flash('⚠️ All fields are required!', 'error')
            return redirect(url_for('auth.register'))
        
        if len(username) < 3:
            flash('❌ Username must be at least 3 characters!', 'error')
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash('❌ Password must be at least 6 characters!', 'error')
            return redirect(url_for('auth.register'))
        
        if password != confirm_password:
            flash('❌ Passwords do not match!', 'error')
            return redirect(url_for('auth.register'))
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('❌ Username already taken!', 'error')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('❌ Email already registered!', 'error')
            return redirect(url_for('auth.register'))
        
        # Create new user
        user = User(username=username, email=email)
        user.set_password(password)  # Hash the password
        
        db.session.add(user)
        db.session.commit()
        
        flash('✅ Registration successful! Please login.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        
        if not username or not password:
            flash('⚠️ Username and password required!', 'error')
            return redirect(url_for('auth.login'))
        
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            session['user_id'] = user.id
            session['username'] = user.username
            session.permanent = True
            
            # FIX THIS LINE:
            user.last_login = datetime.now(timezone.utc)  # Changed from utcnow()
            db.session.commit()
            
            flash(f'✅ Welcome back, {user.username}!', 'success')
            return redirect(url_for('main.dashboard'))
        else:
            flash('❌ Invalid username or password!', 'error')
            return redirect(url_for('auth.login'))
    
    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    """Logout user and clear session"""
    username = session.get('username', 'User')
    session.clear()
    flash(f'👋 Goodbye, {username}!', 'success')
    return redirect(url_for('auth.login'))


def login_required(f):
    """
    Decorator to require login for a route
    Usage: @login_required
    """
    from functools import wraps
    
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('⚠️ Please login first!', 'warning')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    
    return decorated_function