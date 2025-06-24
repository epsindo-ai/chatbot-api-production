from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
import os
import uvicorn
from sqlalchemy.orm import Session
import logging

# Suppress passlib bcrypt warning
logging.getLogger("passlib.handlers.bcrypt").setLevel(logging.ERROR)

from app.config import settings
from app.api.routes import api_router
from app.db.database import engine, get_db, Base
from app.db import models
from app.db.models import UserRole
from app.services.admin_config_service import AdminConfigService
from app.services.super_admin_service import SuperAdminService

# Note: Database tables are created by Alembic migrations, not here
# This ensures proper version tracking and schema consistency

app = FastAPI(
    title=settings.APP_NAME,
    description="FastAPI server for an LLM chatbot with JWT authentication and RAG capabilities",
    version="0.2.0"
)

# Custom OpenAPI schema to use JWT auth only
def custom_openapi():
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )
    
    # Define JWT security scheme
    openapi_schema["components"]["securitySchemes"] = {
        "JWT": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT",
        }
    }
    
    # Apply JWT security globally
    openapi_schema["security"] = [{"JWT": []}]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema

# Replace the default OpenAPI schema with our custom one
app.openapi = custom_openapi

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include routers
# Note: The API now uses a unified approach with all functionality in /api/chat
# This includes: 
# - Regular chat endpoint (/chat/conversation)
# - RAG chat endpoint (same as above but with collection_name parameter)
# - File upload endpoint (/chat/upload-file)
# - System health endpoint (/chat/system/health)
# - Embeddings endpoint (/chat/embeddings)
app.include_router(api_router)

# Define function for setting default user roles
def ensure_user_roles(db: Session):
    """Ensure all users have a role assigned"""
    users_without_role = db.query(models.User).filter(
        models.User.role.is_(None)
    ).all()
    
    if users_without_role:
        for user in users_without_role:
            user.role = UserRole.USER
        db.commit()
        print(f"Startup: Set default roles for {len(users_without_role)} users")

@app.on_event("startup")
async def startup_db_client():
    """
    Startup event to run maintenance tasks:
    1. Ensure all users have roles assigned
    2. Initialize the single super admin user
    3. Ensure default admin configurations are in the database
    """
    # Create a database session
    # Correct way to get a session for startup tasks if using SessionLocal pattern
    from app.db.database import SessionLocal 
    db = SessionLocal()
    
    try:
        # Run maintenance tasks
        ensure_user_roles(db)
        
        # Initialize the single super admin user
        SuperAdminService.initialize_super_admin(db)
        
        # Initialize default admin configurations
        AdminConfigService.initialize_default_configs(db)
        
        db.commit() # Commit any changes made by initialization tasks
    except Exception as e:
        print(f"Startup error: {e}")
        db.rollback() # Rollback in case of error during startup tasks
    finally:
        db.close()

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """Return a simple message for the root endpoint."""
    return HTMLResponse(content="<html><body><h1>API Server Running</h1><p>Use /docs for API documentation</p></body></html>")

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app", 
        host="0.0.0.0", 
        port=35430, 
        reload=False,
        workers=10,  # Use 1 worker to avoid multiprocessing import issues
        loop="asyncio",  # Use asyncio event loop
        access_log=True,
        log_level="info"
    ) 