# File Upload Blocking Implementation Guide

## Overview

This implementation provides file upload functionality that can block conversation until processing is complete, ensuring users can't send messages until files are ready for RAG.

## API Changes

### 1. Enhanced Upload Endpoint

**Endpoint**: `POST /api/chat/upload-file`

**New Parameter**:
- `sync_processing` (boolean, default: `true`) - Controls processing behavior

**Behavior**:
- `sync_processing=true`: Waits for file processing to complete before returning
- `sync_processing=false`: Returns immediately, processes files in background

### 2. New Conversation Ready Endpoint

**Endpoint**: `GET /api/chat/conversation-ready/{conversation_id}`

**Response**:
```json
{
  "ready": true,
  "message": "All files processed",
  "files_count": 2,
  "processed_count": 2,
  "files": [
    {
      "id": 123,
      "filename": "document.pdf",
      "processed": true
    }
  ]
}
```

## Frontend Implementation Options

### Option 1: Synchronous Upload (Recommended for Blocking)

```javascript
// Upload files and wait for completion
const formData = new FormData();
files.forEach(file => formData.append('files', file));
formData.append('conversation_id', conversationId);
formData.append('sync_processing', 'true'); // Block until complete

const response = await fetch('/api/chat/upload-file', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
});

const result = await response.json();

// Check if all files processed successfully
const allProcessed = result.every(file => 
    file.processing_status === 'completed' && !file.error
);

if (allProcessed) {
    console.log('✅ Files ready! Conversation can start.');
    enableChatInterface();
} else {
    console.log('❌ Some files failed to process');
    showErrors(result);
}
```

### Option 2: Asynchronous Upload with Polling

```javascript
// Upload files asynchronously
const formData = new FormData();
files.forEach(file => formData.append('files', file));
formData.append('conversation_id', conversationId);
formData.append('sync_processing', 'false'); // Background processing

await fetch('/api/chat/upload-file', {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` },
    body: formData
});

// Poll for completion
async function waitForCompletion() {
    while (true) {
        const response = await fetch(`/api/chat/conversation-ready/${conversationId}`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        
        const status = await response.json();
        
        if (status.ready) {
            console.log('✅ Files ready!');
            enableChatInterface();
            break;
        }
        
        console.log(`⏳ Processing: ${status.processed_count}/${status.files_count}`);
        await new Promise(resolve => setTimeout(resolve, 2000));
    }
}

waitForCompletion();
```

### Option 3: Check Before Each Message

```javascript
async function sendMessage(conversationId, message) {
    // Check if conversation is ready
    const readyResponse = await fetch(`/api/chat/conversation-ready/${conversationId}`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });
    
    const status = await readyResponse.json();
    
    if (!status.ready) {
        alert('Files are still processing. Please wait.');
        return;
    }
    
    // Send the message
    const response = await fetch('/api/chat/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            message: message,
            conversation_id: conversationId
        })
    });
    
    const result = await response.json();
    displayResponse(result.response);
}
```

## UI/UX Recommendations

### 1. Loading States

```javascript
// Show loading during synchronous upload
function showFileProcessingLoader() {
    // Show spinner with message: "Processing files... Please wait."
    // Disable chat input
    // Show progress if possible
}

function hideFileProcessingLoader() {
    // Hide spinner
    // Enable chat input
    // Show success message
}
```

### 2. Progress Indicators

```javascript
// For multiple files, show individual file status
function updateFileStatus(fileId, status) {
    const fileElement = document.querySelector(`[data-file-id="${fileId}"]`);
    
    switch (status) {
        case 'uploading':
            fileElement.innerHTML = '📤 Uploading...';
            break;
        case 'processing':
            fileElement.innerHTML = '⚙️ Processing...';
            break;
        case 'completed':
            fileElement.innerHTML = '✅ Ready';
            break;
        case 'failed':
            fileElement.innerHTML = '❌ Failed';
            break;
    }
}
```

### 3. Chat Interface States

```javascript
// Disable chat while files are processing
function disableChatInterface() {
    document.getElementById('messageInput').disabled = true;
    document.getElementById('sendButton').disabled = true;
    document.getElementById('sendButton').textContent = 'Processing files...';
}

function enableChatInterface() {
    document.getElementById('messageInput').disabled = false;
    document.getElementById('sendButton').disabled = false;
    document.getElementById('sendButton').textContent = 'Send';
}
```

## Real-time Updates (Alternative)

### WebSocket Implementation

```javascript
// Connect to real-time file processing updates
const ws = new WebSocket(`ws://localhost:8000/api/chat/ws/file-processing/${conversationId}`);

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    switch (data.type) {
        case 'file_processing_started':
            updateFileStatus(data.file_id, 'processing');
            break;
            
        case 'file_processing_completed':
            updateFileStatus(data.file_id, data.status);
            break;
            
        case 'all_files_processed':
            enableChatInterface();
            showSuccess('All files processed! You can now chat.');
            break;
    }
};
```

## Complete Workflow Example

```javascript
async function handleFileUploadWorkflow(conversationId, files, firstMessage) {
    try {
        // 1. Show loading state
        showFileProcessingLoader();
        disableChatInterface();
        
        // 2. Upload files synchronously (blocks until complete)
        const formData = new FormData();
        files.forEach(file => formData.append('files', file));
        formData.append('conversation_id', conversationId);
        formData.append('sync_processing', 'true');
        
        const uploadResponse = await fetch('/api/chat/upload-file', {
            method: 'POST',
            headers: { 'Authorization': `Bearer ${token}` },
            body: formData
        });
        
        const uploadResult = await uploadResponse.json();
        
        // 3. Check if upload was successful
        const allProcessed = uploadResult.every(file => 
            file.processing_status === 'completed' && !file.error
        );
        
        if (!allProcessed) {
            throw new Error('Some files failed to process');
        }
        
        // 4. Files are ready, enable chat
        hideFileProcessingLoader();
        enableChatInterface();
        showSuccess('Files processed successfully!');
        
        // 5. Send the first message if provided
        if (firstMessage) {
            await sendMessage(conversationId, firstMessage);
        }
        
    } catch (error) {
        hideFileProcessingLoader();
        showError('File processing failed: ' + error.message);
        
        // Optionally enable chat anyway for regular conversation
        enableChatInterface();
    }
}
```

## Error Handling

### Common Error Scenarios

1. **File too large**: Show specific error message
2. **Unsupported file type**: List supported formats
3. **Processing timeout**: Offer retry option
4. **Network error**: Show retry button

```javascript
function handleUploadError(error, files) {
    if (error.message.includes('too large')) {
        showError('File too large. Maximum size: 10MB');
    } else if (error.message.includes('Unsupported')) {
        showError('Unsupported file type. Supported: PDF, TXT, DOC, DOCX, CSV, MD');
    } else if (error.message.includes('timeout')) {
        showError('Processing timeout. Please try again.');
        showRetryButton();
    } else {
        showError('Upload failed: ' + error.message);
    }
}
```

## Performance Considerations

### 1. File Size Limits
- Current limit: 10MB per file
- Maximum 3 files per upload
- Consider chunked upload for larger files

### 2. Processing Time
- PDF processing: ~5-30 seconds depending on size
- Text files: ~1-5 seconds
- Show estimated time based on file size

### 3. User Experience
- Use synchronous upload for better UX (user knows when ready)
- Show progress indicators
- Provide clear feedback on success/failure

## Testing

### Test Scenarios

1. **Single file upload**: Verify blocking works
2. **Multiple files**: Check all files processed before enabling chat
3. **Mixed success/failure**: Handle partial failures gracefully
4. **Large files**: Test timeout handling
5. **Network interruption**: Test error recovery

### Test Commands

```bash
# Test synchronous upload
curl -X POST "http://localhost:8000/api/chat/upload-file" \
  -H "Authorization: Bearer $TOKEN" \
  -F "files=@test.pdf" \
  -F "conversation_id=test-conv-123" \
  -F "sync_processing=true"

# Test conversation ready check
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/chat/conversation-ready/test-conv-123"
```

## Migration from Existing Implementation

If you have existing async file upload code:

1. **Add sync_processing parameter**: Set to `true` for blocking behavior
2. **Update UI**: Add loading states and disable chat during processing
3. **Add readiness checks**: Use the new endpoint to verify before chat
4. **Handle errors**: Implement proper error handling for failed processing

The new implementation is backward compatible - existing async behavior works with `sync_processing=false`. 