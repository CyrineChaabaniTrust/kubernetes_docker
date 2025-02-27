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

from .s3_agent import AWSS3Agent
from .rds_agent import AWSRDSAgent
from .eks_agent import AWSEKSAgent
from .ec2_agent import AWSEC2Agent
from .iam_agent import AWSIAMAgent

logger = logging.getLogger(__name__)

class UserInputSchema(BaseModel):
    user_input: str = Field(..., description="The input from the user")

class ResourceDataSchema(BaseModel):
    user_input: str = Field(..., description="The input from the user")
    resource_type: Optional[str] = Field(None, description="The type of resource to collect data for")

class EmptySchema(BaseModel):
    pass

class AWSAgent:
    """Agent for handling AWS specific interactions"""
    
    def __init__(self, llm, state=None):
        self.llm = llm
        self.state = state
        self.current_resource = None
        self.collected_data = {}
        self.resource_agents = {
            's3': AWSS3Agent(llm),
            'rds': AWSRDSAgent(llm),
            'eks': AWSEKSAgent(llm),
            'ec2': AWSEC2Agent(llm),
            'iam': AWSIAMAgent(llm)
        }
        
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        
        self.resource_type_prompt = PromptTemplate(
            input_variables=["user_input", "previous_attempts"],
            template="""
            You are an expert in AWS resources for Crossplane. 
            Determine what type of AWS resource the user wants to create based on their input.
            
            Available AWS resource types:
            - s3: S3 Buckets for storage
            - rds: RDS Database instances
            - eks: EKS Kubernetes clusters
            - ec2: EC2 Virtual machines
            - iam: IAM roles or policies
            
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
        
        self.unknown_resource_prompt = PromptTemplate(
            input_variables=["user_input"],
            template="""
            The user has indicated they want to create an AWS resource, but I couldn't determine which specific resource type.
            
            User input: {user_input}
            
            Create a helpful response that:
            1. Explains that I couldn't determine the resource type
            2. Lists the available resource types I can help with (S3, RDS, EKS, EC2, IAM)
            3. Asks them to clarify which resource they want to create
            4. Is friendly and helpful
            
            Keep your response concise (2-3 sentences).
            """
        )
        
        tools = [
            StructuredTool.from_function(
                name="determine_resource_type",
                description="Determines which AWS resource type the user wants to create",
                func=self._determine_resource_type_tool,
                args_schema=UserInputSchema,
                return_direct=False
            ),
            StructuredTool.from_function(
                name="start_resource_data_collection",
                description="Starts collecting data for a specific resource type",
                func=self._start_resource_data_collection_tool,
                args_schema=ResourceDataSchema,
                return_direct=False
            ),
            StructuredTool.from_function(
                name="collect_resource_data",
                description="Collects required data for the resource being created",
                func=self._collect_resource_data_tool,
                args_schema=UserInputSchema,
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
            """You are an AWS infrastructure specialist helping create Crossplane manifests.
            
            Your role is to identify which AWS resource the user wants to create and collect the necessary information.
            
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
    
    def _determine_resource_type_tool(self, params: UserInputSchema) -> dict:
        """Tool to determine which AWS resource type the user wants to create"""
        user_input = params.user_input
        previous_attempts = self.state.state.get("previous_attempts", []) if self.state else []
        
        try:
            resource_chain = LLMChain(llm=self.llm, prompt=self.resource_type_prompt)
            response = resource_chain.invoke({
                "user_input": user_input,
                "previous_attempts": json.dumps(previous_attempts)
            })
            
            match = re.search(r'\{.*\}', response["text"], re.DOTALL)
            if match:
                resource_json = match.group(0)
                try:
                    resource_data = json.loads(resource_json)
                    resource_type = resource_data.get("resource_type", "unknown").lower()
                except json.JSONDecodeError:
                    logger.warning(f"Could not parse resource type JSON: {resource_json}")
                    resource_type = "unknown"
            else:
                resource_type = response["text"].strip().lower()
                if resource_type not in ["s3", "rds", "eks", "ec2", "iam", "unknown"]:
                    resource_type = "unknown"
            
            if resource_type == "unknown":
                unknown_chain = LLMChain(llm=self.llm, prompt=self.unknown_resource_prompt)
                response = unknown_chain.invoke({"user_input": user_input})
                return {
                    "resource_type": "unknown",
                    "message": response["text"].strip()
                }
            
            if resource_type in ["s3", "rds", "eks", "ec2", "iam"]:
                self.current_resource = resource_type
                
                if self.state:
                    self.state.update(
                        current_step="collect_resource_data",
                        resource_type=resource_type
                    )
                    self.state.mark_step_complete("select_resource")
                
                return {
                    "resource_type": resource_type,
                    "message": f"Great! Let's create an AWS {resource_type.upper()} resource. I'll collect the necessary information."
                }
            
            return {
                "resource_type": "unknown",
                "message": "I'm not sure which AWS resource you want to create. Could you please specify if you want to create an S3 bucket, RDS database, EKS cluster, EC2 instance, or IAM role?"
            }
            
        except Exception as e:
            logger.error(f"Error determining resource type: {str(e)}")
            return {
                "error": str(e),
                "message": "I encountered an error trying to determine which AWS resource you want to create. Could you please clearly specify one of: S3, RDS, EKS, EC2, or IAM?"
            }
    
    def _start_resource_data_collection_tool(self, params: ResourceDataSchema) -> dict:
        """Tool to start collecting data for a specific resource type"""
        resource_type = params.resource_type
        if not resource_type:
            result = self._determine_resource_type_tool(UserInputSchema(user_input=params.user_input))
            resource_type = result.get("resource_type")
            
            if resource_type == "unknown":
                return result
        
        if resource_type not in self.resource_agents:
            return {
                "error": "Invalid resource type",
                "message": "I don't support that AWS resource type. I can help with S3, RDS, EKS, EC2, or IAM."
            }
        
        self.current_resource = resource_type
        if self.state:
            self.state.update(
                current_step="collect_resource_data",
                resource_type=resource_type
            )
            self.state.mark_step_complete("select_resource")
        
        resource_agent = self.resource_agents.get(resource_type)
        first_question = resource_agent.get_first_question() if resource_agent else f"Let's collect information for your {resource_type}. What would you like to name it?"
        
        return {
            "resource_type": resource_type,
            "message": first_question
        }
        
    def _collect_resource_data_tool(self, params: UserInputSchema) -> dict:
        """Tool to collect data for the resource being created"""
        user_input = params.user_input
        
        if not self.current_resource:
            result = self._determine_resource_type_tool(params)
            resource_type = result.get("resource_type")
            
            if resource_type == "unknown":
                return result
                
            return self._start_resource_data_collection_tool(ResourceDataSchema(
                user_input=user_input,
                resource_type=resource_type
            ))
        
        resource_agent = self.resource_agents.get(self.current_resource)
        if not resource_agent:
            return {
                "error": "Invalid resource",
                "message": f"I'm having trouble with the {self.current_resource} agent. Let's try a different resource type."
            }
        
        result = resource_agent.process_input(user_input)
        
        if result.get("field_name") and result.get("field_value") is not None:
            self.collected_data[result["field_name"]] = result["field_value"]
            
            if self.state:
                collected_data = self.state.state.get("collected_data", {})
                collected_data[result["field_name"]] = result["field_value"]
                self.state.update(collected_data=collected_data)
        
        if result.get("data_collection_complete"):
            if self.state:
                self.state.update(current_step="generate_manifest")
                self.state.mark_step_complete("collect_resource_data")
            
            return {
                "data_collection_complete": True,
                "message": f"Great! I have all the information I need for your AWS {self.current_resource.upper()} resource. I can generate the Crossplane manifest now."
            }
        
        return {
            "data_collection_complete": False,
            "message": result.get("next_question", "Could you provide more information?")
        }
    
    def _generate_manifest_tool(self, params: EmptySchema) -> dict:
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
                "message": f"Here's your Crossplane manifest for AWS {self.current_resource}. Would you like to create another resource?"
            }
        except Exception as e:
            logger.error(f"Error generating manifest: {str(e)}")
            return {
                "error": str(e),
                "message": f"I encountered an error generating the manifest: {str(e)}. Please check the data you provided."
            }
            
    def _get_current_state_tool(self, params: EmptySchema) -> dict:
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