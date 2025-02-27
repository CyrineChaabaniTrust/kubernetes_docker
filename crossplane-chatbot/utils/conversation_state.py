import logging
import json
import os
import time
from datetime import datetime

logger = logging.getLogger(__name__)

class ConversationState:
    """Manages the state of a conversation with the chatbot"""
    
    def __init__(self, conversation_id=None, save_dir='conversation_history'):
        """Initialize a new conversation state manager"""
        self.conversation_id = conversation_id or self._generate_id()
        self.save_dir = save_dir
        self.state = {
            "conversation_id": self.conversation_id,
            "start_time": datetime.now().isoformat(),
            "current_step": "initial",
            "cloud_provider": None,
            "resource_type": None,
            "collected_data": {},
            "history": [],
            "error_count": 0,
            "completed_steps": []
        }
        
        os.makedirs(save_dir, exist_ok=True)
        
        logger.info(f"Started new conversation with ID: {self.conversation_id}")
    
    def _generate_id(self):
        """Generate a unique conversation ID"""
        import uuid
        return str(uuid.uuid4())
    
    def update(self, **kwargs):
        """Update the conversation state"""
        for key, value in kwargs.items():
            if key in self.state:
                self.state[key] = value
                logger.debug(f"Updated {key} to {value}")
            else:
                logger.warning(f"Attempted to update unknown state key: {key}")
        return self
    
    def add_message(self, role, message):
        """Add a message to the conversation history"""
        self.state["history"].append({
            "role": role,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
        return self
    
    def add_collected_data(self, key, value):
        """Add a piece of collected data"""
        self.state["collected_data"][key] = value
        logger.debug(f"Collected data: {key}={value}")
        return self
    
    def mark_step_complete(self, step_name):
        """Mark a step as complete"""
        if step_name not in self.state["completed_steps"]:
            self.state["completed_steps"].append(step_name)
            logger.info(f"Completed step: {step_name}")
        return self
    
    def save(self):
        """Save the current state to disk"""
        file_path = os.path.join(self.save_dir, f"{self.conversation_id}.json")
        try:
            with open(file_path, 'w') as f:
                json.dump(self.state, f, indent=2)
            logger.debug(f"Saved conversation state to {file_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to save conversation state: {str(e)}")
            return False
    
    @classmethod
    def load(cls, conversation_id, save_dir='conversation_history'):
        """Load a conversation state from disk"""
        file_path = os.path.join(save_dir, f"{conversation_id}.json")
        try:
            with open(file_path, 'r') as f:
                state_data = json.load(f)
            
            instance = cls(conversation_id=conversation_id, save_dir=save_dir)
            instance.state = state_data
            logger.info(f"Loaded conversation state for ID: {conversation_id}")
            return instance
        except FileNotFoundError:
            logger.warning(f"No saved state found for conversation ID: {conversation_id}")
            return None
        except Exception as e:
            logger.error(f"Failed to load conversation state: {str(e)}")
            return None
    
    def can_undo(self):
        """Check if the current state can be undone"""
        return len(self.state["completed_steps"]) > 0
    
    def undo_last_step(self):
        """Undo the last completed step"""
        if not self.can_undo():
            logger.warning("Cannot undo - no completed steps")
            return False
        
        last_step = self.state["completed_steps"].pop()
        logger.info(f"Undoing step: {last_step}")
        
        if last_step == "collect_resource_data":
            if self.state["collected_data"]:
                keys = list(self.state["collected_data"].keys())
                if keys:
                    last_key = keys[-1]
                    del self.state["collected_data"][last_key]
                    logger.info(f"Removed last collected data field: {last_key}")
        
        previous_steps = {
            "generate_manifest": "collect_resource_data",
            "collect_resource_data": "select_resource",
            "select_resource": "select_provider",
            "select_provider": "initial"
        }
        
        self.state["current_step"] = previous_steps.get(self.state["current_step"], "initial")
        return True 