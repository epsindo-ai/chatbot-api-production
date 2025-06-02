from fastapi import APIRouter
from app.api.routes import auth, config, collections, unified_chat, admin_files, admin_collections, llm_config
from app.api import admin

api_router = APIRouter(prefix="/api")

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(config.router, prefix="/config", tags=["config"])
api_router.include_router(collections.router, prefix="/collections", tags=["collections"])
api_router.include_router(llm_config.router, prefix="/llm-config", tags=["llm-config"])

# Admin routes
api_router.include_router(admin_files.router, prefix="/admin", tags=["admin-files"])
api_router.include_router(admin_collections.router, prefix="/admin", tags=["admin-collections"])
api_router.include_router(admin.router)

# Unified chat endpoint that combines regular chat and RAG
api_router.include_router(unified_chat.router, prefix="/chat", tags=["chat"]) 