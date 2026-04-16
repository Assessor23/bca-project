"""
Utility Functions
Helper functions for file operations, validation, etc.
"""

import os
import secrets
import string
import qrcode
import base64
from io import BytesIO
from werkzeug.utils import secure_filename
from datetime import datetime, timedelta, timezone
from config import Config

# Rest of the code...

def allowed_file(filename):
    """
    Check if file extension is allowed
    Returns: Boolean
    """
    if '.' not in filename:
        return False
    
    ext = filename.rsplit('.', 1)[1].lower()
    return ext in Config.ALLOWED_EXTENSIONS


def generate_safe_filename(filename):
    """
    Generate a safe filename for storage
    Prevents directory traversal attacks
    Returns: Sanitized filename
    """
    # Get original extension
    ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
    
    # Generate unique filename using timestamp + random string
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S_')
    random_string = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(8))
    
    new_filename = timestamp + random_string
    if ext:
        new_filename += '.' + ext
    
    return new_filename


def get_file_extension(filename):
    """
    Extract file extension from filename
    Returns: Extension without dot
    """
    if '.' in filename:
        return filename.rsplit('.', 1)[1].lower()
    return ''


def format_file_size(size_in_bytes):
    """
    Convert bytes to human-readable format
    Returns: Formatted string (e.g., "2.5 MB")
    """
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    
    return f"{size_in_bytes:.2f} PB"


def generate_share_token(length=20):
    """
    Generate a secure random token for sharing
    Returns: Random token string
    """
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))


def calculate_expiry_date(days):
    """Calculate expiry date based on number of days"""
    from datetime import timezone
    return datetime.now(timezone.utc) + timedelta(days=days)


def ensure_upload_folder_exists():
    """Create upload folder if it doesn't exist"""
    if not os.path.exists(Config.UPLOAD_FOLDER):
        os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)


def get_user_file_path(user_id, filename):
    """
    Get the full path for storing a user's file
    Organizes files by user_id for better management
    Returns: Full file path
    """
    user_folder = os.path.join(Config.UPLOAD_FOLDER, str(user_id))
    
    if not os.path.exists(user_folder):
        os.makedirs(user_folder, exist_ok=True)
    
    return os.path.join(user_folder, filename)


def delete_file_safely(filepath):
    """
    Safely delete a file
    Returns: Boolean indicating success
    """
    try:
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
    except Exception as e:
        print(f"Error deleting file: {e}")
    
    return False


def get_total_storage_used():
    """
    Calculate total storage used by all users
    Returns: Size in MB
    """
    total = 0
    for root, dirs, files in os.walk(Config.UPLOAD_FOLDER):
        for file in files:
            filepath = os.path.join(root, file)
            if os.path.exists(filepath):
                total += os.path.getsize(filepath)
    
    return round(total / (1024 * 1024), 2)


def generate_qr_code(share_url):
    """Generate QR code and return as base64 for HTML embedding"""
    qr = qrcode.QRCode(
    version=1,
    error_correction=qrcode.constants.ERROR_CORRECT_H, 
    box_size=10,
    border=4,
    )
    
    qr.add_data(share_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to base64 so we can embed in HTML
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    buffer.seek(0)
    img_base64 = base64.b64encode(buffer.getvalue()).decode()
    
    return f"data:image/png;base64,{img_base64}"