const chatMessages = document.getElementById('chat-messages');
const messageInput = document.getElementById('message-input');
const sendButton = document.getElementById('send-button');
const commandButtons = document.querySelectorAll('.command-btn');

const currentStepEl = document.getElementById('current-step');
const cloudProviderEl = document.getElementById('cloud-provider');
const resourceTypeEl = document.getElementById('resource-type');
const completedStepsEl = document.getElementById('completed-steps');
const collectedDataEl = document.getElementById('collected-data');
const yamlOutputEl = document.getElementById('yaml-output');

document.addEventListener('DOMContentLoaded', initializeConversation);

function createMessageElement(message) {
    const messageEl = document.createElement('div');
    messageEl.classList.add('message', message.role);
    
    if (message.content.includes('```')) {
        const parts = message.content.split(/```(?:yaml)?/);
        for (let i = 0; i < parts.length; i++) {
            if (i % 2 === 0) {
                const textNode = document.createElement('div');
                textNode.textContent = parts[i].trim();
                if (textNode.textContent) {
                    messageEl.appendChild(textNode);
                }
            } else {
                const pre = document.createElement('pre');
                const code = document.createElement('code');
                code.classList.add('language-yaml');
                code.textContent = parts[i].trim();
                pre.appendChild(code);
                messageEl.appendChild(pre);
                
                hljs.highlightElement(code);
            }
        }
    } else {
        messageEl.textContent = message.content;
    }
    
    return messageEl;
}

async function initializeConversation() {
    try {
        const response = await fetch('/api/initialize', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        if (data.messages) {
            chatMessages.innerHTML = '';
            data.messages.forEach(message => {
                chatMessages.appendChild(createMessageElement(message));
            });
            chatMessages.scrollTop = chatMessages.scrollHeight;
        } else if (data.message) {
            chatMessages.innerHTML = '';
            chatMessages.appendChild(createMessageElement({
                role: 'assistant',
                content: data.message
            }));
        }
        
        updateStateDisplay(data.state);
    } catch (error) {
        showError('Failed to initialize conversation: ' + error.message);
    }
}

async function sendMessage() {
    const message = messageInput.value.trim();
    if (!message) return;
    
    messageInput.value = '';
    

    chatMessages.appendChild(createMessageElement({
        role: 'user',
        content: message
    }));
    chatMessages.scrollTop = chatMessages.scrollHeight;
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ message })
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        if (data.message) {
            chatMessages.appendChild(createMessageElement({
                role: 'assistant',
                content: data.message
            }));
            chatMessages.scrollTop = chatMessages.scrollHeight;
        }
        
        if (data.state) {
            updateStateDisplay(data.state);
        }
        
        if (data.manifest) {
            yamlOutputEl.textContent = data.manifest;
            hljs.highlightElement(yamlOutputEl);
        }
    } catch (error) {
        showError('Failed to send message: ' + error.message);
    }
}

async function resetConversation() {
    try {
        const response = await fetch('/api/reset', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        });
        
        const data = await response.json();
        
        if (data.error) {
            showError(data.error);
            return;
        }
        
        chatMessages.innerHTML = '';
        if (data.messages) {
            data.messages.forEach(message => {
                chatMessages.appendChild(createMessageElement(message));
            });
        } else if (data.message) {
            chatMessages.appendChild(createMessageElement({
                role: 'assistant',
                content: data.message
            }));
        }
        chatMessages.scrollTop = chatMessages.scrollHeight;
        
        if (data.state) {
            updateStateDisplay(data.state);
        }
        
        yamlOutputEl.textContent = '';
    } catch (error) {
        showError('Failed to reset conversation: ' + error.message);
    }
}

function updateStateDisplay(state) {
    if (!state) return;
    
    currentStepEl.textContent = formatStateLabel(state.current_step || 'initial');
    cloudProviderEl.textContent = state.cloud_provider || 'None';
    resourceTypeEl.textContent = state.resource_type || 'None';
    
    completedStepsEl.innerHTML = '';
    if (state.completed_steps && state.completed_steps.length > 0) {
        state.completed_steps.forEach(step => {
            const stepEl = document.createElement('span');
            stepEl.classList.add('state-list-item');
            stepEl.textContent = formatStateLabel(step);
            completedStepsEl.appendChild(stepEl);
        });
    } else {
        completedStepsEl.textContent = 'None';
    }
    
    collectedDataEl.innerHTML = '';
    if (state.collected_data && Object.keys(state.collected_data).length > 0) {
        for (const [key, value] of Object.entries(state.collected_data)) {
            const dataItemEl = document.createElement('div');
            dataItemEl.classList.add('data-item');
            
            const keyEl = document.createElement('span');
            keyEl.classList.add('data-key');
            keyEl.textContent = formatStateLabel(key);
            
            const valueEl = document.createElement('span');
            valueEl.classList.add('data-value');
            valueEl.textContent = value;
            
            dataItemEl.appendChild(keyEl);
            dataItemEl.appendChild(valueEl);
            collectedDataEl.appendChild(dataItemEl);
        }
    } else {
        const emptyEl = document.createElement('p');
        emptyEl.classList.add('empty-state');
        emptyEl.textContent = 'No data collected yet';
        collectedDataEl.appendChild(emptyEl);
    }
}

function showError(errorMessage) {
    chatMessages.appendChild(createMessageElement({
        role: 'assistant',
        content: `Error: ${errorMessage}`
    }));
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function displayHelpMessage() {
    const helpMessage = {
        role: 'assistant',
        content: `
            Available commands:
            - undo: Undo the last step
            - restart: Start a new conversation
            - help: Show this help message
            
            Tips:
            - Be specific about the cloud provider and resource type you want to create
            - Your conversation state is shown on the right panel
            - Generated YAML will appear in the bottom right panel
        `
    };
    
    chatMessages.appendChild(createMessageElement(helpMessage));
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function formatStateLabel(label) {
    return label
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

sendButton.addEventListener('click', sendMessage);
messageInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
        sendMessage();
    }
});

commandButtons.forEach(button => {
    button.addEventListener('click', () => {
        const command = button.dataset.command;
        if (command === 'help') {
            displayHelpMessage();
        } else if (command === 'restart') {
            resetConversation();
        } else {
            sendMessage({ message: command });
        }
    });
});

hljs.highlightAll();
