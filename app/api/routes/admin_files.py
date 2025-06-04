from fastapi import APIRouter, Depends, HTTPException, status, File, UploadFile, Form, Query
from fastapi.responses import JSONResponse, StreamingResponse
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
import os

from app.db import crud, models, schemas
from app.db.database import get_db
from app.utils.auth import get_admin_access
from app.services.minio_service import MinioService
from app.config import settings

router = APIRouter(
    prefix="/files",
    tags=["admin-files"],
)

# Initialize services
minio_service = MinioService()

@router.get("/", response_model=List[schemas.FileStorageResponse])
async def list_all_files(
    skip: int = 0,
    limit: int = 100,
    search: Optional[str] = None,
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    List all files in the system (admin only).
    Optionally filter by filename with search parameter.
    """
    files = crud.get_all_files(db, skip=skip, limit=limit, search=search)
    
    # Add download URLs to each file
    result = []
    for file in files:
        file_dict = schemas.FileStorage.model_validate(file).model_dump()
        file_dict["download_url"] = f"/api/admin/files/{file.id}/download"
        result.append(schemas.FileStorageResponse(**file_dict))
    
    return result

@router.get("/minio", response_model=List[Dict[str, Any]])
async def list_minio_files(
    prefix: str = "",
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    List all files in MinIO storage with rich information from database (admin only).
    Optionally filter by prefix.
    Returns rich file information when database record exists, basic MinIO info otherwise.
    """
    objects = minio_service.list_files(prefix=prefix)
    
    if not objects:
        return []
    
    # Get all file paths for batch database query
    file_paths = [obj.object_name for obj in objects]
    
    # Batch query to get all database records
    db_files = crud.get_files_by_paths(db, file_paths)
    
    # Create a mapping for quick lookup
    db_files_map = {file.file_path: file for file in db_files}
    
    # Convert objects to a more readable format with database enrichment
    result = []
    for obj in objects:
        db_file = db_files_map.get(obj.object_name)
        
        if db_file:
            # File exists in database - return rich information like /api/admin/files/
            file_dict = schemas.FileStorage.model_validate(db_file).model_dump()
            file_dict["download_url"] = f"/api/admin/files/{db_file.id}/download"
            
            # Add MinIO-specific metadata
            file_dict["minio_metadata"] = {
                "etag": obj.etag if hasattr(obj, "etag") else None,
                "last_modified_minio": obj.last_modified.isoformat() if hasattr(obj, "last_modified") else None,
                "size_minio": obj.size
            }
            
            result.append(file_dict)
        else:
            # File exists only in MinIO - return basic MinIO information
            result.append({
                "name": obj.object_name,
                "size": obj.size,
                "last_modified": obj.last_modified.isoformat() if hasattr(obj, "last_modified") else None,
                "etag": obj.etag if hasattr(obj, "etag") else None,
                "download_url": f"/api/admin/files/minio/{obj.object_name}",
                "is_orphaned": True,  # Flag to indicate file exists only in MinIO
                "filename": None,
                "original_filename": None,
                "file_path": obj.object_name,
                "file_size": obj.size,
                "mime_type": None,
                "file_metadata": None,
                "conversation_id": None,
                "id": None,
                "user_id": None,
                "created_at": None
            })
    
    return result

@router.post("/upload", response_model=schemas.FileStorageResponse)
async def admin_upload_file(
    file: UploadFile = File(...),
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Upload a file as an admin to MinIO storage.
    
    This endpoint only handles file upload and storage - no RAG processing.
    For creating collections with files and processing them for RAG, use:
    - POST /api/admin/collections/with-files (for existing files)
    - POST /api/admin/collections/upload-and-create (for new uploads)
    """
    # Upload file to MinIO
    success, object_name, metadata = await minio_service.upload_file_async(file, folder="admin")
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to upload file to storage"
        )
    
    # Create file record in database
    file_create = schemas.FileStorageCreate(
        user_id=current_user.id,
        filename=metadata["filename"],
        original_filename=metadata["filename"],
        file_path=metadata["path"],
        file_size=metadata["size"],
        mime_type=metadata["content_type"],
        file_metadata={"is_admin_upload": True}
    )
    
    db_file = crud.create_file_storage(db, file_create)
    
    # Generate download URL for the response
    download_url = f"/api/admin/files/{db_file.id}/download"
    
    # Create response
    file_response = schemas.FileStorage.model_validate(db_file).model_dump()
    file_response["download_url"] = download_url
    
    return schemas.FileStorageResponse(**file_response)

@router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    delete_from_minio: bool = Query(True, description="Whether to also delete the file from MinIO storage"),
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Delete a file (admin only).
    Optionally also delete it from MinIO storage.
    """
    # Get file info
    file = crud.get_file_storage(db, file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found"
        )
    
    # Delete from MinIO if requested
    if delete_from_minio:
        minio_service.delete_file(file.file_path)
    
    # Delete from database
    success = crud.delete_file_storage(db, file_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete file from database"
        )
    
    return {"detail": "File deleted successfully"}

# MOVED: list_milvus_collections endpoint moved to /api/admin/collections/milvus/collections
# This provides better organization - database collections vs Milvus collections

@router.get("/{file_id}/download", operation_id="admin_files_download_file")
def download_admin_file(
    file_id: int,
    current_user: models.User = Depends(get_admin_access),
    db: Session = Depends(get_db)
):
    """
    Securely download a file (Admin only).
    
    This endpoint:
    1. Validates admin access
    2. Validates that the file exists
    3. Streams the file content directly from MinIO
    4. Requires authentication for every download
    """
    # Get file info
    file = crud.get_file_storage(db, file_id)
    if not file:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File with ID {file_id} not found"
        )
    
    # Download file from MinIO
    success, file_data = minio_service.download_file(file.file_path)
    
    if not success or not file_data:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to download file from storage"
        )
    
    # Create streaming response
    def generate():
        try:
            file_data.seek(0)  # Ensure we're at the beginning
            while True:
                chunk = file_data.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                yield chunk
        finally:
            file_data.close()
    
    # Return streaming response with appropriate headers
    return StreamingResponse(
        generate(),
        media_type=file.mime_type or "application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{file.original_filename}"',
            "Content-Length": str(file.file_size) if file.file_size else None
        }
    )

@router.get("/minio/{file_path:path}", operation_id="admin_files_download_minio_file")
def download_minio_file(
    file_path: str,
    current_user: models.User = Depends(get_admin_access)
):
    """
    Download an orphaned file directly from MinIO (Admin only).
    
    This is for files that exist in MinIO but not in the database.
    These are typically files that were uploaded but never properly recorded,
    or files left behind after database cleanup.
    
    Security features:
    - Requires admin authentication
    - Streams file directly without exposing MinIO credentials
    - Provides audit trail through API logs
    """
    # Download file from MinIO
    success, file_data = minio_service.download_file(file_path)
    
    if not success or not file_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="File not found in storage"
        )
    
    # Create streaming response
    def generate():
        try:
            file_data.seek(0)  # Ensure we're at the beginning
            while True:
                chunk = file_data.read(8192)  # Read in 8KB chunks
                if not chunk:
                    break
                yield chunk
        finally:
            file_data.close()
    
    # Extract filename from path
    filename = file_path.split('/')[-1] if '/' in file_path else file_path
    
    # Return streaming response with appropriate headers
    return StreamingResponse(
        generate(),
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        }
    ) 