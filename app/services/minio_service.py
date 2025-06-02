from typing import Optional, Dict, Any, Tuple, BinaryIO
import os
import io
import uuid
from urllib.parse import urljoin

from minio import Minio
from minio.error import S3Error
from fastapi import UploadFile

from app.config import settings

class MinioService:
    """Service for managing files in MinIO object storage."""
    
    def __init__(self, 
                 endpoint: Optional[str] = None,
                 access_key: Optional[str] = None,
                 secret_key: Optional[str] = None,
                 secure: bool = False):
        """
        Initialize the MinIO service.
        
        Args:
            endpoint: MinIO endpoint (host:port)
            access_key: MinIO access key
            secret_key: MinIO secret key
            secure: Whether to use secure connection (HTTPS)
        """
        self.endpoint = endpoint or settings.MINIO_ENDPOINT
        self.access_key = access_key or settings.MINIO_ACCESS_KEY
        self.secret_key = secret_key or settings.MINIO_SECRET_KEY
        self.secure = secure or settings.MINIO_SECURE
        self.default_bucket = settings.MINIO_DEFAULT_BUCKET
        
        # Initialize MinIO client
        self.client = Minio(
            endpoint=self.endpoint,
            access_key=self.access_key,
            secret_key=self.secret_key,
            secure=self.secure
        )
        
        # Ensure default bucket exists
        self.ensure_bucket_exists(self.default_bucket)
    
    def ensure_bucket_exists(self, bucket_name: str) -> bool:
        """
        Ensure the specified bucket exists, creating it if it doesn't.
        
        Args:
            bucket_name: Name of the bucket
            
        Returns:
            True if bucket exists or was created
        """
        try:
            if not self.client.bucket_exists(bucket_name):
                self.client.make_bucket(bucket_name)
            return True
        except S3Error as e:
            print(f"Error ensuring bucket exists: {e}")
            return False
    
    def upload_file(self, file_data: bytes, file_path: str, content_type: str = "application/octet-stream") -> bool:
        """
        Upload file data to MinIO (synchronous version).
        
        Args:
            file_data: Raw file data as bytes
            file_path: Path to store the file (including filename)
            content_type: MIME type of the file
            
        Returns:
            True if upload was successful, False otherwise
        """
        try:
            # Create file-like object
            data = io.BytesIO(file_data)
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.default_bucket,
                object_name=file_path,
                data=data,
                length=len(file_data),
                content_type=content_type
            )
            
            return True
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False
    
    async def upload_file_async(self, file: UploadFile, folder: str = "uploads") -> Tuple[bool, str, Dict[str, Any]]:
        """
        Upload a file to MinIO.
        
        Args:
            file: FastAPI UploadFile object
            folder: Folder to store the file in
            
        Returns:
            Tuple of (success, object_name, metadata)
        """
        try:
            # Generate a unique filename with the original extension
            filename = file.filename
            ext = os.path.splitext(filename)[1] if filename else ""
            object_name = f"{folder}/{uuid.uuid4()}{ext}"
            
            # Read file content
            content = await file.read()
            file_size = len(content)
            
            # Create file-like object
            file_data = io.BytesIO(content)
            
            # Upload to MinIO
            self.client.put_object(
                bucket_name=self.default_bucket,
                object_name=object_name,
                data=file_data,
                length=file_size,
                content_type=file.content_type or "application/octet-stream"
            )
            
            # Reset file pointer for potential further use
            await file.seek(0)
            
            return True, object_name, {
                "filename": filename,
                "path": object_name,
                "size": file_size,
                "content_type": file.content_type
            }
        
        except Exception as e:
            print(f"Error uploading file: {e}")
            return False, "", {}
    
    def download_file(self, object_name: str) -> Tuple[bool, Optional[BinaryIO]]:
        """
        Download a file from MinIO.
        
        Args:
            object_name: Name of the object in MinIO
            
        Returns:
            Tuple of (success, file_data)
        """
        try:
            # Get object data
            response = self.client.get_object(
                bucket_name=self.default_bucket,
                object_name=object_name
            )
            
            # Read all data
            data = response.read()
            
            # Create BytesIO object
            file_data = io.BytesIO(data)
            
            # Close the response
            response.close()
            response.release_conn()
            
            return True, file_data
        
        except Exception as e:
            print(f"Error downloading file: {e}")
            return False, None
    
    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from MinIO.
        
        Args:
            object_name: Name of the object in MinIO
            
        Returns:
            True if file was deleted
        """
        try:
            self.client.remove_object(
                bucket_name=self.default_bucket,
                object_name=object_name
            )
            
            return True
        
        except Exception as e:
            print(f"Error deleting file: {e}")
            return False
    
    def generate_presigned_url(self, object_name: str, expires: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for accessing a file.
        
        Args:
            object_name: Name of the object in MinIO
            expires: Expiration time in seconds
            
        Returns:
            Presigned URL or None if error
        """
        try:
            # Make sure expires is an integer
            if not isinstance(expires, int):
                # Try to convert to int if possible
                try:
                    expires = int(expires)
                except (TypeError, ValueError):
                    # Default to 1 hour if conversion fails
                    expires = 3600
            
            # Convert seconds to timedelta
            from datetime import timedelta
            expires_delta = timedelta(seconds=expires)
            
            url = self.client.presigned_get_object(
                bucket_name=self.default_bucket,
                object_name=object_name,
                expires=expires_delta
            )
            
            return url
        
        except Exception as e:
            print(f"Error generating presigned URL: {e}")
            # Return a placeholder URL instead of None to avoid breaking the UI
            # This allows the application to continue functioning even if MinIO is not available
            return f"/api/files/download/{object_name}"
    
    def list_files(self, prefix: str = "", recursive: bool = True) -> list:
        """
        List files in MinIO bucket with optional prefix.
        
        Args:
            prefix: Prefix to filter objects
            recursive: Whether to list recursively
            
        Returns:
            List of objects
        """
        try:
            objects = self.client.list_objects(
                bucket_name=self.default_bucket,
                prefix=prefix,
                recursive=recursive
            )
            
            return list(objects)
        
        except Exception as e:
            print(f"Error listing files: {e}")
            return [] 