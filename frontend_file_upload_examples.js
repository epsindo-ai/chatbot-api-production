// Frontend Examples for File Upload with Conversation Blocking
// This shows how to implement file upload that blocks conversation until processing is complete

const API_BASE = 'http://localhost:35430/api/chat';
const AUTH_TOKEN = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbGhhbSIsImV4cCI6MTc0ODI0Mzg1N30.Efxck_Ijpr-PtGOFG7Fwv4bea65eEAYZ89cyAowm9Ow';

// Example 1: Synchronous File Upload (Blocks until processing complete)
async function uploadFilesSync(conversationId, files) {
    const formData = new FormData();
    
    // Add files to form data
    files.forEach(file => {
        formData.append('files', file);
    });
    
    // Add conversation ID and sync processing flag
    formData.append('conversation_id', conversationId);
    formData.append('sync_processing', 'true'); // This makes it wait for completion
    
    try {
        console.log('Uploading files synchronously...');
        
        const response = await fetch(`${API_BASE}/upload-file`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${AUTH_TOKEN}`
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Upload complete:', result);
        
        // Check if all files were processed successfully
        const allProcessed = result.every(file => 
            file.processing_status === 'completed' && !file.error
        );
        
        if (allProcessed) {
            console.log('✅ All files processed successfully! Conversation is ready for chat.');
            return { success: true, files: result };
        } else {
            console.log('❌ Some files failed to process:', result);
            return { success: false, files: result };
        }
        
    } catch (error) {
        console.error('Upload error:', error);
        return { success: false, error: error.message };
    }
}

// Example 2: Asynchronous File Upload with Polling
async function uploadFilesAsync(conversationId, files) {
    const formData = new FormData();
    
    files.forEach(file => {
        formData.append('files', file);
    });
    
    formData.append('conversation_id', conversationId);
    formData.append('sync_processing', 'false'); // Async processing
    
    try {
        console.log('Uploading files asynchronously...');
        
        // Upload files
        const response = await fetch(`${API_BASE}/upload-file`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${AUTH_TOKEN}`
            },
            body: formData
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        console.log('Upload started:', result);
        
        // Poll for completion
        return await pollForCompletion(conversationId);
        
    } catch (error) {
        console.error('Upload error:', error);
        return { success: false, error: error.message };
    }
}

// Helper function to poll for file processing completion
async function pollForCompletion(conversationId, maxAttempts = 30) {
    for (let attempt = 1; attempt <= maxAttempts; attempt++) {
        try {
            const response = await fetch(`${API_BASE}/conversation-ready/${conversationId}`, {
                headers: {
                    'Authorization': `Bearer ${AUTH_TOKEN}`
                }
            });
            
            if (!response.ok) {
                throw new Error(`Status check failed: ${response.statusText}`);
            }
            
            const status = await response.json();
            console.log(`Attempt ${attempt}: ${status.message}`);
            
            if (status.ready) {
                console.log('✅ All files processed! Conversation is ready for chat.');
                return { success: true, status };
            }
            
            // Wait 2 seconds before next check
            await new Promise(resolve => setTimeout(resolve, 2000));
            
        } catch (error) {
            console.error(`Status check attempt ${attempt} failed:`, error);
        }
    }
    
    console.log('❌ Timeout waiting for file processing');
    return { success: false, error: 'Timeout waiting for file processing' };
}

// Example 3: Check if conversation is ready before sending messages
async function isConversationReady(conversationId) {
    try {
        const response = await fetch(`${API_BASE}/conversation-ready/${conversationId}`, {
            headers: {
                'Authorization': `Bearer ${AUTH_TOKEN}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Status check failed: ${response.statusText}`);
        }
        
        const status = await response.json();
        return status.ready;
        
    } catch (error) {
        console.error('Error checking conversation status:', error);
        return false;
    }
}

// Example 4: Send chat message with readiness check
async function sendChatMessage(conversationId, message) {
    // First check if conversation is ready
    const ready = await isConversationReady(conversationId);
    
    if (!ready) {
        console.log('⏳ Conversation not ready yet, files are still processing...');
        return { 
            success: false, 
            error: 'Files are still being processed. Please wait.' 
        };
    }
    
    // Send the chat message
    try {
        const response = await fetch(`${API_BASE}/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${AUTH_TOKEN}`
            },
            body: JSON.stringify({
                message: message,
                conversation_id: conversationId
            })
        });
        
        if (!response.ok) {
            throw new Error(`Chat failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        return { success: true, response: result.response };
        
    } catch (error) {
        console.error('Chat error:', error);
        return { success: false, error: error.message };
    }
}

// Example 5: Complete workflow with UI feedback
async function handleFileUploadAndChat(conversationId, files, userMessage) {
    // Show loading state
    showLoadingState('Uploading and processing files...');
    
    try {
        // Option A: Use synchronous upload (blocks until complete)
        const uploadResult = await uploadFilesSync(conversationId, files);
        
        if (!uploadResult.success) {
            showError('File upload failed: ' + (uploadResult.error || 'Unknown error'));
            return;
        }
        
        // Files are processed, conversation is ready
        hideLoadingState();
        showSuccess('Files processed successfully! You can now chat.');
        
        // Send the chat message
        const chatResult = await sendChatMessage(conversationId, userMessage);
        
        if (chatResult.success) {
            displayChatResponse(chatResult.response);
        } else {
            showError('Chat failed: ' + chatResult.error);
        }
        
    } catch (error) {
        hideLoadingState();
        showError('Error: ' + error.message);
    }
}

// Example 6: Using WebSocket for real-time updates (alternative to polling)
function connectToFileProcessingUpdates(conversationId) {
    const ws = new WebSocket(`ws://localhost:8000/api/chat/ws/file-processing/${conversationId}`);
    
    ws.onopen = () => {
        console.log('Connected to file processing updates');
    };
    
    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        
        switch (data.type) {
            case 'file_processing_started':
                console.log(`Processing started for: ${data.filename}`);
                showFileProcessingStatus(data.file_id, 'processing');
                break;
                
            case 'file_processing_completed':
                console.log(`Processing completed for: ${data.filename}`);
                showFileProcessingStatus(data.file_id, data.status);
                break;
                
            case 'all_files_processed':
                console.log('All files processed! Conversation ready.');
                showConversationReady();
                break;
                
            case 'error':
                console.error('Processing error:', data.message);
                showError(data.message);
                break;
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
    
    ws.onclose = () => {
        console.log('WebSocket connection closed');
    };
    
    return ws;
}

// UI Helper Functions (implement these based on your UI framework)
function showLoadingState(message) {
    console.log('🔄 ' + message);
    // Update your UI to show loading spinner and message
}

function hideLoadingState() {
    console.log('✅ Loading complete');
    // Hide loading spinner
}

function showSuccess(message) {
    console.log('✅ ' + message);
    // Show success notification
}

function showError(message) {
    console.error('❌ ' + message);
    // Show error notification
}

function displayChatResponse(response) {
    console.log('💬 Bot response:', response);
    // Add response to chat UI
}

function showFileProcessingStatus(fileId, status) {
    console.log(`📄 File ${fileId}: ${status}`);
    // Update file status in UI
}

function showConversationReady() {
    console.log('🎉 Conversation is ready for chat!');
    // Enable chat input, hide processing indicators
}

// Usage Examples:

// Example usage 1: Synchronous upload with immediate chat
/*
const files = document.getElementById('fileInput').files;
const conversationId = 'your-conversation-id';
const message = 'What does this document say about...?';

handleFileUploadAndChat(conversationId, files, message);
*/

// Example usage 2: Asynchronous upload with polling
/*
const files = document.getElementById('fileInput').files;
const conversationId = 'your-conversation-id';

uploadFilesAsync(conversationId, files).then(result => {
    if (result.success) {
        console.log('Files ready! You can now chat.');
        // Enable chat interface
    } else {
        console.error('Upload failed:', result.error);
    }
});
*/

// Example usage 3: Check before sending each message
/*
document.getElementById('sendButton').addEventListener('click', async () => {
    const message = document.getElementById('messageInput').value;
    const conversationId = getCurrentConversationId();
    
    const result = await sendChatMessage(conversationId, message);
    if (!result.success) {
        alert(result.error);
    }
});
*/ 