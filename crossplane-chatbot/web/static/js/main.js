const socket = io();

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

function createMessageElement(message) {
    const messageEl = document.createElement('div');
    messageEl.classList.add('message', message.role);
    
    if (message.content.includes('```')) {
        const parts = message.content.split(/```(?:yaml)?/);
        for (let i = 0; i < parts.length; i++) {
            if (i % 2 === 0) {
                // Regular text
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

function sendMessage() {
    const message = messageInput.value.trim();
    if (message) {
        socket.emit('message', { message });
        messageInput.value = '';
    }
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
        } else {
            socket.emit('message', { message: command });
        }
    });
});

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

socket.on('connect', () => {
    console.log('Connected to server');
});

socket.on('message', (message) => {
    chatMessages.appendChild(createMessageElement(message));
    chatMessages.scrollTop = chatMessages.scrollHeight;
});

socket.on('error', (data) => {
    const errorMessage = {
        role: 'assistant',
        content: `Error: ${data.message}`
    };
    chatMessages.appendChild(createMessageElement(errorMessage));
    chatMessages.scrollTop = chatMessages.scrollHeight;
});

socket.on('state_update', (state) => {
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
});

socket.on('yaml_manifest', (data) => {
    yamlOutputEl.textContent = data.content;
    hljs.highlightElement(yamlOutputEl);
});

function formatStateLabel(label) {
    return label
        .replace(/_/g, ' ')
        .replace(/\b\w/g, l => l.toUpperCase());
}

hljs.highlightAll();
