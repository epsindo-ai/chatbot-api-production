from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.auth.jwt import Token, create_access_token
from app.db import schemas, crud, models
from app.services.user_service import authenticate_user, create_initial_user, create_user
from app.config import settings
from app.db.database import get_db
from app.utils.auth import get_current_active_user

router = APIRouter()

@router.post("/token", response_model=schemas.UserLoginResponse)
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    # Create initial user if database is empty
    create_initial_user(db)
    
    user = authenticate_user(form_data.username, form_data.password, db)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    
    return {
        "access_token": access_token, 
        "token_type": "bearer",
        "user_id": user.id,
        "username": user.username,
        "email": user.email,
        "full_name": user.full_name,
        "role": user.role.value,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
        "is_active": user.is_active
    }

@router.post("/signup", response_model=schemas.UserLoginResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    user_data: schemas.UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register a new user
    """
    # Check if username already exists
    existing_user = crud.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Username already registered"
        )
    
    # Check if email already exists
    if user_data.email:
        existing_email = crud.get_user_by_email(db, user_data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Email already registered"
            )
    
    # Force user role to be regular user (prevent role spoofing)
    user_data_dict = user_data.dict()
    user_data_dict["role"] = schemas.UserRole.USER
    safe_user_data = schemas.UserCreate(**user_data_dict)
    
    # Create new user
    new_user = create_user(db, safe_user_data)
    
    # Generate access token
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.username}, expires_delta=access_token_expires
    )
    
    # Return token with user info
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": new_user.id,
        "username": new_user.username,
        "email": new_user.email,
        "full_name": new_user.full_name,
        "role": new_user.role.value,
        "expires_in": settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,  # in seconds
        "is_active": new_user.is_active
    }

@router.get("/me", response_model=schemas.UserInfo)
async def get_current_user_info(current_user: models.User = Depends(get_current_active_user)):
    """
    Get information about the currently authenticated user.
    This endpoint can be used to verify authentication and get user details.
    """
    return {
        "user_id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "full_name": current_user.full_name,
        "role": current_user.role.value,
        "is_active": current_user.is_active
    } 