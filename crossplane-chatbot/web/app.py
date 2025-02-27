from flask import Flask, render_template, request, jsonify, session
import os
import sys
import uuid
import json
from dotenv import load_dotenv

dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
load_dotenv(dotenv_path)

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from langchain.llms import OpenAI
from agents.orchestrator import OrchestratorAgent
from utils.conversation_state import ConversationState
from utils.error_handler import handle_errors, CrossplaneError

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', 'crossplane-chatbot-secret!')

active_conversations = {}

@app.route('/')
def index():
    """Render the main UI page"""
    if 'conversation_id' not in session:
        session['conversation_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@app.route('/api/initialize', methods=['POST'])
def initialize_conversation():
    """Initialize or get an existing conversation"""
    conversation_id = session.get('conversation_id')
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        session['conversation_id'] = conversation_id
    
    if conversation_id not in active_conversations:
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                return jsonify({
                    'error': 'OpenAI API key not set. Please check your .env file.'
                }), 500
            
            llm = OpenAI(api_key=api_key)
            
            state = ConversationState(conversation_id=conversation_id)
            
            orchestrator = OrchestratorAgent(llm, state=state)
            
            active_conversations[conversation_id] = {
                'state': state,
                'orchestrator': orchestrator,
                'messages': [{
                    'role': 'assistant',
                    'content': "Welcome to the Crossplane YAML Manifest Generator! I'll help you create infrastructure as code using Crossplane. What cloud provider would you like to use? (AWS or Azure)"
                }]
            }
            
            return jsonify({
                'conversation_id': conversation_id,
                'message': "Welcome to the Crossplane YAML Manifest Generator! I'll help you create infrastructure as code using Crossplane. What cloud provider would you like to use? (AWS or Azure)",
                'state': {
                    'current_step': state.state['current_step'],
                    'cloud_provider': state.state['cloud_provider'],
                    'resource_type': state.state['resource_type'],
                    'collected_data': state.state['collected_data'],
                    'completed_steps': state.state['completed_steps']
                }
            })
            
        except Exception as e:
            return jsonify({'error': f'Error initializing chatbot: {str(e)}'}), 500
    else:
        state = active_conversations[conversation_id]['state']
        messages = active_conversations[conversation_id]['messages']
        
        return jsonify({
            'conversation_id': conversation_id,
            'messages': messages,
            'state': {
                'current_step': state.state['current_step'],
                'cloud_provider': state.state['cloud_provider'],
                'resource_type': state.state['resource_type'],
                'collected_data': state.state['collected_data'],
                'completed_steps': state.state['completed_steps']
            }
        })

@app.route('/api/chat', methods=['POST'])
def chat():
    """Handle incoming message from client"""
    data = request.json
    user_input = data.get('message', '').strip()
    if not user_input:
        return jsonify({'error': 'No message provided'}), 400
    
    conversation_id = session.get('conversation_id')
    if not conversation_id or conversation_id not in active_conversations:
        return jsonify({'error': 'Session expired or invalid. Please refresh the page.'}), 400
    
    orchestrator = active_conversations[conversation_id]['orchestrator']
    state = active_conversations[conversation_id]['state']
    state.add_message('user', user_input)
    
    active_conversations[conversation_id]['messages'].append({
        'role': 'user',
        'content': user_input
    })
    
    if user_input.lower() == 'restart':
        state = ConversationState(conversation_id=conversation_id)
        orchestrator = OrchestratorAgent(orchestrator.llm, state=state)
        
        active_conversations[conversation_id] = {
            'state': state,
            'orchestrator': orchestrator,
            'messages': [{
                'role': 'assistant',
                'content': "Starting a new conversation. What cloud provider would you like to use? (AWS or Azure)"
            }]
        }
        
        return jsonify({
            'message': "Starting a new conversation. What cloud provider would you like to use? (AWS or Azure)",
            'state': {
                'current_step': state.state['current_step'],
                'cloud_provider': state.state['cloud_provider'],
                'resource_type': state.state['resource_type'],
                'collected_data': state.state['collected_data'],
                'completed_steps': state.state['completed_steps']
            },
            'messages': active_conversations[conversation_id]['messages']
        })
    
    try:
        response = orchestrator.process_message(user_input)
        
        if isinstance(response, dict) and response.get('error'):
            assistant_message = f"Error: {response.get('message', 'An error occurred')}"
            state.update(error_count=state.state['error_count'] + 1)
        else:
            content = response
            if isinstance(response, dict) and 'result' in response:
                content = response['result']
            
            manifest = None
            if isinstance(response, dict) and 'manifest' in response:
                manifest = response['manifest']
                message_content = response.get('message', "Here's your Crossplane manifest:")
                assistant_message = f"{message_content}\n\n```yaml\n{manifest}\n```"
                
                state.update(current_step='manifest_complete')
                state.mark_step_complete('generate_manifest')
            else:
                assistant_message = content
            
            state.add_message('assistant', assistant_message)
        
        active_conversations[conversation_id]['messages'].append({
            'role': 'assistant',
            'content': assistant_message
        })
        
        state.save()
        
        current_state = orchestrator.state.state
        
        yaml_content = None
        if '```yaml' in assistant_message and '```' in assistant_message.split('```yaml', 1)[1]:
            yaml_content = assistant_message.split('```yaml', 1)[1].split('```', 1)[0].strip()
        
        return jsonify({
            'message': assistant_message,
            'manifest': manifest or yaml_content,
            'state': {
                'current_step': current_state['current_step'],
                'cloud_provider': current_state['cloud_provider'],
                'resource_type': current_state['resource_type'],
                'collected_data': current_state['collected_data'],
                'completed_steps': current_state['completed_steps']
            },
            'messages': active_conversations[conversation_id]['messages']
        })
        
    except CrossplaneError as e:
        error_message = f"Error: {e.user_message}"
        
        active_conversations[conversation_id]['messages'].append({
            'role': 'assistant',
            'content': error_message
        })
        
        state.update(error_count=state.state['error_count'] + 1)
        state.save()
        
        return jsonify({
            'error': e.user_message,
            'message': error_message,
            'messages': active_conversations[conversation_id]['messages']
        })
        
    except Exception as e:
        error_message = f"An unexpected error occurred: {str(e)}. Please try again or restart the application."
        
        active_conversations[conversation_id]['messages'].append({
            'role': 'assistant',
            'content': error_message
        })
        
        state.update(error_count=state.state['error_count'] + 1)
        state.save()
        
        return jsonify({
            'error': str(e),
            'message': error_message,
            'messages': active_conversations[conversation_id]['messages']
        })

@app.route('/api/state', methods=['GET'])
def get_state():
    """Get the current state of the conversation"""
    conversation_id = session.get('conversation_id')
    if not conversation_id or conversation_id not in active_conversations:
        return jsonify({'error': 'Session expired or invalid. Please refresh the page.'}), 400
    
    state = active_conversations[conversation_id]['state']
    
    return jsonify({
        'state': {
            'current_step': state.state['current_step'],
            'cloud_provider': state.state['cloud_provider'],
            'resource_type': state.state['resource_type'],
            'collected_data': state.state['collected_data'],
            'completed_steps': state.state['completed_steps']
        }
    })

@app.route('/api/messages', methods=['GET'])
def get_messages():
    """Get conversation messages"""
    conversation_id = session.get('conversation_id')
    if not conversation_id or conversation_id not in active_conversations:
        return jsonify({'error': 'Session expired or invalid. Please refresh the page.'}), 400
    
    messages = active_conversations[conversation_id]['messages']
    
    return jsonify({
        'messages': messages
    })

@app.route('/api/reset', methods=['POST'])
def reset_conversation():
    """Reset the current conversation"""
    conversation_id = session.get('conversation_id')
    if not conversation_id or conversation_id not in active_conversations:
        return jsonify({'error': 'Session expired or invalid. Please refresh the page.'}), 400
    
    orchestrator = active_conversations[conversation_id]['orchestrator']
    
    state = ConversationState(conversation_id=conversation_id)
    orchestrator = OrchestratorAgent(orchestrator.llm, state=state)
    
    active_conversations[conversation_id] = {
        'state': state,
        'orchestrator': orchestrator,
        'messages': [{
            'role': 'assistant',
            'content': "Starting a new conversation. What cloud provider would you like to use? (AWS or Azure)"
        }]
    }
    
    return jsonify({
        'message': "Starting a new conversation. What cloud provider would you like to use? (AWS or Azure)",
        'state': {
            'current_step': state.state['current_step'],
            'cloud_provider': state.state['cloud_provider'],
            'resource_type': state.state['resource_type'],
            'collected_data': state.state['collected_data'],
            'completed_steps': state.state['completed_steps']
        },
        'messages': active_conversations[conversation_id]['messages']
    })

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    app.run(debug=debug, port=port)
