"""
Database Models - Defines the structure of our database tables
Using SQLAlchemy ORM for object-relational mapping
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta, timezone
import os

db = SQLAlchemy()

class User(db.Model):
    """User model - represents a user account"""
    
    __tablename__ = 'users'
    
    # Primary key - unique identifier for each user
    id = db.Column(db.Integer, primary_key=True)
    
    # Username - must be unique
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    
    # Email - must be unique
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    
    # Password hash - we never store plain passwords!
    password_hash = db.Column(db.String(255), nullable=False)
    
    # Account creation timestamp
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Last login timestamp
    last_login = db.Column(db.DateTime)
    
    # Relationship to files - one user has many files
    files = db.relationship('File', backref='owner', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash and store password securely"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password against stored hash"""
        return check_password_hash(self.password_hash, password)
    
    def get_storage_used(self):
        """Calculate total storage used by this user in bytes"""
        total = 0
        for file in self.files:
            if os.path.exists(file.filepath):
                total += os.path.getsize(file.filepath)
        return total
    
    def get_storage_used_mb(self):
        """Get storage used in MB"""
        return round(self.get_storage_used() / (1024 * 1024), 2)
    
    def get_file_count(self):
        """Get total number of files owned by user"""
        return len(self.files)
    
    def __repr__(self):
        return f'<User {self.username}>'


class File(db.Model):
    """File model - represents a file uploaded by a user"""
    
    __tablename__ = 'files'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Original filename
    filename = db.Column(db.String(255), nullable=False)
    
    # Stored filename (sanitized)
    stored_filename = db.Column(db.String(255), unique=True, nullable=False)
    
    # File size in bytes
    file_size = db.Column(db.Integer, nullable=False)
    
    # File type/extension
    file_type = db.Column(db.String(50), nullable=False)
    
    # Full file path
    filepath = db.Column(db.String(500), nullable=False)
    
    # Upload timestamp
    uploaded_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc), index=True)
    
    # File description/notes
    description = db.Column(db.Text)
    
    # Foreign key - which user owns this file
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    
    # Relationship to share links
    share_links = db.relationship('ShareLink', backref='file', lazy=True, cascade='all, delete-orphan')
    
    def get_file_size_formatted(self):
        """Return file size in human-readable format"""
        size = self.file_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.2f} {unit}"
            size /= 1024
        return f"{size:.2f} TB"
    
    def is_image(self):
        """Check if file is an image"""
        return self.file_type.lower() in ['jpg', 'jpeg', 'png', 'gif', 'bmp']
    
    def is_document(self):
        """Check if file is a document"""
        return self.file_type.lower() in ['pdf', 'doc', 'docx', 'txt', 'xls', 'xlsx']
    
    def is_video(self):
        """Check if file is a video"""
        return self.file_type.lower() in ['mp4', 'avi', 'mov', 'mkv']
    
    def __repr__(self):
        return f'<File {self.filename}>'


class ShareLink(db.Model):
    """ShareLink model - tracks shareable links for files"""
    
    __tablename__ = 'share_links'
    
    # Primary key
    id = db.Column(db.Integer, primary_key=True)
    
    # Unique share token (like a secret link)
    token = db.Column(db.String(100), unique=True, nullable=False, index=True)
    
    # Foreign key - which file is being shared
    file_id = db.Column(db.Integer, db.ForeignKey('files.id'), nullable=False, index=True)
    
    # When the share link was created
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    # When the share link expires
    expires_at = db.Column(db.DateTime, nullable=False)
    
    # How many times this link has been accessed
    access_count = db.Column(db.Integer, default=0)
    
    # Is the link still active?
    is_active = db.Column(db.Boolean, default=True)
    
    def is_expired(self):
        """Check if share link has expired"""
        return datetime.now(timezone.utc) > self.expires_at
    
    def is_valid(self):
        """Check if share link is still valid"""
        from datetime import timezone
        # Compare both as timezone-aware UTC
        return datetime.now(timezone.utc) < self.expires_at.replace(tzinfo=timezone.utc)
    
    def __repr__(self):
        return f'<ShareLink {self.token[:10]}...>'


class SiteStats(db.Model):
    """Track site-wide statistics"""
    __tablename__ = 'site_stats'
    
    id = db.Column(db.Integer, primary_key=True)
    total_visits = db.Column(db.Integer, default=0)
    total_users = db.Column(db.Integer, default=0)
    total_files_uploaded = db.Column(db.Integer, default=0)
    total_storage_used_mb = db.Column(db.Float, default=0.0)
    last_updated = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))
    
    @staticmethod
    def get_or_create():
        """Get or create stats record"""
        stats = SiteStats.query.first()
        if not stats:
            stats = SiteStats()
            db.session.add(stats)
            db.session.commit()
        return stats
    
    def increment_visits(self):
        """Increment visit counter"""
        self.total_visits += 1
        self.last_updated = datetime.now(timezone.utc)
        db.session.commit()
    
    def update_stats(self):
        """Update all statistics"""
        self.total_users = User.query.count()
        self.total_files_uploaded = File.query.count()
        
        # Calculate total storage
        total_bytes = 0
        for file in File.query.all():
            total_bytes += file.file_size
        self.total_storage_used_mb = round(total_bytes / (1024 * 1024), 2)
        
        self.last_updated = datetime.now(timezone.utc)
        db.session.commit()