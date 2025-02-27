from flask import Flask, render_template, request, jsonify, session
from flask_socketio import SocketIO, emit
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
socketio = SocketIO(app, cors_allowed_origins="*")

active_conversations = {}

@app.route('/')
def index():
    """Render the main UI page"""
    if 'conversation_id' not in session:
        session['conversation_id'] = str(uuid.uuid4())
    
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    conversation_id = session.get('conversation_id')
    if not conversation_id:
        conversation_id = str(uuid.uuid4())
        session['conversation_id'] = conversation_id
    
    if conversation_id not in active_conversations:
        try:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                emit('error', {'message': 'OpenAI API key not set. Please check your .env file.'})
                return
            
            llm = OpenAI(api_key=api_key)
            
            state = ConversationState(conversation_id=conversation_id)
            
            orchestrator = OrchestratorAgent(llm, state=state)
            
            active_conversations[conversation_id] = {
                'state': state,
                'orchestrator': orchestrator
            }
            
            emit('message', {
                'role': 'assistant',
                'content': "Welcome to the Crossplane YAML Manifest Generator! I'll help you create infrastructure as code using Crossplane. What cloud provider would you like to use? (AWS or Azure)"
            })
            
            emit('state_update', {
                'current_step': state.state['current_step'],
                'cloud_provider': state.state['cloud_provider'],
                'resource_type': state.state['resource_type'],
                'collected_data': state.state['collected_data'],
                'completed_steps': state.state['completed_steps']
            })
            
        except Exception as e:
            emit('error', {'message': f'Error initializing chatbot: {str(e)}'})
    else:
        state = active_conversations[conversation_id]['state']
        
        emit('state_update', {
            'current_step': state.state['current_step'],
            'cloud_provider': state.state['cloud_provider'],
            'resource_type': state.state['resource_type'],
            'collected_data': state.state['collected_data'],
            'completed_steps': state.state['completed_steps']
        })

@socketio.on('message')
def handle_message(data):
    """Handle incoming message from client"""
    user_input = data.get('message', '').strip()
    if not user_input:
        return
    
    conversation_id = session.get('conversation_id')
    if not conversation_id or conversation_id not in active_conversations:
        emit('error', {'message': 'Session expired or invalid. Please refresh the page.'})
        return
    
    orchestrator = active_conversations[conversation_id]['orchestrator']
    state = active_conversations[conversation_id]['state']
    state.add_message('user', user_input)
    
    emit('message', {
        'role': 'user',
        'content': user_input
    })
    
    if user_input.lower() == 'restart':
        state = ConversationState(conversation_id=conversation_id)
        orchestrator = OrchestratorAgent(orchestrator.llm, state=state)
        
        active_conversations[conversation_id] = {
            'state': state,
            'orchestrator': orchestrator
        }
        
        emit('message', {
            'role': 'assistant',
            'content': "Starting a new conversation. What cloud provider would you like to use? (AWS or Azure)"
        })
        
        emit('state_update', {
            'current_step': state.state['current_step'],
            'cloud_provider': state.state['cloud_provider'],
            'resource_type': state.state['resource_type'],
            'collected_data': state.state['collected_data'],
            'completed_steps': state.state['completed_steps']
        })
        return
    
    try:
        response = orchestrator.process_message(user_input)
        
        if isinstance(response, dict) and response.get('error'):
            emit('message', {
                'role': 'assistant',
                'content': f"Error: {response.get('message', 'An error occurred')}"
            })
            state.update(error_count=state.state['error_count'] + 1)
        else:
            content = response
            if isinstance(response, dict) and 'result' in response:
                content = response['result']
            
            if isinstance(response, dict) and 'manifest' in response:
                manifest = response['manifest']
                message = response.get('message', "Here's your Crossplane manifest:")
                content = f"{message}\n\n```yaml\n{manifest}\n```"
                
                emit('yaml_manifest', {
                    'content': manifest
                })
                
                state.update(current_step='manifest_complete')
                state.mark_step_complete('generate_manifest')
            
            emit('message', {
                'role': 'assistant',
                'content': content
            })
            state.add_message('assistant', content)
            
            if '```yaml' in content and '```' in content.split('```yaml', 1)[1]:
                yaml_content = content.split('```yaml', 1)[1].split('```', 1)[0].strip()
                emit('yaml_manifest', {
                    'content': yaml_content
                })
        
        state.save()
        
        current_state = orchestrator.state.state
        
        emit('state_update', {
            'current_step': current_state['current_step'],
            'cloud_provider': current_state['cloud_provider'],
            'resource_type': current_state['resource_type'],
            'collected_data': current_state['collected_data'],
            'completed_steps': current_state['completed_steps']
        })
        
    except CrossplaneError as e:
        emit('message', {
            'role': 'assistant',
            'content': f"Error: {e.user_message}"
        })
        state.update(error_count=state.state['error_count'] + 1)
        state.save()
        
    except Exception as e:
        emit('message', {
            'role': 'assistant',
            'content': f"An unexpected error occurred: {str(e)}. Please try again or restart the application."
        })
        state.update(error_count=state.state['error_count'] + 1)
        state.save()

@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    conversation_id = session.get('conversation_id')
    if conversation_id and conversation_id in active_conversations:
        state = active_conversations[conversation_id]['state']
        state.save()

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')
    socketio.run(app, debug=debug, port=port)
