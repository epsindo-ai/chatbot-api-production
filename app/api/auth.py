from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from sqlalchemy.orm import Session
from typing import Any, Optional
from pydantic import BaseModel, EmailStr

from app.db import crud, models, schemas
from app.db.database import get_db
from app.utils.password import verify_password
from app.utils.auth import create_access_token, get_current_active_user
from app.config import settings

router = APIRouter(
    prefix="/api/auth",
    tags=["auth"],
)

@router.post("/token", response_model=schemas.UserLoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = crud.get_user_by_username(db, form_data.username)
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Create access token with shorter expiry if user is admin
    access_token = create_access_token(
        data={"sub": user.username},
        is_admin=(user.role == models.UserRole.ADMIN)
    )
    
    # Calculate token expiry in seconds
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    if user.role == models.UserRole.ADMIN:
        from app.utils.auth import ADMIN_TOKEN_EXPIRE_MINUTES
        expires_in = ADMIN_TOKEN_EXPIRE_MINUTES * 60
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,  # Convert Enum to string
        "expires_in": expires_in
    }

@router.post("/login", response_model=schemas.UserLoginResponse)
async def login(user_data: schemas.UserLogin, db: Session = Depends(get_db)):
    # Reuse the token endpoint logic but with JSON body instead of form
    user = crud.get_user_by_username(db, user_data.username)
    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    # Create access token with shorter expiry if user is admin
    access_token = create_access_token(
        data={"sub": user.username},
        is_admin=(user.role == models.UserRole.ADMIN)
    )
    
    # Calculate token expiry in seconds
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    if user.role == models.UserRole.ADMIN:
        from app.utils.auth import ADMIN_TOKEN_EXPIRE_MINUTES
        expires_in = ADMIN_TOKEN_EXPIRE_MINUTES * 60
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,  # Convert Enum to string
        "expires_in": expires_in
    }

# Simplified user creation model to prevent role spoofing
class UserSignUp(BaseModel):
    username: str
    email: EmailStr
    full_name: Optional[str] = None
    password: str

@router.post("/signup", response_model=schemas.UserLoginResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserSignUp, db: Session = Depends(get_db)):
    # Check if username already exists
    db_user = crud.get_user_by_username(db, username=user_data.username)
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if user_data.email:
        db_user = crud.get_user_by_email(db, email=user_data.email)
        if db_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered"
            )
    
    # Create a safe UserCreate object with forced USER role
    user_create = schemas.UserCreate(
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        password=user_data.password,
        is_active=True,
        role=schemas.UserRole.USER  # Force regular user role
    )
    
    # Create the user in the database
    new_user = crud.create_user(db=db, user=user_create)
    
    # Create token for the new user
    access_token = create_access_token(
        data={"sub": new_user.username},
        is_admin=False  # New users are never admins
    )
    
    # Return login response with token
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role.value,  # Include role in the response
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }

@router.get("/me", response_model=schemas.User)
async def read_users_me(current_user: models.User = Depends(get_current_active_user)):
    """Get current authenticated user information"""
    return current_user 