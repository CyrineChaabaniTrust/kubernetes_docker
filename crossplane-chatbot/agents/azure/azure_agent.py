from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.memory import ConversationBufferMemory
from langchain.tools import StructuredTool
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.schema import AgentAction, AgentFinish, HumanMessage, AIMessage
import logging
import json
import re
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from .resource_group_agent import AzureResourceGroupAgent
from .aks_agent import AzureAKSAgent
from .storage_agent import AzureStorageAgent
from .sql_agent import AzureSQLAgent
from .app_service_agent import AzureAppServiceAgent

logger = logging.getLogger(__name__)

class UserInputSchema(BaseModel):
    user_input: str = Field(..., description="The input from the user")

class ResourceDataSchema(BaseModel):
    user_input: str = Field(..., description="The input from the user")
    resource_type: Optional[str] = Field(None, description="The type of resource to collect data for")

class EmptySchema(BaseModel):
    pass

class AzureAgent:
    """Agent for handling Azure specific interactions"""
    
    def __init__(self, llm, state=None):
        self.llm = llm
        self.state = state
        self.current_resource = None
        self.collected_data = {}
        self.resource_agents = {
            'resource_group': AzureResourceGroupAgent(llm),
            'aks': AzureAKSAgent(llm),
            'storage': AzureStorageAgent(llm),
            'sql': AzureSQLAgent(llm),
            'app_service': AzureAppServiceAgent(llm),
        }
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self.resource_type_prompt = PromptTemplate(
            input_variables=["user_input", "previous_attempts"],
            template="""
            You are an expert in Azure resources for Crossplane. 
            Determine what type of Azure resource the user wants to create based on their input.
            
            Available Azure resource types:
            - resource_group: Azure Resource Groups for organizing resources
            - aks: Azure Kubernetes Service clusters
            - storage: Azure Storage Accounts
            - sql: Azure SQL Databases
            - app_service: Azure App Services for web applications
            
            User input: {user_input}
            
            Previous classification attempts: {previous_attempts}
            
            First, analyze the user input to determine which resource type they are referring to.
            Then respond with a JSON object like this:
            {{
                "resource_type": "the_resource_type_code"
            }}
            
            If you can't determine the resource type, respond with:
            {{
                "resource_type": "unknown"
            }}
            
            Return ONLY the JSON object and nothing else.
            """
        )
        
        tools = [
            StructuredTool.from_function(
                name="determine_resource_type",
                description="Determines which Azure resource type the user wants to create",
                func=self._determine_resource_type_tool,
                args_schema=UserInputSchema,
                return_direct=False
            ),
            StructuredTool.from_function(
                name="collect_resource_data",
                description="Collects the required data for the resource being created",
                func=self._collect_resource_data_tool,
                args_schema=ResourceDataSchema,
                return_direct=False
            ),
            StructuredTool.from_function(
                name="generate_manifest",
                description="Generates the Crossplane manifest for the resource being created",
                func=self._generate_manifest_tool,
                args_schema=EmptySchema,
                return_direct=False
            ),
            StructuredTool.from_function(
                name="get_current_state",
                description="Gets the current state of the resource creation process",
                func=self._get_current_state_tool,
                args_schema=EmptySchema,
                return_direct=False
            )
        ]
        
        tool_names = [tool.name for tool in tools]
        
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            """You are an Azure infrastructure specialist helping create Crossplane manifests.
            
            Your role is to identify which Azure resource the user wants to create and collect the necessary information.
            
            You have access to the following tools: {tools}
            
            The available tools are: {tool_names}
            
            Always use the most appropriate tool for the job.
            """
        )
        
        human_message_prompt = HumanMessagePromptTemplate.from_template("{input}")
        
        chat_prompt = ChatPromptTemplate.from_messages([
            system_message_prompt,
            MessagesPlaceholder(variable_name="chat_history"),
            human_message_prompt,
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        self.agent_executor = AgentExecutor(
            agent=create_structured_chat_agent(
                llm=self.llm,
                tools=tools,
                prompt=chat_prompt
            ),
            tools=tools,
            memory=self.memory,
            verbose=True,
            max_iterations=5,
            max_execution_time=120,
            handle_parsing_errors=True
        )
    
    def determine_resource_type(self, user_input: str) -> Dict:
        """Determine which resource type the user wants to create"""
        return self._determine_resource_type_tool(UserInputSchema(user_input=user_input))
    
    def _determine_resource_type_tool(self, params: UserInputSchema) -> Dict:
        """Tool to determine which Azure resource type the user wants to create"""
        user_input = params.user_input
        
        try:
            response = self.llm.invoke(
                self.resource_type_prompt.format(
                    user_input=user_input,
                    previous_attempts=""
                )
            )
            
            try:
                result = json.loads(response)
                resource_type = result.get("resource_type", "unknown").lower().strip()
            except json.JSONDecodeError:
                resource_type = "unknown"
                if "resource_group" in response.lower():
                    resource_type = "resource_group"
                elif "aks" in response.lower():
                    resource_type = "aks"
                elif "storage" in response.lower():
                    resource_type = "storage"
                elif "sql" in response.lower():
                    resource_type = "sql"
                elif "app_service" in response.lower():
                    resource_type = "app_service"
            
            valid_resources = {'resource_group', 'aks', 'storage', 'sql', 'app_service'}
            if resource_type not in valid_resources:
                resource_type_map = {
                    'resource_group': ['resource group', 'resource-group', 'rg'],
                    'aks': ['aks', 'kubernetes', 'cluster'],
                    'storage': ['storage', 'blob', 'file share', 'storage account'],
                    'sql': ['sql', 'database', 'db'],
                    'app_service': ['app service', 'web app', 'webapp', 'application']
                }
                
                for type_name, keywords in resource_type_map.items():
                    if any(keyword in user_input.lower() for keyword in keywords):
                        resource_type = type_name
                        break
                else:
                    resource_type = "unknown"
            
            if resource_type != "unknown":
                self.current_resource = resource_type
                
                if self.state:
                    self.state.update(
                        current_step="collect_resource_data",
                        resource_type=resource_type
                    )
                    self.state.mark_step_complete("select_resource")
                
                resource_agent = self.resource_agents.get(resource_type)
                if resource_agent:
                    first_question = resource_agent.get_first_question()
                else:
                    first_question = f"Let's collect information for your {resource_type}. What would you like to name it?"
                
                return {
                    "resource_type": resource_type,
                    "message": first_question
                }
            else:
                available_resources = "Resource Groups, AKS clusters, Storage Accounts, SQL Databases, and App Services"
                
                return {
                    "resource_type": "unknown",
                    "message": f"I'm not sure which Azure resource you want to create. I can help with {available_resources}. Could you please specify which one you need?"
                }
        except Exception as e:
            logger.error(f"Error determining resource type: {str(e)}")
            return {
                "error": str(e),
                "message": "I'm having trouble understanding which Azure resource you want to create. Could you please clearly specify one of: Resource Group, AKS, Storage, SQL, or App Service?"
            }
    
    def _collect_resource_data_tool(self, params: ResourceDataSchema) -> Dict:
        """Tool to collect data for the resource being created"""
        user_input = params.user_input
        resource_type = params.resource_type or self.current_resource
        
        if not resource_type:
            return {
                "error": "No resource type",
                "message": "I'm not sure which Azure resource you want to create. Could you please specify one of: Resource Group, AKS, Storage, SQL, or App Service?"
            }
        
        try:
            resource_agent = self.resource_agents.get(resource_type)
            if not resource_agent:
                return {
                    "error": "Invalid resource",
                    "message": f"I'm having trouble with the {resource_type} agent. Let's try a different resource type."
                }
            
            result = resource_agent.process_input(user_input)
            
            if result.get("field_name") and result.get("field_value"):
                field_name = result["field_name"]
                field_value = result["field_value"]
                
                self.collected_data[field_name] = field_value
                
                if self.state:
                    collected_data = self.state.state.get("collected_data", {})
                    collected_data[field_name] = field_value
                    self.state.update(collected_data=collected_data)
            
            if result.get("data_collection_complete"):
                if self.state:
                    self.state.update(current_step="generate_manifest")
                    self.state.mark_step_complete("collect_resource_data")
                
                return {
                    "data_collection_complete": True,
                    "message": f"Great! I have all the information I need for your Azure {resource_type.upper()} resource. I can generate the Crossplane manifest now."
                }
            
            return {
                "data_collection_complete": False,
                "message": result.get("next_question", "Could you provide more information?")
            }
        except Exception as e:
            logger.error(f"Error collecting resource data: {str(e)}")
            return {
                "error": str(e),
                "message": f"I encountered an error collecting resource data: {str(e)}. Let's try again."
            }
    
    def _generate_manifest_tool(self, params: EmptySchema) -> Dict:
        """Tool to generate a Crossplane manifest for the resource"""
        if not self.current_resource or not self.collected_data:
            return {
                "error": "Missing data",
                "message": "I don't have enough information to generate a manifest. Let's collect the required data first."
            }
        
        try:
            resource_agent = self.resource_agents.get(self.current_resource)
            if not resource_agent:
                return {
                    "error": "Invalid resource",
                    "message": f"I'm having trouble with the {self.current_resource} agent. Let's try a different resource type."
                }
            
            manifest = resource_agent.generate_manifest(self.collected_data)
            
            if self.state:
                self.state.update(current_step="manifest_complete")
                self.state.mark_step_complete("generate_manifest")
            
            return {
                "manifest_complete": True,
                "manifest": manifest,
                "message": f"Here's your Crossplane manifest for Azure {self.current_resource}. Would you like to create another resource?"
            }
        except Exception as e:
            logger.error(f"Error generating manifest: {str(e)}")
            return {
                "error": str(e),
                "message": f"I encountered an error generating the manifest: {str(e)}. Please check the data you provided."
            }
            
    def _get_current_state_tool(self, params: EmptySchema) -> Dict:
        """Tool to get the current state of the resource creation process"""
        if not self.state:
            return {
                "message": "No state information available."
            }
            
        current_step = self.state.state.get("current_step", "initial")
        resource_type = self.state.state.get("resource_type")
        collected_data = self.state.state.get("collected_data", {})
        
        return {
            "current_step": current_step,
            "resource_type": resource_type,
            "collected_data": collected_data,
            "message": f"Current step: {current_step}, Resource type: {resource_type}, Collected data fields: {list(collected_data.keys()) if collected_data else 'None'}"
        }
    
    def process_message(self, message: str) -> Dict:
        """Process a user message and return a response"""
        try:
            response = self.agent_executor.invoke({"input": message})
            return response
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return {"output": f"I encountered an error: {str(e)}. Could we try again?"} 