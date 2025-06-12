# PUT /api/admin/collections/{collection_id} - Example Queries

This document provides example HTTP requests for the PUT endpoint that demonstrate how it properly handles global default collection management.

## Prerequisites

1. You need an admin authentication token
2. You need existing admin collections to update
3. Replace `{BASE_URL}` with your actual API base URL (e.g., `http://localhost:8000`)

## Example 1: Setting a Collection as Global Default

### Scenario
You have collection ID `123` named "hr_policies_2024" and want to set it as the global default collection.

### Request
```bash
curl -X PUT "{BASE_URL}/api/admin/collections/123" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hr_policies_2024",
    "description": "HR policies and procedures for 2024 - Global Default",
    "is_global_default": true
  }'
```

### Expected Response
```json
{
  "id": 123,
  "name": "hr_policies_2024",
  "description": "HR policies and procedures for 2024 - Global Default",
  "is_admin_only": true,
  "is_global_default": true,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T11:45:00Z"
}
```

### What Happens Behind the Scenes
1. **Database Level**: Any existing global default collection is automatically set to `is_global_default = false`
2. **Database Level**: Collection 123 is set to `is_global_default = true`
3. **Config Level**: Admin configuration is updated to use "hr_policies_2024" for RAG
4. **Global Behavior**: Existing conversations may become read-only or auto-update (depending on global collection behavior setting)

---

## Example 2: Switching Global Default to Another Collection

### Scenario
Collection 123 is currently the global default. You want to switch to collection ID `456` named "tech_documentation".

### Request
```bash
curl -X PUT "{BASE_URL}/api/admin/collections/456" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "tech_documentation",
    "description": "Technical documentation - New Global Default",
    "is_global_default": true
  }'
```

### Expected Response
```json
{
  "id": 456,
  "name": "tech_documentation",
  "description": "Technical documentation - New Global Default",
  "is_admin_only": true,
  "is_global_default": true,
  "is_active": true,
  "created_at": "2024-01-10T09:15:00Z",
  "updated_at": "2024-01-15T11:50:00Z"
}
```

### What Happens Behind the Scenes
1. Collection 123 automatically becomes `is_global_default = false`
2. Collection 456 becomes `is_global_default = true`
3. RAG config updates to use "tech_documentation"

---

## Example 3: Updating Metadata Without Changing Global Default

### Scenario
You want to update the description of collection 123 without affecting its global default status.

### Request
```bash
curl -X PUT "{BASE_URL}/api/admin/collections/123" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hr_policies_2024",
    "description": "Updated HR policies and procedures for 2024 with new compliance requirements"
  }'
```

### Expected Response
```json
{
  "id": 123,
  "name": "hr_policies_2024",
  "description": "Updated HR policies and procedures for 2024 with new compliance requirements",
  "is_admin_only": true,
  "is_global_default": true,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:00:00Z"
}
```

### Note
Since `is_global_default` was not included in the request, the existing value is preserved.

---

## Example 4: Removing Global Default Status

### Scenario
You want to remove the global default status from the currently active global default collection.

### Request
```bash
curl -X PUT "{BASE_URL}/api/admin/collections/123" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hr_policies_2024",
    "description": "HR policies and procedures for 2024",
    "is_global_default": false
  }'
```

### Expected Response
```json
{
  "id": 123,
  "name": "hr_policies_2024",
  "description": "HR policies and procedures for 2024",
  "is_admin_only": true,
  "is_global_default": false,
  "is_active": true,
  "created_at": "2024-01-15T10:30:00Z",
  "updated_at": "2024-01-15T12:05:00Z"
}
```

### Result
After this request, no collection will be the global default.

---

## Example 5: Deactivating a Collection

### Scenario
You want to temporarily disable a collection without deleting it.

### Request
```bash
curl -X PUT "{BASE_URL}/api/admin/collections/789" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "old_policies",
    "description": "Outdated policies - temporarily disabled",
    "is_active": false
  }'
```

### Expected Response
```json
{
  "id": 789,
  "name": "old_policies",
  "description": "Outdated policies - temporarily disabled",
  "is_admin_only": true,
  "is_global_default": false,
  "is_active": false,
  "created_at": "2024-01-01T08:00:00Z",
  "updated_at": "2024-01-15T12:10:00Z"
}
```

---

## Error Examples

### Error 1: Collection Not Found
```bash
curl -X PUT "{BASE_URL}/api/admin/collections/99999" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "nonexistent",
    "is_global_default": true
  }'
```

**Response (404)**:
```json
{
  "detail": "Collection with ID 99999 not found"
}
```

### Error 2: Duplicate Name
```bash
curl -X PUT "{BASE_URL}/api/admin/collections/456" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "hr_policies_2024"
  }'
```

**Response (400)**:
```json
{
  "detail": "Collection with name 'hr_policies_2024' already exists"
}
```

### Error 3: Not an Admin Collection
```bash
curl -X PUT "{BASE_URL}/api/admin/collections/999" \
  -H "Authorization: Bearer YOUR_ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "user_collection",
    "is_global_default": true
  }'
```

**Response (400)**:
```json
{
  "detail": "This is not an admin collection"
}
```

---

## Python Example

```python
import requests

def update_collection_as_global_default(collection_id: int, token: str):
    """Set a collection as the global default."""
    url = f"http://localhost:8000/api/admin/collections/{collection_id}"
    
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    data = {
        "name": "my_knowledge_base",
        "description": "Company knowledge base - Global Default",
        "is_global_default": True
    }
    
    response = requests.put(url, json=data, headers=headers)
    
    if response.status_code == 200:
        result = response.json()
        print(f"✅ Collection {result['name']} is now the global default")
        return result
    else:
        print(f"❌ Error: {response.status_code} - {response.json()}")
        return None

# Usage
admin_token = "your_admin_token_here"
collection_id = 123
result = update_collection_as_global_default(collection_id, admin_token)
```

---

## Key Points

1. **Automatic Deactivation**: When setting `is_global_default: true`, the current global default is automatically deactivated
2. **Single Global Default**: Only one collection can be global default at any time
3. **Two-Level Update**: Database state AND admin configuration are both updated
4. **Atomic Operation**: The entire operation succeeds or fails together
5. **Metadata Only**: This endpoint only updates metadata - use unified creation endpoints for file management
6. **Admin Only**: Only admin collections can be updated through this endpoint
7. **Validation**: Name uniqueness and collection existence are validated

This design ensures data consistency and prevents the issues you were concerned about with typical PUT operations!
