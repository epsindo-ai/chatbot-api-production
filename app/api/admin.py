from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.db import crud, models
from app.db.database import get_db
from app.utils.auth import get_admin_access, get_super_admin_access
from app.db.models import UserRole
from app.config import settings

router = APIRouter(
    prefix="/admin/users",
    tags=["admin-users"],
)

class UserRoleChangeRequest(BaseModel):
    username: str

class UserRoleUpdateRequest(BaseModel):
    username: str
    role: UserRole

class UserResponse(BaseModel):
    id: int
    username: str
    email: Optional[str] = None
    role: str
    is_active: bool

@router.post("/update-role", response_model=UserResponse)
async def update_user_role(
    request: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_super_admin_access)
):
    """
    Update a user's role directly - Super Admin only
    """
    # Find the user
    user = crud.get_user_by_username(db, request.username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{request.username}' not found"
        )
    
    # Prevent promotion to super admin via API
    if request.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot promote users to super admin via API. Only one super admin is allowed and is created during deployment."
        )
    
    # Check if trying to change to the same role
    if user.role == request.role:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User '{request.username}' already has the role '{request.role.value}'"
        )
    
    # Prevent self-role changes
    if user.username == current_user.username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot change your own role"
        )
    
    # Prevent demotion of the super admin user
    if user.role == UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot demote the super admin user. Super admin role is permanent."
        )
    
    # Update the user role
    user.role = request.role
    db.commit()
    db.refresh(user)
    
    return {
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role.value,
        "is_active": user.is_active
    }

@router.get("/", response_model=List[UserResponse])
async def get_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_access)
):
    """
    Get list of all users
    """
    users = db.query(models.User).offset(skip).limit(limit).all()
    return [
        {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role.value,
            "is_active": user.is_active
        }
        for user in users
    ]

@router.get("/stats", response_model=Dict[str, int])
async def get_user_stats(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_admin_access)
):
    """
    Get basic user statistics.
    """
    total_users = db.query(models.User).count()
    active_users = db.query(models.User).filter(models.User.is_active == True).count()
    admin_users = db.query(models.User).filter(models.User.role == UserRole.ADMIN).count()
    
    return {
        "total_users": total_users,
        "active_users": active_users,
        "admin_users": admin_users
    }

# Alternative routes for OAuth token authentication (without request parameter dependency)
# These are now redundant and have been removed. 