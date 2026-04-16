"""
Configuration file for the File Storage System
This keeps all settings in one place for easy management
"""

import os
from datetime import timedelta

class Config:
    """Base configuration - used by all environments"""
    
    # Application secret key for session management
    # In production, use environment variables
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    # SQLite database stored in project root
    SQLALCHEMY_DATABASE_URI = 'sqlite:///database.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Adding this line to use ngrok's forwarded headers
    PREFERRED_URL_SCHEME = 'https'  # ngrok uses HTTPS

    # Upload settings
    UPLOAD_FOLDER = 'uploads'
    MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB
    ALLOWED_EXTENSIONS = {
        'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif',
        'doc', 'docx', 'xls', 'xlsx', 'zip', 'mp3',
        'mp4', 'avi', 'mov', 'csv', 'json'
    }
    
    # Session settings
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    
    # Pagination
    ITEMS_PER_PAGE = 10
    
    # File sharing
    SHARE_LINK_EXPIRY_DAYS = 7

class DevelopmentConfig(Config):
    """Development environment settings"""
    DEBUG = True
    TESTING = False

class ProductionConfig(Config):
    """Production environment settings"""
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True

class TestingConfig(Config):
    """Testing environment settings"""
    DEBUG = True
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

# Select config based on environment
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}

def get_config(env=None):
    """Get config object based on environment"""
    if env is None:
        env = os.environ.get('FLASK_ENV', 'development')
    return config.get(env, config['default'])