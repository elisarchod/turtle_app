// API Base URL
const API_BASE = '';

// DOM Elements
const chatMessages = document.getElementById('chatMessages');
const messageInput = document.getElementById('messageInput');
const sendButton = document.getElementById('sendButton');
const loadingIndicator = document.getElementById('loadingIndicator');
const healthStatus = document.getElementById('healthStatus');
const statusIndicator = document.getElementById('statusIndicator');
const statusText = document.getElementById('statusText');
const statusTime = document.getElementById('statusTime');

// Thread ID management
const THREAD_ID_KEY = 'turtle_app_thread_id';

function getThreadId() {
    return localStorage.getItem(THREAD_ID_KEY);
}

function setThreadId(threadId) {
    localStorage.setItem(THREAD_ID_KEY, threadId);
}

// Auto-resize textarea
messageInput.addEventListener('input', function() {
    this.style.height = 'auto';
    this.style.height = Math.min(this.scrollHeight, 120) + 'px';
});

// Send message on Enter (Shift+Enter for new line)
messageInput.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// Send button click
sendButton.addEventListener('click', sendMessage);

// API Functions
async function sendChatMessage(message, threadId = null) {
    const response = await fetch(`${API_BASE}/chat`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            message: message,
            thread_id: threadId
        })
    });

    if (!response.ok) {
        const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
        throw new Error(error.detail || `HTTP error! status: ${response.status}`);
    }

    return await response.json();
}

async function getHealthStatus() {
    try {
        const response = await fetch(`${API_BASE}/health`);
        if (!response.ok) {
            throw new Error('Health check failed');
        }
        return await response.json();
    } catch (error) {
        return null;
    }
}

// UI Functions
function addMessage(content, isUser = false) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${isUser ? 'user' : 'assistant'}`;
    
    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';
    
    // Convert plain text to HTML with line breaks
    const formattedContent = content
        .split('\n')
        .map(line => line.trim() ? `<p>${escapeHtml(line)}</p>` : '')
        .join('');
    
    contentDiv.innerHTML = formattedContent;
    messageDiv.appendChild(contentDiv);
    
    chatMessages.appendChild(messageDiv);
    scrollToBottom();
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function showError(message) {
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = `Error: ${message}`;
    chatMessages.appendChild(errorDiv);
    scrollToBottom();
}

function scrollToBottom() {
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function setLoading(loading) {
    if (loading) {
        loadingIndicator.style.display = 'flex';
        sendButton.disabled = true;
        messageInput.disabled = true;
    } else {
        loadingIndicator.style.display = 'none';
        sendButton.disabled = false;
        messageInput.disabled = false;
    }
}

function updateHealthStatus(health) {
    if (health) {
        statusIndicator.className = 'status-indicator healthy';
        statusText.textContent = `Status: ${health.status}`;
        const time = new Date(health.time);
        statusTime.textContent = `Last checked: ${time.toLocaleTimeString()}`;
    } else {
        statusIndicator.className = 'status-indicator unhealthy';
        statusText.textContent = 'Status: Unavailable';
        statusTime.textContent = 'Connection error';
    }
}

// Main send message function
async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;

    // Add user message to chat
    addMessage(message, true);
    messageInput.value = '';
    messageInput.style.height = 'auto';

    // Show loading state
    setLoading(true);

    try {
        // Get thread ID from storage
        const threadId = getThreadId();
        
        // Send message to API
        const response = await sendChatMessage(message, threadId);
        
        // Store thread ID for conversation continuity
        if (response.thread_id) {
            setThreadId(response.thread_id);
        }
        
        // Add assistant response to chat
        addMessage(response.response, false);
    } catch (error) {
        console.error('Error sending message:', error);
        showError(error.message || 'Failed to send message. Please try again.');
    } finally {
        setLoading(false);
        messageInput.focus();
    }
}

// Health status polling
async function checkHealth() {
    const health = await getHealthStatus();
    updateHealthStatus(health);
}

// Initialize
document.addEventListener('DOMContentLoaded', function() {
    // Initial health check
    checkHealth();
    
    // Poll health status every 30 seconds
    setInterval(checkHealth, 30000);
    
    // Focus input on load
    messageInput.focus();
});

