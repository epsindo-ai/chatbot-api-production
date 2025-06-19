import secrets
import string
from datetime import datetime, timedelta, timezone
from typing import Optional

def generate_temporary_password(length: int = 12) -> str:
    """Generate a secure temporary password"""
    # Use a mix of letters, digits, and some safe special characters
    alphabet = string.ascii_letters + string.digits + "!@#$%^&*"
    password = ''.join(secrets.choice(alphabet) for _ in range(length))
    return password

def calculate_expiry(hours: int = 24) -> datetime:
    """Calculate expiry datetime for temporary password"""
    return datetime.now(timezone.utc) + timedelta(hours=hours)

def is_password_expired(expires_at: Optional[datetime]) -> bool:
    """Check if a temporary password has expired"""
    if not expires_at:
        return False
    return datetime.now(timezone.utc) > expires_at

def format_password_for_display(password: str) -> str:
    """Format password for secure display (could be enhanced with better formatting)"""
    return password
