# Frontend File Processing Integration Guide

## Overview

Since file processing is now asynchronous, the frontend needs to handle notifications when processing is complete. Here are three approaches you can use:

## 1. Polling Approach (Simplest)

### JavaScript Implementation:

```javascript
class FileProcessingManager {
    constructor(apiBaseUrl, authToken) {
        this.apiBaseUrl = apiBaseUrl;
        this.authToken = authToken;
        this.pollInterval = 3000; // 3 seconds
        this.maxPollTime = 300000; // 5 minutes
    }

    async uploadFiles(files, conversationId) {
        const formData = new FormData();
        formData.append('conversation_id', conversationId);
        
        files.forEach(file => {
            formData.append('files', file);
        });

        const response = await fetch(`${this.apiBaseUrl}/api/chat/upload-file`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.authToken}`
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }

        const result = await response.json();
        
        // Start polling for completion
        this.startPolling(conversationId);
        
        return result;
    }

    async startPolling(conversationId) {
        const startTime = Date.now();
        
        while (Date.now() - startTime < this.maxPollTime) {
            try {
                const status = await this.checkFileStatus(conversationId);
                
                if (status.status === 'ready') {
                    this.onAllFilesProcessed(conversationId, status.files);
                    return;
                } else if (status.status === 'error') {
                    this.onProcessingError(conversationId, status.message);
                    return;
                } else if (status.status === 'processing') {
                    this.onProcessingUpdate(conversationId, status.files);
                }
                
                await this.sleep(this.pollInterval);
            } catch (error) {
                console.error('Error checking file status:', error);
                await this.sleep(this.pollInterval);
            }
        }
        
        this.onProcessingTimeout(conversationId);
    }

    async checkFileStatus(conversationId) {
        const response = await fetch(`${this.apiBaseUrl}/api/chat/file-status/${conversationId}`, {
            headers: {
                'Authorization': `Bearer ${this.authToken}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Status check failed: ${response.statusText}`);
        }
        
        return await response.json();
    }

    // Event handlers - override these in your implementation
    onAllFilesProcessed(conversationId, files) {
        console.log('All files processed!', { conversationId, files });
        // Enable chat interface, show success message, etc.
        this.showNotification('Files processed successfully! You can now start chatting.', 'success');
        this.enableChatInterface();
    }

    onProcessingUpdate(conversationId, files) {
        const processed = files.filter(f => f.is_processed).length;
        const total = files.length;
        console.log(`Processing: ${processed}/${total} files completed`);
        
        // Update progress bar
        this.updateProgressBar(processed, total);
        this.showNotification(`Processing files: ${processed}/${total} completed`, 'info');
    }

    onProcessingError(conversationId, message) {
        console.error('File processing error:', message);
        this.showNotification(`Error processing files: ${message}`, 'error');
    }

    onProcessingTimeout(conversationId) {
        console.warn('File processing timeout');
        this.showNotification('File processing is taking longer than expected. Please try again.', 'warning');
    }

    // Utility methods
    sleep(ms) {
        return new Promise(resolve => setTimeout(resolve, ms));
    }

    showNotification(message, type) {
        // Implement your notification system here
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    updateProgressBar(current, total) {
        const percentage = (current / total) * 100;
        // Update your progress bar UI here
        console.log(`Progress: ${percentage}%`);
    }

    enableChatInterface() {
        // Enable chat input, remove loading states, etc.
        console.log('Chat interface enabled');
    }
}

// Usage example:
const fileManager = new FileProcessingManager('http://localhost:35430', 'your-jwt-token');

// When user uploads files:
document.getElementById('file-upload').addEventListener('change', async (event) => {
    const files = Array.from(event.target.files);
    const conversationId = getCurrentConversationId(); // Your function to get current conversation
    
    try {
        await fileManager.uploadFiles(files, conversationId);
    } catch (error) {
        console.error('Upload failed:', error);
        fileManager.showNotification('Upload failed. Please try again.', 'error');
    }
});
```

## 2. WebSocket Approach (Real-time)

### JavaScript Implementation:

```javascript
class WebSocketFileManager {
    constructor(apiBaseUrl, authToken) {
        this.apiBaseUrl = apiBaseUrl;
        this.authToken = authToken;
        this.websockets = new Map(); // conversationId -> WebSocket
    }

    async uploadFiles(files, conversationId) {
        // Connect to WebSocket first
        await this.connectWebSocket(conversationId);
        
        // Then upload files
        const formData = new FormData();
        formData.append('conversation_id', conversationId);
        
        files.forEach(file => {
            formData.append('files', file);
        });

        const response = await fetch(`${this.apiBaseUrl}/api/chat/upload-file`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.authToken}`
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }

        return await response.json();
    }

    async connectWebSocket(conversationId) {
        if (this.websockets.has(conversationId)) {
            return; // Already connected
        }

        const wsUrl = `ws://localhost:35430/api/chat/ws/file-processing/${conversationId}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log(`WebSocket connected for conversation ${conversationId}`);
            // Send heartbeat
            ws.send(JSON.stringify({ type: 'heartbeat' }));
        };

        ws.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleWebSocketMessage(conversationId, data);
            } catch (error) {
                console.error('Error parsing WebSocket message:', error);
            }
        };

        ws.onclose = () => {
            console.log(`WebSocket disconnected for conversation ${conversationId}`);
            this.websockets.delete(conversationId);
        };

        ws.onerror = (error) => {
            console.error('WebSocket error:', error);
        };

        this.websockets.set(conversationId, ws);
    }

    handleWebSocketMessage(conversationId, data) {
        switch (data.type) {
            case 'heartbeat':
                console.log('WebSocket heartbeat received');
                break;
                
            case 'file_processing_started':
                this.onFileProcessingStarted(conversationId, data);
                break;
                
            case 'file_processing_completed':
                this.onFileProcessingCompleted(conversationId, data);
                break;
                
            case 'all_files_processed':
                this.onAllFilesProcessed(conversationId, data);
                break;
                
            case 'file_processing_error':
                this.onFileProcessingError(conversationId, data);
                break;
                
            default:
                console.log('Unknown WebSocket message type:', data.type);
        }
    }

    // Event handlers
    onFileProcessingStarted(conversationId, data) {
        console.log(`Started processing file: ${data.filename}`);
        this.showNotification(`Processing ${data.filename}...`, 'info');
    }

    onFileProcessingCompleted(conversationId, data) {
        console.log(`Completed processing file: ${data.filename}`);
        if (data.status === 'success') {
            this.showNotification(`✓ ${data.filename} processed successfully`, 'success');
        } else {
            this.showNotification(`✗ Failed to process ${data.filename}`, 'error');
        }
    }

    onAllFilesProcessed(conversationId, data) {
        console.log('All files processed!');
        this.showNotification('All files processed! You can now start chatting.', 'success');
        this.enableChatInterface();
        
        // Close WebSocket connection
        this.disconnectWebSocket(conversationId);
    }

    onFileProcessingError(conversationId, data) {
        console.error('File processing error:', data.error);
        this.showNotification(`Error processing files: ${data.error}`, 'error');
    }

    disconnectWebSocket(conversationId) {
        const ws = this.websockets.get(conversationId);
        if (ws) {
            ws.close();
            this.websockets.delete(conversationId);
        }
    }

    // Utility methods (same as polling approach)
    showNotification(message, type) {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    enableChatInterface() {
        console.log('Chat interface enabled');
    }
}
```

## 3. Server-Sent Events (SSE) Approach

### JavaScript Implementation:

```javascript
class SSEFileManager {
    constructor(apiBaseUrl, authToken) {
        this.apiBaseUrl = apiBaseUrl;
        this.authToken = authToken;
        this.eventSources = new Map(); // conversationId -> EventSource
    }

    async uploadFiles(files, conversationId) {
        // Connect to SSE first
        this.connectSSE(conversationId);
        
        // Then upload files
        const formData = new FormData();
        formData.append('conversation_id', conversationId);
        
        files.forEach(file => {
            formData.append('files', file);
        });

        const response = await fetch(`${this.apiBaseUrl}/api/chat/upload-file`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.authToken}`
            },
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }

        return await response.json();
    }

    connectSSE(conversationId) {
        if (this.eventSources.has(conversationId)) {
            return; // Already connected
        }

        const sseUrl = `${this.apiBaseUrl}/api/chat/sse/file-processing/${conversationId}`;
        const eventSource = new EventSource(sseUrl);

        eventSource.onopen = () => {
            console.log(`SSE connected for conversation ${conversationId}`);
        };

        eventSource.onmessage = (event) => {
            try {
                const data = JSON.parse(event.data);
                this.handleSSEMessage(conversationId, data);
            } catch (error) {
                console.error('Error parsing SSE message:', error);
            }
        };

        eventSource.onerror = (error) => {
            console.error('SSE error:', error);
            eventSource.close();
            this.eventSources.delete(conversationId);
        };

        this.eventSources.set(conversationId, eventSource);
    }

    handleSSEMessage(conversationId, data) {
        switch (data.type) {
            case 'connected':
                console.log('SSE connected');
                break;
                
            case 'file_processing_completed':
                this.onFileProcessingCompleted(conversationId, data);
                break;
                
            case 'all_files_processed':
                this.onAllFilesProcessed(conversationId, data);
                break;
                
            case 'error':
                this.onProcessingError(conversationId, data.message);
                break;
                
            default:
                console.log('Unknown SSE message type:', data.type);
        }
    }

    // Event handlers (similar to WebSocket approach)
    onFileProcessingCompleted(conversationId, data) {
        console.log(`Completed processing file: ${data.filename}`);
        this.showNotification(`✓ ${data.filename} processed successfully`, 'success');
    }

    onAllFilesProcessed(conversationId, data) {
        console.log('All files processed!');
        this.showNotification('All files processed! You can now start chatting.', 'success');
        this.enableChatInterface();
        
        // Close SSE connection
        this.disconnectSSE(conversationId);
    }

    onProcessingError(conversationId, message) {
        console.error('File processing error:', message);
        this.showNotification(`Error processing files: ${message}`, 'error');
    }

    disconnectSSE(conversationId) {
        const eventSource = this.eventSources.get(conversationId);
        if (eventSource) {
            eventSource.close();
            this.eventSources.delete(conversationId);
        }
    }

    // Utility methods
    showNotification(message, type) {
        console.log(`[${type.toUpperCase()}] ${message}`);
    }

    enableChatInterface() {
        console.log('Chat interface enabled');
    }
}
```

## 4. React Hook Example

### Custom Hook for File Processing:

```javascript
import { useState, useEffect, useCallback } from 'react';

export const useFileProcessing = (apiBaseUrl, authToken) => {
    const [processingStatus, setProcessingStatus] = useState({
        isProcessing: false,
        files: [],
        progress: 0,
        error: null
    });

    const uploadFiles = useCallback(async (files, conversationId) => {
        setProcessingStatus(prev => ({
            ...prev,
            isProcessing: true,
            error: null
        }));

        try {
            const formData = new FormData();
            formData.append('conversation_id', conversationId);
            
            files.forEach(file => {
                formData.append('files', file);
            });

            const response = await fetch(`${apiBaseUrl}/api/chat/upload-file`, {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${authToken}`
                },
                body: formData
            });

            if (!response.ok) {
                throw new Error(`Upload failed: ${response.statusText}`);
            }

            const result = await response.json();
            
            // Start polling for status
            pollForCompletion(conversationId);
            
            return result;
        } catch (error) {
            setProcessingStatus(prev => ({
                ...prev,
                isProcessing: false,
                error: error.message
            }));
            throw error;
        }
    }, [apiBaseUrl, authToken]);

    const pollForCompletion = useCallback(async (conversationId) => {
        const maxAttempts = 100; // 5 minutes with 3-second intervals
        let attempts = 0;

        const poll = async () => {
            try {
                const response = await fetch(`${apiBaseUrl}/api/chat/file-status/${conversationId}`, {
                    headers: {
                        'Authorization': `Bearer ${authToken}`
                    }
                });

                if (!response.ok) {
                    throw new Error('Failed to check status');
                }

                const status = await response.json();
                
                setProcessingStatus(prev => ({
                    ...prev,
                    files: status.files,
                    progress: status.files.length > 0 
                        ? (status.files.filter(f => f.is_processed).length / status.files.length) * 100 
                        : 0
                }));

                if (status.status === 'ready') {
                    setProcessingStatus(prev => ({
                        ...prev,
                        isProcessing: false,
                        progress: 100
                    }));
                    return;
                } else if (status.status === 'error') {
                    setProcessingStatus(prev => ({
                        ...prev,
                        isProcessing: false,
                        error: status.message
                    }));
                    return;
                }

                attempts++;
                if (attempts < maxAttempts) {
                    setTimeout(poll, 3000);
                } else {
                    setProcessingStatus(prev => ({
                        ...prev,
                        isProcessing: false,
                        error: 'Processing timeout'
                    }));
                }
            } catch (error) {
                setProcessingStatus(prev => ({
                    ...prev,
                    isProcessing: false,
                    error: error.message
                }));
            }
        };

        poll();
    }, [apiBaseUrl, authToken]);

    return {
        processingStatus,
        uploadFiles,
        resetStatus: () => setProcessingStatus({
            isProcessing: false,
            files: [],
            progress: 0,
            error: null
        })
    };
};

// Usage in React component:
const FileUploadComponent = () => {
    const { processingStatus, uploadFiles, resetStatus } = useFileProcessing(
        'http://localhost:35430',
        'your-jwt-token'
    );

    const handleFileUpload = async (event) => {
        const files = Array.from(event.target.files);
        const conversationId = getCurrentConversationId();
        
        try {
            await uploadFiles(files, conversationId);
        } catch (error) {
            console.error('Upload failed:', error);
        }
    };

    return (
        <div>
            <input type="file" multiple onChange={handleFileUpload} />
            
            {processingStatus.isProcessing && (
                <div>
                    <p>Processing files... {processingStatus.progress.toFixed(0)}%</p>
                    <progress value={processingStatus.progress} max="100" />
                </div>
            )}
            
            {processingStatus.error && (
                <div style={{ color: 'red' }}>
                    Error: {processingStatus.error}
                </div>
            )}
            
            {processingStatus.progress === 100 && !processingStatus.isProcessing && (
                <div style={{ color: 'green' }}>
                    All files processed successfully!
                </div>
            )}
        </div>
    );
};
```

## Recommendation

For most applications, I recommend starting with the **Polling Approach** because:

1. **Simplicity**: Easy to implement and debug
2. **Reliability**: Works with all browsers and network configurations
3. **No connection management**: No need to handle WebSocket/SSE disconnections
4. **Good enough performance**: 3-5 second polling is responsive enough for file processing

You can always upgrade to WebSocket or SSE later if you need real-time updates for other features.

## API Endpoints Summary

- **Upload files**: `POST /api/chat/upload-file`
- **Check status**: `GET /api/chat/file-status/{conversation_id}`
- **WebSocket**: `ws://localhost:35430/api/chat/ws/file-processing/{conversation_id}`
- **SSE**: `GET /api/chat/sse/file-processing/{conversation_id}`

All endpoints require JWT authentication via the `Authorization: Bearer <token>` header. 