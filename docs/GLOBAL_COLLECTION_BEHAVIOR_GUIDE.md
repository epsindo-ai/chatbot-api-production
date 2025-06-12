# Global Collection Behavior Guide

## Overview

This guide explains the new global collection behavior functionality that allows administrators to control how conversations handle changes to the global/predefined collection.

## Problem Statement

Previously, when an admin changed the global collection (the predefined collection used for RAG), existing conversations linked to the old collection would continue using the outdated collection, potentially causing confusion and inconsistent results.

## Solution

We've implemented two behavior modes that admins can choose from:

1. **Auto Update** (`auto_update`) - Default behavior
2. **Read-Only on Change** (`readonly_on_change`) - New behavior

## Behavior Modes

### 1. Auto Update (`auto_update`)

**Description**: Conversations automatically use the latest global collection without any user intervention.

**How it works**:
- When a user sends a message to a global collection conversation, the system checks if the global collection has changed
- If it has changed, the conversation is automatically updated to use the new collection
- The user experiences seamless continuation of their conversation with the latest knowledge base
- No user action required

**Best for**: 
- Organizations where the knowledge base is frequently updated
- When you want users to always have access to the latest information
- Environments where collection changes are improvements/additions rather than complete replacements

### 2. Read-Only on Change (`readonly_on_change`)

**Description**: Conversations become read-only when the global collection changes, requiring explicit user action.

**How it works**:
- When a user tries to send a message to a global collection conversation and the global collection has changed, the system returns an error
- The conversation becomes read-only until the user takes action
- Users can either:
  - Migrate the conversation to the current global collection
  - Start a new conversation with the current global collection

**Best for**:
- Organizations where collection changes represent significant shifts in knowledge
- When you want users to be explicitly aware of knowledge base changes
- Environments where mixing old and new knowledge could be problematic

## Database Schema Changes

### New Fields

#### `conversations` table:
- `original_global_collection_name` (String, nullable): Stores the name of the global collection when the conversation was initiated

#### `admin_config` table:
- New configuration key: `global_collection_behavior` with values `auto_update` or `readonly_on_change`

## API Endpoints

### Configuration Management

#### Get Global Collection Behavior
```http
GET /api/config/global-collection-behavior
```

**Response**:
```json
{
  "behavior": "auto_update",
  "description": "Conversations automatically use the latest global collection"
}
```

#### Set Global Collection Behavior (Admin Only)
```http
PUT /api/config/global-collection-behavior?behavior=readonly_on_change
```

**Response**:
```json
{
  "behavior": "readonly_on_change",
  "message": "Global collection behavior set to 'readonly_on_change'"
}
```

### Conversation Management

#### Get Global Collection Status
```http
GET /api/chat/conversations/{conversation_id}/global-collection-status
```

**Response**:
```json
{
  "conversation_type": "global_collection",
  "is_global_collection": true,
  "behavior": "readonly_on_change",
  "is_outdated": true,
  "original_collection_name": "old_knowledge_base",
  "current_global_collection_name": "new_knowledge_base",
  "linked_collection_id": 123,
  "can_migrate": true,
  "is_readonly": true,
  "auto_updates": false,
  "message": "This conversation is read-only because the global collection has changed. You can migrate to the current collection or start a new conversation."
}
```

#### Migrate Conversation to Current Global Collection
```http
POST /api/chat/conversations/{conversation_id}/migrate-to-current-global
```

**Response**: Updated conversation object

### Chat Behavior

#### Auto Update Mode
- Chat requests proceed normally
- System automatically updates conversation to use current global collection
- No user intervention required

#### Read-Only Mode
- Chat requests return HTTP 423 (Locked) with error message
- User must either migrate conversation or start new one

**Error Response**:
```json
{
  "status_code": 423,
  "error": "The knowledge base has been updated. This conversation is now read-only. Please start a new conversation or migrate to the current knowledge base.",
  "response": "",
  "conversation_id": "conv_123"
}
```

## Implementation Details

### Key Functions

#### `is_global_collection_outdated(db, conversation_id)`
- Checks if a conversation's global collection has changed
- Returns `False` for auto_update mode (never considered outdated)
- Returns `True` for readonly_on_change mode if collection names differ

#### `update_conversation_to_current_global_collection(db, conversation_id)`
- Updates conversation to use current global collection
- Updates both `linked_global_collection_id` and `original_global_collection_name`

### Chat Flow Changes

1. **Conversation Type Detection**: System identifies global collection conversations
2. **Outdated Check**: Checks if collection has changed based on behavior mode
3. **Action Based on Mode**:
   - **Auto Update**: Automatically update and proceed
   - **Read-Only**: Return error and block chat

## Frontend Integration

### Recommended UI Flow

#### For Auto Update Mode:
- No special UI needed
- Optionally show a brief notification when collection is auto-updated

#### For Read-Only Mode:
1. **Detection**: Check conversation status before allowing chat
2. **User Notification**: Show clear message about collection change
3. **Action Options**: Provide buttons for:
   - "Migrate to Current Knowledge Base"
   - "Start New Conversation"
4. **Status Indicator**: Show conversation status in conversation list

### Example Frontend Code

```javascript
// Check conversation status before sending message
async function checkConversationStatus(conversationId) {
  const response = await fetch(`/api/chat/conversations/${conversationId}/global-collection-status`);
  const status = await response.json();
  
  if (status.is_readonly) {
    // Show migration dialog
    showMigrationDialog(conversationId, status);
    return false; // Block message sending
  }
  
  return true; // Allow message sending
}

// Migrate conversation
async function migrateConversation(conversationId) {
  const response = await fetch(`/api/chat/conversations/${conversationId}/migrate-to-current-global`, {
    method: 'POST'
  });
  
  if (response.ok) {
    // Conversation migrated successfully
    // Refresh conversation or show success message
  }
}
```

## Configuration Examples

### Setting Up Auto Update (Default)
```bash
curl -X PUT "http://localhost:8000/api/config/global-collection-behavior?behavior=auto_update" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Setting Up Read-Only on Change
```bash
curl -X PUT "http://localhost:8000/api/config/global-collection-behavior?behavior=readonly_on_change" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Migration Guide

### From Previous Version

1. **Run Database Migration**: The migration adds the `original_global_collection_name` field
2. **Set Default Behavior**: The system defaults to `auto_update` mode
3. **Update Frontend**: Add UI for handling read-only conversations if using `readonly_on_change`

### Existing Conversations

- Existing global collection conversations will have `original_global_collection_name` set to `NULL`
- The system will handle this gracefully by using the current collection name as reference
- No data loss or corruption will occur

## Testing

Use the provided test script to verify functionality:

```bash
python test_global_collection_behavior.py
```

The test script verifies:
- Configuration endpoints
- Behavior switching
- Conversation creation
- Status checking
- Error handling

## Best Practices

### For Administrators

1. **Choose Appropriate Mode**: 
   - Use `auto_update` for frequently updated knowledge bases
   - Use `readonly_on_change` for major knowledge base overhauls

2. **Communicate Changes**: 
   - Notify users when switching to `readonly_on_change` mode
   - Provide guidance on migration process

3. **Monitor Conversations**: 
   - Check for orphaned conversations after collection changes
   - Provide support for users with migration questions

### For Frontend Developers

1. **Handle Both Modes**: Design UI that works with both behavior modes
2. **Clear Messaging**: Provide clear explanations when conversations become read-only
3. **Easy Migration**: Make the migration process as simple as possible
4. **Status Indicators**: Show conversation status clearly in the UI

## Troubleshooting

### Common Issues

#### Conversations Not Updating in Auto Mode
- Check that `global_collection_behavior` is set to `auto_update`
- Verify that the global collection is properly configured
- Check server logs for any errors during auto-update

#### Migration Fails
- Ensure the current global collection exists and is active
- Check user permissions
- Verify conversation belongs to the requesting user

#### Status Endpoint Returns Wrong Information
- Refresh the database connection
- Check that the conversation type is correctly set
- Verify the global collection configuration

### Debug Commands

```bash
# Check current behavior
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/config/global-collection-behavior

# Check conversation status
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/chat/conversations/CONV_ID/global-collection-status

# Check unified config
curl -H "Authorization: Bearer TOKEN" http://localhost:8000/api/config/
```

## Security Considerations

- Only admin users can change the global collection behavior
- Users can only access their own conversations
- Migration preserves user ownership and permissions
- No sensitive data is exposed in status endpoints

## Performance Impact

- Minimal performance impact for auto_update mode (single database query per chat)
- No performance impact for readonly_on_change mode when collections haven't changed
- Status checks are lightweight and cached where possible

## Future Enhancements

Potential future improvements:
- Batch migration tools for administrators
- Notification system for collection changes
- Conversation archiving for outdated collections
- Analytics on migration patterns
- Custom behavior rules per collection 