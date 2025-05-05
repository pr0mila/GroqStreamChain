document.addEventListener('DOMContentLoaded', () => {
    // DOM Elements
    const messagesContainer = document.getElementById('chat-messages');
    const messageInput = document.getElementById('message-input');
    const sendButton = document.getElementById('send-button');
    const connectionStatus = document.getElementById('connection-status');
    
    // State variables
    let socket = null;
    let sessionId = null;
    let isProcessing = false;
    let currentAssistantMessageElement = null;
    let reconnectAttempts = 0;
    const maxReconnectAttempts = 5;
    
    // Initialize the WebSocket connection
    function connectWebSocket() {
        try {
            connectionStatus.textContent = 'Connecting...';
            
            // Close existing socket if any
            if (socket) {
                socket.close();
            }
            
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            const wsUrl = `${protocol}//${window.location.host}/ws/chat`;
            
            console.log(`Connecting to WebSocket at: ${wsUrl}`);
            socket = new WebSocket(wsUrl);
            
            socket.onopen = () => {
                console.log('WebSocket connection established');
                connectionStatus.textContent = 'Connected';
                connectionStatus.classList.add('connected');
                connectionStatus.classList.remove('disconnected');
                sendButton.disabled = false;
                reconnectAttempts = 0;
            };
            
            socket.onclose = (event) => {
                console.log(`WebSocket closed with code: ${event.code}`);
                connectionStatus.textContent = 'Disconnected';
                connectionStatus.classList.add('disconnected');
                connectionStatus.classList.remove('connected');
                sendButton.disabled = true;
                
                // Attempt to reconnect with exponential backoff
                if (reconnectAttempts < maxReconnectAttempts) {
                    reconnectAttempts++;
                    const delay = Math.min(1000 * Math.pow(2, reconnectAttempts), 10000);
                    setTimeout(connectWebSocket, delay);
                }
            };
            
            socket.onerror = (error) => {
                console.error('WebSocket Error:', error);
            };
            
            socket.onmessage = (event) => {
                try {
                    const data = JSON.parse(event.data);
                    console.log('Received message:', data);
                    handleSocketMessage(data);
                } catch (e) {
                    console.error('Error parsing message:', e);
                }
            };
        } catch (e) {
            console.error('Error connecting to WebSocket:', e);
        }
    }
    
    // Handle different types of messages from the server
    function handleSocketMessage(data) {
        switch (data.type) {
            case 'session_id':
                console.log('Received session ID:', data.session_id);
                sessionId = data.session_id;
                localStorage.setItem('chatSessionId', sessionId);
                break;
                
            case 'initial_message':
                console.log('Received initial message');
                const assistantMessageElement = createMessageElement(data.content, 'assistant');
                messagesContainer.appendChild(assistantMessageElement);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                break;
                
            case 'message_received':
                console.log('Message received by server, processing...');
                showTypingIndicator();
                break;
                
            case 'stream':
                if (!currentAssistantMessageElement) {
                    removeTypingIndicator();
                    currentAssistantMessageElement = createMessageElement('', 'assistant');
                    messagesContainer.appendChild(currentAssistantMessageElement);
                }
                appendToAssistantMessage(data.content);
                break;
                
            case 'stream_end':
                console.log('Stream ended');
                isProcessing = false;
                currentAssistantMessageElement = null;
                enableUserInput();
                break;
                
            case 'error':
                console.error('Error from server:', data.message);
                removeTypingIndicator();
                const errorElement = createMessageElement(data.message, 'assistant');
                errorElement.style.color = '#d9534f';
                messagesContainer.appendChild(errorElement);
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
                isProcessing = false;
                enableUserInput();
                break;
                
            default:
                console.log('Unknown message type:', data);
        }
    }
    
    // Create a new message element
    function createMessageElement(content, role) {
        const messageElement = document.createElement('div');
        messageElement.classList.add('message', `${role}-message`);
        
        // Process markdown-like formatting for code blocks
        content = processCodeBlocks(content);
        
        messageElement.innerHTML = content;
        return messageElement;
    }
    
    // Process code blocks in messages
    function processCodeBlocks(text) {
        // Simple markdown code block processing
        return text.replace(/```([\s\S]*?)```/g, (match, code) => {
            return `<div class="code-block">${code}</div>`;
        });
    }
    
    // Append content to the current assistant message
    function appendToAssistantMessage(content) {
        if (currentAssistantMessageElement) {
            // Process markdown-like formatting for code blocks
            const processedContent = processCodeBlocks(
                currentAssistantMessageElement.innerHTML + content
            );
            currentAssistantMessageElement.innerHTML = processedContent;
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }
    
    // Show the typing indicator
    function showTypingIndicator() {
        removeTypingIndicator(); // Remove existing indicator if any
        
        const typingIndicator = document.createElement('div');
        typingIndicator.classList.add('typing-indicator');
        typingIndicator.id = 'typing-indicator';
        
        for (let i = 0; i < 3; i++) {
            const dot = document.createElement('div');
            dot.classList.add('typing-dot');
            typingIndicator.appendChild(dot);
        }
        
        messagesContainer.appendChild(typingIndicator);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
    
    // Remove the typing indicator
    function removeTypingIndicator() {
        const existingIndicator = document.getElementById('typing-indicator');
        if (existingIndicator) {
            existingIndicator.remove();
        }
    }
    
    // Send a message to the server
    function sendMessage() {
        const message = messageInput.value.trim();
        if (message && !isProcessing && socket && socket.readyState === WebSocket.OPEN) {
            // Add user message to the UI
            const userMessageElement = createMessageElement(message, 'user');
            messagesContainer.appendChild(userMessageElement);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
            
            // Clear input and disable until response is complete
            messageInput.value = '';
            disableUserInput();
            
            try {
                // Send message to server
                socket.send(JSON.stringify({ message }));
                isProcessing = true;
            } catch (e) {
                console.error('Error sending message:', e);
                enableUserInput();
                const errorElement = createMessageElement(
                    "Failed to send message. Please try again.", 
                    'assistant'
                );
                errorElement.style.color = '#d9534f';
                messagesContainer.appendChild(errorElement);
            }
        }
    }
    
    // Disable user input during processing
    function disableUserInput() {
        messageInput.disabled = true;
        sendButton.disabled = true;
    }
    
    // Enable user input when processing is complete
    function enableUserInput() {
        messageInput.disabled = false;
        sendButton.disabled = false;
        messageInput.focus();
    }
    
    // Event listeners
    sendButton.addEventListener('click', sendMessage);
    
    messageInput.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    // Initialize connection
    connectWebSocket();
});