from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate, ChatPromptTemplate, MessagesPlaceholder, SystemMessagePromptTemplate, HumanMessagePromptTemplate
from langchain.tools import Tool, StructuredTool
from langchain.agents import AgentExecutor, create_structured_chat_agent
from langchain.schema import AgentAction, AgentFinish, HumanMessage, AIMessage, SystemMessage
from agents.aws.aws_agent import AWSAgent
from agents.azure.azure_agent import AzureAgent
from generators.manifest_generator import ManifestGenerator
from utils.conversation_state import ConversationState
from utils.error_handler import handle_errors, ResourceNotSupportedError
import logging
import json
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser

logger = logging.getLogger(__name__)

class UserInputSchema(BaseModel):
    user_input: str = Field(..., description="The input from the user")

class EmptySchema(BaseModel):
    pass

class OrchestratorAgent:
    def __init__(self, llm, state=None):
        self.llm = llm
        self.state = state or ConversationState()
        self.memory = ConversationBufferMemory(
            memory_key="chat_history",
            return_messages=True
        )
        self.cloud_agents = {
            'aws': AWSAgent(llm, self.state),
            'azure': AzureAgent(llm, self.state)
        }
        self.manifest_generator = ManifestGenerator()
        
        self.intent_detection_prompt = PromptTemplate(
            input_variables=["user_input", "current_step"],
            template="""
            Analyze the user's message and determine if they are:
            1. Asking a general question about cloud resources, Crossplane, or infrastructure
            2. Providing information for the current step ({current_step})
            
            User message: "{user_input}"
            
            Return only one of these values:
            - "question" if they're asking a general question
            - "input" if they're providing information for the current step
            """)
        
        self.qa_prompt = PromptTemplate(
            input_variables=["question"],
            template="""
            You are a helpful assistant with expertise in cloud infrastructure, Kubernetes, and Crossplane.
            Answer the following question clearly and concisely:
            
            {question}
            
            Provide a helpful, informative answer in 2-3 sentences. After answering, remind the user 
            we can continue with their resource creation process.
            """)
        
        tools = [
            StructuredTool.from_function(
                name="determine_cloud_provider",
                description="Determines which cloud provider (AWS or Azure) the user wants to use",
                func=self._determine_cloud_provider_tool,
                args_schema=UserInputSchema,
                return_direct=False
            ),
            StructuredTool.from_function(
                name="get_current_state",
                description="Gets the current state of the conversation workflow",
                func=self._get_current_state_tool,
                args_schema=EmptySchema,
                return_direct=False
            ),
            StructuredTool.from_function(
                name="reset_conversation",
                description="Resets the conversation to start over",
                func=self._reset_conversation_tool,
                args_schema=EmptySchema,
                return_direct=False
            )
        ]
        
        tool_names = [tool.name for tool in tools]
        
        system_message_prompt = SystemMessagePromptTemplate.from_template(
            """You are a Crossplane specialist helping users create infrastructure manifests for cloud providers.
            
            Your main role is to identify which cloud provider the user wants to use (AWS or Azure).
            Once the cloud provider is determined, you'll delegate to the appropriate specialist.
            
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
        
        def create_structured_chat_agent_updated(llm, tools, prompt):
            tool_descriptions = []
            tool_names = [tool.name for tool in tools]
            
            for tool in tools:
                if hasattr(tool, "args_schema"):
                    schema = tool.args_schema.schema()
                    parameters = {
                        "type": "object",
                        "properties": schema.get("properties", {}),
                        "required": schema.get("required", []),
                        "additionalProperties": False
                    }
                else:
                    parameters = {
                        "type": "object", 
                        "properties": {},
                        "additionalProperties": False
                    }
                
                function_def = {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": parameters
                }
                
                tool_descriptions.append(function_def)
            
            print(f"Tool descriptions: {json.dumps(tool_descriptions, indent=2)}")
            
            tool_strings = []
            for tool in tools:
                tool_strings.append(f"{tool.name}: {tool.description}")
            tools_string = "\n".join(tool_strings)
            
            agent = (
                {
                    "input": lambda x: x["input"],
                    "chat_history": lambda x: x.get("chat_history", []),
                    "agent_scratchpad": lambda x: format_to_openai_function_messages(x.get("intermediate_steps", [])),
                    "tools": lambda x: tools_string,
                    "tool_names": lambda x: ", ".join(tool_names)
                }
                | prompt
                | llm.bind(functions=tool_descriptions)
                | OpenAIFunctionsAgentOutputParser()
            )
            
            return agent

        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=create_structured_chat_agent_updated(
                llm=self.llm,
                tools=tools,
                prompt=chat_prompt
            ),
            tools=tools,
            memory=self.memory,
            verbose=True,
            max_iterations=3,
            handle_parsing_errors=True
        )
        
        self.cloud_prompt = PromptTemplate(
            input_variables=["user_input"],
            template="""
            Based on the user's input, determine which cloud provider they want to use.
            User input: {user_input}
            
            Reply with only one of the following options: 'aws', 'azure', or 'unknown'.
            """
        )
        self.cloud_chain = LLMChain(llm=llm, prompt=self.cloud_prompt)

    def _is_general_question(self, user_input: str) -> bool:
        logger.info(f"Checking if user input is a general question: {user_input}")
        """Determine if user input is a general question rather than providing data"""
        current_step = self.state.state.get("current_step", "initial")
        
        response = self.llm.invoke(
            self.intent_detection_prompt.format(
                user_input=user_input,
                current_step=current_step
            )
        )
        print(response)
        return response == "question"
    
    def _answer_general_question(self, question: str) -> str:
        logger.info(f"Answering general question: {question}")
        """Provide an answer to a general question about Crossplane or cloud resources"""
        response = self.llm.invoke(
            self.qa_prompt.format(question=question)
        )
        print(response)
        return response

    @handle_errors
    def process_message(self, user_input):
        logger.info(f"Processing message: {user_input}")
        """Process a message, determining cloud provider or forwarding to agent"""
        try:
            if self._is_general_question(user_input):
                logger.info("Detected general question, providing answer")
                answer = self._answer_general_question(user_input)
                
                self.memory.chat_memory.add_user_message(user_input)
                self.memory.chat_memory.add_ai_message(answer)
                
                return answer
            
            cloud_provider = self.state.state.get("cloud_provider")
            
            self.memory.chat_memory.add_user_message(user_input)
            
            if cloud_provider:
                logger.info(f"Forwarding message to {cloud_provider} agent")
                agent = self.cloud_agents.get(cloud_provider)
                if not agent:
                    return f"I'm sorry, I'm having trouble with the {cloud_provider.upper()} agent. Let's try again."
                
                response = agent.process_message(user_input)
                
                if isinstance(response, dict):
                    for key, value in response.items():
                        if isinstance(value, (HumanMessage, AIMessage, SystemMessage)):
                            response[key] = value.content
                    
                    if len(response) == 1 and "output" in response:
                        return response["output"]
                
                return response
            else:
                logger.info("Determining cloud provider")
                result = self.agent_executor.invoke({"input": user_input})
                
                if isinstance(result, dict) and "output" in result:
                    result_text = result["output"]
                    if isinstance(result_text, (HumanMessage, AIMessage, SystemMessage)):
                        result_text = result_text.content
                else:
                    result_text = str(result)
                
                return result_text
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}")
            return "I encountered an error. Let's start over. What cloud provider would you like to use? (AWS or Azure)"

    @handle_errors
    def _determine_cloud_provider_tool(self, user_input: str) -> dict:
        """Tool to determine which cloud provider the user wants to use"""
        logger.info(f"Determining cloud provider for user input: {user_input}")
        try:
            response = self.cloud_chain.invoke({"user_input": user_input})
            cloud_provider = response["text"]
            
            if cloud_provider not in ["aws", "azure"]:
                prompt = f"Based on this user message: '{user_input}', what cloud provider are they asking about? Answer with only 'aws', 'azure', or 'unknown'."
                cloud_provider = self.llm.invoke(prompt)
                print(cloud_provider)
                cloud_provider = cloud_provider.get("output", "").lower()

            if cloud_provider in ["aws", "azure"]:
                logger.info(f"Determined cloud provider: {cloud_provider}")
                self.state.update(cloud_provider=cloud_provider, current_step="select_resource")
                self.state.mark_step_complete("select_provider")
                
                provider_selected_prompt = PromptTemplate(
                    input_variables=["cloud_provider"],
                    template="""
                    You are a helpful assistant who has just identified that the user wants to use {cloud_provider}.
                    
                    Generate a friendly, conversational response that:
                    1. Confirms you'll help them with {cloud_provider} resources
                    2. Asks what type of {cloud_provider} resource they want to create
                    3. Is brief (1-2 sentences) and professional
                    """
                )
                
                response = self.llm.invoke(
                    provider_selected_prompt.format(
                        cloud_provider=cloud_provider.upper()
                    )
                )
                print(response)
                return {
                    "cloud_provider": cloud_provider,
                    "message": response or f"Great! I'll help you create a {cloud_provider.upper()} resource with Crossplane. What type of {cloud_provider.upper()} resource would you like to create?"
                }
            else:
                return {
                    "cloud_provider": "unknown",
                    "message": "I'm not sure which cloud provider you want to use. Could you please specify if you want to use AWS or Azure?"
                }
        except Exception as e:
            logger.error(f"Error determining cloud provider: {str(e)}")
            return {
                "error": str(e),
                "message": "I'm having trouble understanding which cloud provider you want to use. Could you please clearly state if you want to use AWS or Azure?"
            }
    
    def _get_current_state_tool(self) -> dict:
        """Tool to get the current state of the conversation workflow"""
        current_step = self.state.state.get("current_step", "initial")
        cloud_provider = self.state.state.get("cloud_provider")
        resource_type = self.state.state.get("resource_type")
        collected_data = self.state.state.get("collected_data", {})
        
        return {
            "current_step": current_step,
            "cloud_provider": cloud_provider,
            "resource_type": resource_type,
            "collected_data": collected_data,
            "message": f"Current step: {current_step}, Cloud provider: {cloud_provider}, Resource type: {resource_type}, Collected data fields: {list(collected_data.keys()) if collected_data else 'None'}"
        }
    
    def _reset_conversation_tool(self) -> dict:
        """Tool to reset the conversation to start over with a new resource"""
        self.state = ConversationState(conversation_id=self.state.conversation_id)
        
        for provider, agent in self.cloud_agents.items():
            agent.state = self.state
        
        return {
            "state_reset": True,
            "message": "I've reset our conversation. What cloud provider would you like to use? (AWS or Azure)"
        }