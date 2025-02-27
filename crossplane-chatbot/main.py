from langchain.llms import OpenAI
from agents.orchestrator import OrchestratorAgent
from utils.conversation_state import ConversationState
from utils.error_handler import handle_errors, CrossplaneError
import logging
import os
import sys
import argparse
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("crossplane-chatbot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

@handle_errors
def main():
    parser = argparse.ArgumentParser(description="Crossplane YAML Manifest Generator")
    parser.add_argument("--conversation-id", help="Resume an existing conversation")
    args = parser.parse_args()
    
    # Get API key from environment variable
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        logger.error("OPENAI_API_KEY environment variable not set in .env file")
        print("Please set the OPENAI_API_KEY in your .env file")
        return 1
    
    # Initialize LLM
    try:
        llm = OpenAI(api_key=api_key)
        logger.info("LLM initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing LLM: {str(e)}")
        print(f"Error initializing AI model: {str(e)}")
        return 1
    
    # Initialize or load conversation state
    if args.conversation_id:
        state = ConversationState.load(args.conversation_id)
        if not state:
            logger.warning(f"Could not load conversation with ID {args.conversation_id}, starting new one")
            state = ConversationState()
            print(f"Starting a new conversation instead.")
        else:
            print(f"Resuming conversation {args.conversation_id}")
    else:
        state = ConversationState()
    
    # Create the orchestrator agent with the conversation state
    orchestrator = OrchestratorAgent(llm, state=state)
    
    print("Welcome to the Crossplane YAML Manifest Generator!")
    print("I'll help you create infrastructure as code using Crossplane.")
    print("What cloud provider and resource would you like to create today?")
    print("(Type 'help' for commands, 'exit' to quit)")
    
    # Main conversation loop
    while True:
        user_input = input("> ")
        
        if user_input.lower() in ["exit", "quit", "bye"]:
            print("Thank you for using the Crossplane YAML Manifest Generator. Goodbye!")
            # Save the final state before exiting
            state.save()
            break
        
        elif user_input.lower() == "help":
            print_help_message()
            continue
            
        elif user_input.lower() == "undo":
            if state.undo_last_step():
                print("Undid the last step. What would you like to do now?")
            else:
                print("Nothing to undo.")
            continue
            
        elif user_input.lower() == "restart":
            print("Starting a new conversation.")
            state = ConversationState()
            orchestrator = OrchestratorAgent(llm, state=state)
            print("What cloud provider and resource would you like to create today?")
            continue
        
        # Add user message to state
        state.add_message("user", user_input)
        
        try:
            # Process the user input
            response = orchestrator.process_message(user_input)
            
            # If response is a dict with an error, handle it
            if isinstance(response, dict) and response.get("error"):
                print(f"Error: {response.get('message')}")
                state.update(error_count=state.state["error_count"] + 1)
            else:
                print(response)
                state.add_message("assistant", response)
                
            # Save state after each interaction
            state.save()
            
        except CrossplaneError as e:
            print(f"Error: {e.user_message}")
            logger.error(f"Error during conversation: {e.message}")
            state.update(error_count=state.state["error_count"] + 1)
            state.save()
            
        except Exception as e:
            print(f"An unexpected error occurred. Please try again or restart the application.")
            logger.exception(f"Unhandled exception: {str(e)}")
            state.update(error_count=state.state["error_count"] + 1)
            state.save()

def print_help_message():
    """Print available commands and their descriptions"""
    print("\nAvailable commands:")
    print("  help     - Show this help message")
    print("  undo     - Undo the last step")
    print("  restart  - Start a new conversation")
    print("  exit     - Exit the application")
    print("\nTips:")
    print("- Be specific about the cloud provider and resource type you want to create")
    print("- You can change your mind at any point by using 'undo'")
    print("- Your conversation is automatically saved and can be resumed later\n")

if __name__ == "__main__":
    sys.exit(main() or 0)