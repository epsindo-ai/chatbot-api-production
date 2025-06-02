# MinIO Endpoint Enhancement

## Overview

The `/api/admin/files/minio` endpoint has been enhanced to return rich file information similar to the `/api/admin/files/` endpoint, instead of just basic MinIO object metadata.

## Changes Made

### 1. Enhanced Response Structure

The endpoint now returns rich database information when available, including:

- `filename` - The stored filename
- `original_filename` - The original filename when uploaded
- `file_path` - Path in MinIO storage
- `file_size` - File size in bytes
- `mime_type` - MIME type of the file
- `file_metadata` - Additional metadata (e.g., `is_admin_upload: true`)
- `conversation_id` - Associated conversation ID (if any)
- `id` - Database record ID
- `user_id` - ID of the user who uploaded the file
- `created_at` - Timestamp when the file was uploaded
- `download_url` - Presigned URL for downloading the file

### 2. MinIO Metadata Addition

For files that exist in both MinIO and the database, additional MinIO-specific metadata is included:

```json
{
  "minio_metadata": {
    "etag": "cbb6b2668d79e1d5a869be643ec46b5e",
    "last_modified_minio": "2025-05-09T08:24:02.745000+00:00",
    "size_minio": 115720
  }
}
```

### 3. Orphaned File Detection

Files that exist in MinIO but not in the database are marked as orphaned:

```json
{
  "name": "admin/orphaned-file.pdf",
  "size": 12345,
  "last_modified": "2025-05-27T03:41:10.792000+00:00",
  "etag": "abc123...",
  "download_url": "http://...",
  "is_orphaned": true,
  "filename": null,
  "original_filename": null,
  "file_path": "admin/orphaned-file.pdf",
  "file_size": 12345,
  "mime_type": null,
  "file_metadata": null,
  "conversation_id": null,
  "id": null,
  "user_id": null,
  "created_at": null
}
```

### 4. Performance Optimization

The implementation uses batch database queries to efficiently retrieve file information for all MinIO objects in a single query, rather than making individual database calls for each file.

## API Usage

### Request
```
GET /api/admin/files/minio?prefix=admin
Authorization: Bearer <admin_token>
```

### Response
```json
[
  {
    "filename": "Form Permohonan EFIN (PDF isian).pdf",
    "original_filename": "Form Permohonan EFIN (PDF isian).pdf",
    "file_path": "admin/9ddc2e22-8b77-4eaa-9f92-c62f3e2f261b.pdf",
    "file_size": 98951,
    "mime_type": "application/pdf",
    "file_metadata": {
      "is_admin_upload": true
    },
    "conversation_id": null,
    "id": 81,
    "user_id": 2,
    "created_at": "2025-05-27T03:41:10.788651Z",
    "download_url": "http://192.168.1.10:9000/documents/admin/9ddc2e22-8b77-4eaa-9f92-c62f3e2f261b.pdf?...",
    "minio_metadata": {
      "etag": "47859a215e55808e48a7ba01cdc896ff",
      "last_modified_minio": "2025-05-27T03:41:10.792000+00:00",
      "size_minio": 98951
    }
  }
]
```

## Benefits

1. **Consistent API Response**: The minio endpoint now returns the same rich information as the regular files endpoint
2. **Orphaned File Detection**: Easily identify files that exist in storage but not in the database
3. **Complete File Information**: Access to both storage metadata and database information in a single call
4. **Performance Optimized**: Efficient batch queries for better performance with large file lists
5. **Backward Compatible**: Existing functionality is preserved while adding new features

## Files Modified

- `app/api/routes/admin_files.py` - Enhanced the `list_minio_files` endpoint
- `app/db/crud.py` - Added helper functions `get_file_by_path` and `get_files_by_paths`

## Testing

Use the provided `test_minio_endpoint.py` script to test the enhanced functionality:

```bash
python test_minio_endpoint.py
```

Make sure to adjust the configuration variables in the script to match your environment. 