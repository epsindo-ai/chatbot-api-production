from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.config import settings
from app.db import schemas
from app.db.database import get_db

# Import authentication functions from utils.auth for consistency
from app.utils.auth import (
    oauth2_scheme,
    get_current_user,
    get_current_active_user,
    create_access_token,
)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    username: Optional[str] = None

# Re-export these functions for backwards compatibility
__all__ = [
    "Token", 
    "TokenData", 
    "oauth2_scheme", 
    "get_current_user", 
    "get_current_active_user", 
    "create_access_token"
] 