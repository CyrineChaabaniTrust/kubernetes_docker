from .aws_resource_agent import AWSResourceAgent

class AWSEC2Agent(AWSResourceAgent):
    def __init__(self, llm):
        super().__init__(llm)
        self.required_fields = [
            {"name": "name", "question": "What name would you like for your EC2 instance?", 
             "description": "the name for the EC2 instance"},
            {"name": "region", "question": "Which AWS region should the instance be created in? (e.g., us-east-1)", 
             "description": "the AWS region where the instance will be created"},
            {"name": "instance_type", "question": "What instance type would you like to use? (e.g., t2.micro)", 
             "description": "the EC2 instance type defining compute, memory, and storage capabilities"},
            {"name": "ami", "question": "What AMI ID would you like to use?", 
             "description": "the Amazon Machine Image ID to use for the instance"}
        ]
        self.optional_fields = [
            {"name": "key_name", "question": "What key pair would you like to use for SSH access?", 
             "description": "the key pair for SSH access to the instance"},
            {"name": "subnet", "question": "What subnet would you like to launch the instance in?", 
             "description": "the subnet ID where the instance will be launched"},
            {"name": "security_groups", "question": "What security groups would you like to attach? (comma-separated)", 
             "description": "the security groups to attach to the instance (controls network access)"},
            {"name": "tags", "question": "Enter any tags you'd like to add in the format 'key1=value1,key2=value2'", 
             "description": "any tags to add to the instance in key-value format"}
        ]
