"""
File Storage System - Main Application
A professional file management system with user authentication
"""

from flask import Flask, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import os
from pathlib import Path

# Import configurations and modules
from config import get_config
from models import SiteStats, db, User, File, ShareLink
from auth import auth_bp, login_required
from utils import (
    allowed_file, generate_safe_filename, get_file_extension,
    format_file_size, generate_share_token, calculate_expiry_date,
    ensure_upload_folder_exists, get_user_file_path, delete_file_safely,
    get_total_storage_used, generate_qr_code
)

# Initialize Flask app
app = Flask(__name__)

# Load configuration
config = get_config()
app.config.from_object(config)

# Initialize database
db.init_app(app)

# Register blueprints
app.register_blueprint(auth_bp)

# Ensure upload folder exists
ensure_upload_folder_exists()

# Create database tables
with app.app_context():
    db.create_all()


@app.route('/about')
def about():
    """Project introduction page"""
    features = [
        {
            'icon': '🔐',
            'title': 'Secure Authentication',
            'description': 'Password hashing using PBKDF2, session management, and secure login system'
        },
        {
            'icon': '📁',
            'title': 'File Management',
            'description': 'Upload, download, and delete files with validation and quota management'
        },
        {
            'icon': '🔗',
            'title': 'File Sharing',
            'description': 'Generate time-limited share links without requiring authentication from recipients'
        },
        {
            'icon': '💾',
            'title': 'Storage Tracking',
            'description': 'Monitor personal storage usage with visual progress indicators'
        },
        {
            'icon': '⚡',
            'title': 'Lightweight',
            'description': 'Fast, responsive application built with Flask and modern web technologies'
        },
        {
            'icon': '🛡️',
            'title': 'Secure Sharing',
            'description': 'Token-based sharing with encryption and access control'
        }
    ]
    
    return render_template('about.html', features=features)


@app.before_request
def track_visit():
    """Track every visit to the site"""
    stats = SiteStats.get_or_create()
    stats.increment_visits()
    stats.update_stats()

# Add this context processor to make stats available to ALL templates
@app.context_processor
def inject_stats():
    """Make site_stats available to all templates"""
    stats = SiteStats.get_or_create()
    stats.update_stats()
    return dict(site_stats=stats)


@app.route('/')
def index():
    """
    Home page
    If logged in, redirect to dashboard
    If not, redirect to login
    """
    if 'user_id' in session:
        return redirect(url_for('main.dashboard'))
    return redirect(url_for('auth.login'))


@app.route('/dashboard')
@login_required
def dashboard():
    """
    User dashboard - main page after login
    Shows user's files and storage statistics
    """
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if not user:
        flash('⚠️ User not found!', 'error')
        return redirect(url_for('auth.logout'))
    
    # Get user's files
    files = File.query.filter_by(user_id=user_id).order_by(File.uploaded_at.desc()).all()
    
    # Calculate statistics
    storage_used = user.get_storage_used_mb()
    file_count = user.get_file_count()
    
    context = {
        'user': user,
        'files': files,
        'storage_used_mb': storage_used,
        'file_count': file_count,
        'total_storage_mb': 500  # 500MB limit per user (you can change this)
    }
    
    return render_template('dashboard.html', **context)


@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload():
    """
    Handle file upload
    GET: Show upload form
    POST: Process file upload
    """
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    if request.method == 'POST':
        # Check if file is in request
        if 'file' not in request.files:
            flash('❌ No file selected!', 'error')
            return redirect(url_for('main.upload'))
        
        file = request.files['file']
        
        if file.filename == '':
            flash('❌ No file selected!', 'error')
            return redirect(url_for('main.upload'))
        
        # Validate file
        if not allowed_file(file.filename):
            flash('❌ File type not allowed!', 'error')
            return redirect(url_for('main.upload'))
        
        # Check file size
        file.seek(0, os.SEEK_END)
        file_size = file.tell()
        file.seek(0)
        
        if file_size > app.config['MAX_FILE_SIZE']:
            flash(f'❌ File too large! Maximum: {format_file_size(app.config["MAX_FILE_SIZE"])}', 'error')
            return redirect(url_for('main.upload'))
        
        # Check user storage quota
        user_storage = user.get_storage_used()
        if user_storage + file_size > 500 * 1024 * 1024:  # 500MB limit
            flash('❌ Storage quota exceeded!', 'error')
            return redirect(url_for('main.upload'))
        
        # Generate safe filename
        stored_filename = generate_safe_filename(file.filename)
        
        # Get user's file path
        user_file_path = get_user_file_path(user_id, stored_filename)
        
        # Save file
        file.save(user_file_path)
        
        # Create database record
        file_ext = get_file_extension(file.filename)
        new_file = File(
            filename=file.filename,
            stored_filename=stored_filename,
            file_size=file_size,
            file_type=file_ext,
            filepath=user_file_path,
            user_id=user_id,
            description=request.form.get('description', '')
        )
        
        db.session.add(new_file)
        db.session.commit()
        
        flash(f'✅ File "{file.filename}" uploaded successfully!', 'success')
        return redirect(url_for('main.dashboard'))
    
    return render_template('upload.html', user=user)


@app.route('/download/<int:file_id>')
@login_required
def download(file_id):
    """Download a file"""
    user_id = session.get('user_id')
    
    # Get file from database
    file = File.query.get(file_id)
    
    if not file:
        flash('❌ File not found!', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if user owns this file
    if file.user_id != user_id:
        flash('❌ You do not have permission to download this file!', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check if file exists on disk
    if not os.path.exists(file.filepath):
        flash('❌ File not found on server!', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Send file
    return send_from_directory(
        directory=os.path.dirname(file.filepath),
        path=os.path.basename(file.filepath),
        as_attachment=True,
        download_name=file.filename
    )


@app.route('/delete/<int:file_id>')
@login_required
def delete(file_id):
    """Delete a file"""
    user_id = session.get('user_id')
    
    # Get file
    file = File.query.get(file_id)
    
    if not file:
        flash('❌ File not found!', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Check ownership
    if file.user_id != user_id:
        flash('❌ You do not have permission to delete this file!', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Delete from disk
    delete_file_safely(file.filepath)
    
    # Delete from database
    db.session.delete(file)
    db.session.commit()
    
    flash(f'🗑️ File deleted successfully!', 'success')
    return redirect(url_for('main.dashboard'))


@app.route('/share/<int:file_id>')
@login_required
def create_share_link(file_id):
    """Create a shareable link for a file"""
    user_id = session.get('user_id')
    
    file = File.query.get(file_id)
    
    if not file or file.user_id != user_id:
        flash('❌ File not found!', 'error')
        return redirect(url_for('main.dashboard'))
    
    # Generate share token
    token = generate_share_token()
    expiry = calculate_expiry_date(days=7)  # 7 days expiry
    
    share_link = ShareLink(
        token=token,
        file_id=file_id,
        expires_at=expiry
    )
    
    db.session.add(share_link)
    db.session.commit()
    
    share_url = url_for('main.view_shared_file', token=token, _external=True)
    
    # Generate QR Code
    qr_code = generate_qr_code(share_url)
    
    return render_template('share_modal.html', 
                          share_url=share_url, 
                          qr_code=qr_code,
                          file_name=file.filename)


@app.route('/shared/<token>')
def view_shared_file(token):
    """View or download a shared file"""
    
    share_link = ShareLink.query.filter_by(token=token).first()
    
    if not share_link:
        flash('❌ Invalid share link!', 'error')
        return redirect(url_for('auth.login'))
    
    if not share_link.is_valid():
        flash('❌ This share link has expired!', 'error')
        return redirect(url_for('auth.login'))
    
    file = share_link.file
    
    # Increment access count
    share_link.access_count += 1
    db.session.commit()
    
    return send_from_directory(
        directory=os.path.dirname(file.filepath),
        path=os.path.basename(file.filepath),
        as_attachment=True,
        download_name=file.filename
    )


@app.route('/stats')
@login_required
def stats():
    """Show user statistics"""
    user_id = session.get('user_id')
    user = User.query.get(user_id)
    
    total_storage = get_total_storage_used()
    
    context = {
        'user': user,
        'total_storage_mb': total_storage,
        'user_storage_mb': user.get_storage_used_mb(),
        'file_count': user.get_file_count()
    }
    
    return render_template('stats.html', **context)


# Create main blueprint for main routes
from flask import Blueprint
main_bp = Blueprint('main', __name__)

# Move routes to blueprint
app.add_url_rule('/dashboard', 'main.dashboard', dashboard)
app.add_url_rule('/upload', 'main.upload', upload, methods=['GET', 'POST'])
app.add_url_rule('/download/<int:file_id>', 'main.download', download)
app.add_url_rule('/delete/<int:file_id>', 'main.delete', delete)
app.add_url_rule('/share/<int:file_id>', 'main.create_share_link', create_share_link)
app.add_url_rule('/shared/<token>', 'main.view_shared_file', view_shared_file)
app.add_url_rule('/stats', 'main.stats', stats)


@app.context_processor
def inject_user():
    """Make user available in all templates"""
    user = None
    if 'user_id' in session:
        user = User.query.get(session['user_id'])
    return dict(current_user=user)


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return render_template('404.html'), 404


@app.errorhandler(500)
def server_error(error):
    """Handle 500 errors"""
    return render_template('500.html'), 500


if __name__ == '__main__':
    app.run(debug=True, port=5000)