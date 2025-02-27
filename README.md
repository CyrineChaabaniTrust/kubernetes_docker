# Crossplane YAML Manifest Generator

A chatbot to help users generate Crossplane YAML manifests for different cloud providers.

## Setup

1. Clone the repository:

```bash
git clone [https://github.com/crossplane/crossplane-chatbot.git](https://github.com/CyrineChaabaniTrust/kubernetes_docker.git)
cd kubernetes_docker/crossplane-chatbot
```


2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

3. Create a `.env` file in the root directory with your OpenAI API key:

```bash
OPENAI_API_KEY=your_api_key_here
```

4. Run the chatbot:

## Running the Command Line Interface

```bash
python main.py
```

then open your browser and go to:

```bash
http://localhost:5000
```


Then open your browser and navigate to `http://localhost:5000`

## Available Commands

- `help`: Show help message
- `undo`: Undo the last step
- `restart`: Start a new conversation
- `exit`: Exit the application (CLI only)

## Supported Cloud Providers and Resources

### AWS
- S3 Buckets
- RDS Instances
- EKS Clusters
- EC2 Instances
- IAM Roles

### Azure
- Resource Groups
- AKS Clusters
- Storage Accounts
- SQL Servers
- App Services
- Virtual Networks
- Cosmos DB Accounts

## Architecture

The application consists of several components:

1. **Orchestrator Agent**: Coordinates the conversation flow and delegates to provider-specific agents
2. **Provider Agents**: AWS and Azure agents that handle resource-specific interactions
3. **Manifest Generators**: Create the actual YAML manifests based on collected data
4. **Conversation State**: Manages and persists the state of conversations
5. **Error Handler**: Provides consistent error handling across the application
6. **Web Interface**: A user-friendly interface to interact with the chatbot

## Development

To extend the application with new cloud providers or resources:

1. Add new schema files in the appropriate schema directory
2. Create or update provider agents to handle new resource types
3. Implement the corresponding manifest generation logic



