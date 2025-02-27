from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from typing import Dict, List, Optional, Any
import logging
import json
import re

logger = logging.getLogger(__name__)

class AzureResourceAgent:
    """Base class for Azure resource agents"""
    def __init__(self, llm):
        self.llm = llm
        self.required_fields = []
        self.optional_fields = []
        self.current_field_index = 0
        self.in_optional_phase = False
        self.current_optional_index = 0
        
        # Add response generation prompt
        self.response_prompt = PromptTemplate(
            input_variables=["resource_type", "field_name", "field_description", "collected_data", "is_optional"],
            template="""
            You are a helpful assistant guiding a user to create a Crossplane manifest for an Azure {resource_type} resource.
            
            Currently collected information:
            {collected_data}
            
            You need to ask the user for the {field_name} ({field_description}).
            
            This field is {"optional" if is_optional else "required"}.
            
            Generate a natural, conversational question asking for this information.
            If it's optional, mention they can type 'skip' to leave it blank.
            Be friendly but professional. Keep your response concise (1-2 sentences).
            """
        )
        
        # Add completion message prompt
        self.completion_prompt = PromptTemplate(
            input_variables=["resource_type", "collected_data"],
            template="""
            You are a helpful assistant guiding a user to create a Crossplane manifest for an Azure {resource_type} resource.
            
            The user has provided all the necessary information:
            {collected_data}
            
            Generate a brief message (1-2 sentences) confirming that you've collected all the needed information 
            and are ready to generate the Crossplane manifest for this {resource_type} resource.
            Be friendly but professional.
            """
        )
    
    def get_first_question(self) -> str:
        """Get the first question to ask the user"""
        if not self.required_fields:
            return "What would you like to name this resource?"
        
        field = self.required_fields[0]
        return self._generate_question(field["name"], field["description"], {}, False)
    
    def process_input(self, user_input: str) -> Dict:
        """Process user input and determine the next question to ask"""
        # Skip if user explicitly says to
        skip = user_input.strip().lower() == "skip"
        
        if not self.in_optional_phase:
            # Processing required fields
            if self.current_field_index < len(self.required_fields):
                field = self.required_fields[self.current_field_index]
                field_name = field["name"]
                
                # Cannot skip required fields
                if skip:
                    return {
                        "field_name": None,
                        "field_value": None,
                        "next_question": f"Sorry, {field_name} is a required field. " + field["question"],
                        "data_collection_complete": False
                    }
                
                self.current_field_index += 1
                
                # If we have more required fields, ask the next one
                if self.current_field_index < len(self.required_fields):
                    next_field = self.required_fields[self.current_field_index]
                    collected_data = {field_name: user_input}
                    next_question = self._generate_question(next_field["name"], next_field["description"], collected_data, False)
                    
                    return {
                        "field_name": field_name,
                        "field_value": user_input,
                        "next_question": next_question,
                        "data_collection_complete": False
                    }
                else:
                    # Move to optional fields
                    self.in_optional_phase = True
                    
                    # If we have optional fields, ask the first one
                    if self.optional_fields:
                        next_field = self.optional_fields[0]
                        collected_data = {field_name: user_input}
                        next_question = self._generate_question(next_field["name"], next_field["description"], collected_data, True)
                        
                        return {
                            "field_name": field_name,
                            "field_value": user_input,
                            "next_question": next_question,
                            "data_collection_complete": False
                        }
                    else:
                        # No optional fields, we're done
                        collected_data = {field_name: user_input}
                        next_question = self._generate_completion_message(collected_data)
                        
                        return {
                            "field_name": field_name,
                            "field_value": user_input,
                            "next_question": next_question,
                            "data_collection_complete": True
                        }
            else:
                # Should not reach here but just in case
                return {
                    "field_name": None,
                    "field_value": None,
                    "next_question": "Let's collect information about this resource. What would you like to name it?",
                    "data_collection_complete": False
                }
        else:
            # Processing optional fields
            if self.current_optional_index < len(self.optional_fields):
                field = self.optional_fields[self.current_optional_index]
                field_name = field["name"]
                self.current_optional_index += 1
                
                # Handle skip for optional fields
                if skip:
                    field_value = None
                else:
                    field_value = user_input
                
                collected_data = {
                    field_name: field_value
                }
                
                # If we have more optional fields, ask the next one
                if self.current_optional_index < len(self.optional_fields):
                    next_field = self.optional_fields[self.current_optional_index]
                    next_question = self._generate_question(next_field["name"], next_field["description"], collected_data, True)
                else:
                    # No more fields to collect
                    next_question = self._generate_completion_message(collected_data)
                    return {
                        "field_name": field_name,
                        "field_value": field_value,
                        "next_question": next_question,
                        "data_collection_complete": True
                    }
                
                return {
                    "field_name": field_name,
                    "field_value": field_value,
                    "next_question": next_question,
                    "data_collection_complete": False
                }
        
        # If we get here, we've collected all the data
        return {
            "field_name": None,
            "field_value": None,
            "next_question": "I have all the information I need. I can generate the manifest now.",
            "data_collection_complete": True
        }
    
    def _generate_question(self, field_name: str, field_description: str, collected_data: Dict, is_optional: bool) -> str:
        """Generate a question for a specific field"""
        try:
            response = self.llm.invoke(
                self.response_prompt.format(
                    resource_type=self._get_resource_type(),
                    field_name=field_name,
                    field_description=field_description,
                    collected_data=json.dumps(collected_data, indent=2),
                    is_optional=is_optional
                )
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating question: {str(e)}")
            field_info = next((f for f in (self.required_fields + self.optional_fields) if f["name"] == field_name), None)
            if field_info and "question" in field_info:
                return field_info["question"]
            else:
                return f"What would you like to set for {field_name} ({field_description})?"
    
    def _generate_completion_message(self, collected_data: Dict) -> str:
        """Generate a completion message"""
        try:
            response = self.llm.invoke(
                self.completion_prompt.format(
                    resource_type=self._get_resource_type(),
                    collected_data=json.dumps(collected_data, indent=2)
                )
            )
            return response.strip()
        except Exception as e:
            logger.error(f"Error generating completion message: {str(e)}")
            return f"Great! I have all the information I need for your {self._get_resource_type()} resource. I'll generate the Crossplane manifest now."
    
    def _get_resource_type(self) -> str:
        """Get the resource type name"""
        return self.__class__.__name__.replace("Azure", "").replace("Agent", "")
    
    def generate_manifest(self, collected_data: Dict) -> str:
        """Generate a Crossplane manifest for the resource"""
        # This should be implemented by subclasses
        raise NotImplementedError("Subclasses must implement generate_manifest") 