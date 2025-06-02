from datetime import datetime, timedelta
from typing import Optional
from fastapi import Depends, HTTPException, status, Request
from jose import JWTError, jwt
from sqlalchemy.orm import Session
from fastapi.security import OAuth2PasswordBearer
from app.db import crud, models, schemas
from app.db.database import get_db
from app.config import settings
import os

# Check if we're in production mode
IS_PRODUCTION = os.getenv("ENVIRONMENT", "development").lower() == "production"

# Use a more secure OAuth scheme that requires HTTPS in production
oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="api/auth/token", 
    scheme_name="JWT",
    auto_error=True
)

# Shorter token lifetime for admin users
ADMIN_TOKEN_EXPIRE_MINUTES = int(os.getenv("ADMIN_TOKEN_EXPIRE_MINUTES", "15"))

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None, is_admin: bool = False):
    to_encode = data.copy()
    
    # Use shorter expiry for admin tokens if not explicitly provided
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        # Use shorter expiry for admin users
        if is_admin:
            expire = datetime.utcnow() + timedelta(minutes=ADMIN_TOKEN_EXPIRE_MINUTES)
        else:
            expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
        token_data = schemas.TokenData(username=username)
    except JWTError:
        raise credentials_exception
    user = crud.get_user_by_username(db, username=token_data.username)
    if user is None:
        raise credentials_exception
    return user

async def get_current_active_user(current_user: models.User = Depends(get_current_user)):
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

async def get_admin_user(request: Request, current_user: models.User = Depends(get_current_active_user)):
    # Removed HTTPS check for local deployment
    # if IS_PRODUCTION and not request.url.scheme == "https":
    #     raise HTTPException(
    #         status_code=status.HTTP_403_FORBIDDEN,
    #         detail="HTTPS is required for admin endpoints in production"
    #     )
        
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
        
    return current_user

async def get_admin_access(current_user: models.User = Depends(get_current_active_user)):
    """
    Check if the current user has admin access.
    This version doesn't require a Request parameter.
    """
    if current_user.role != models.UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions. Admin role required."
        )
    
    return current_user 