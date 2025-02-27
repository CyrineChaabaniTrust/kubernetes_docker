from .aws_resource_agent import AWSResourceAgent

class AWSIAMAgent(AWSResourceAgent):
    def __init__(self, llm):
        super().__init__(llm)
        self.required_fields = [
            {"name": "name", "question": "What name would you like for your IAM role?", 
             "description": "the name for the IAM role"},
            {"name": "assume_role_policy", "question": "What service should be able to assume this role? (e.g., ec2, lambda)", 
             "description": "which AWS service should be allowed to assume this role"}
        ]
        self.optional_fields = [
            {"name": "managed_policies", "question": "What managed policies would you like to attach? (comma-separated ARNs)", 
             "description": "any managed policies to attach to the role (by ARN)"},
            {"name": "tags", "question": "Enter any tags you'd like to add in the format 'key1=value1,key2=value2'", 
             "description": "any tags to add to the role in key-value format"}
        ]