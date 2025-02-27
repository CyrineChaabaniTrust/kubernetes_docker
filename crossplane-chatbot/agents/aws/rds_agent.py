from .aws_resource_agent import AWSResourceAgent

class AWSRDSAgent(AWSResourceAgent):
    def __init__(self, llm):
        super().__init__(llm)
        self.required_fields = [
            {"name": "name", "question": "What name would you like for your RDS instance?", 
             "description": "the name for the RDS database instance"},
            {"name": "region", "question": "Which AWS region should the RDS instance be created in? (e.g., us-east-1)", 
             "description": "the AWS region where the database will be created"},
            {"name": "engine", "question": "What database engine would you like to use? (e.g., mysql, postgres)", 
             "description": "the database engine to use (e.g., MySQL, PostgreSQL, SQL Server)"},
            {"name": "instance_class", "question": "What instance class would you like to use? (e.g., db.t3.micro)", 
             "description": "the compute and memory capacity for the database instance"},
            {"name": "storage", "question": "How much storage (in GB) would you like to allocate?", 
             "description": "the amount of storage in GB to allocate for the database"}
        ]
        self.optional_fields = [
            {"name": "username", "question": "What master username would you like to use?", 
             "description": "the master username for database access"},
            {"name": "publicly_accessible", "question": "Should the database be publicly accessible? (yes/no)", 
             "description": "whether the database should be accessible from the internet"},
            {"name": "multi_az", "question": "Should the database be deployed across multiple availability zones? (yes/no)", 
             "description": "whether to deploy the database across multiple availability zones for high availability"},
            {"name": "tags", "question": "Enter any tags you'd like to add in the format 'key1=value1,key2=value2'", 
             "description": "any tags to add to the database in key-value format"}
        ]
    
    def generate_manifest(self, collected_data):
        """Generate a Crossplane manifest for an RDS instance"""
        template = f"""apiVersion: rds.aws.upbound.io/v1beta1
kind: Instance
metadata:
  name: {collected_data.get('name', 'my-rds-instance')}
spec:
  forProvider:
    region: {collected_data.get('region', 'us-east-1')}
    engine: {collected_data.get('engine', 'mysql')}
    instanceClass: {collected_data.get('instance_class', 'db.t3.micro')}
    allocatedStorage: {collected_data.get('storage', '20')}
"""
        
        # Add username if provided
        if 'username' in collected_data and collected_data['username']:
            template += f"    username: {collected_data['username']}\n"
        
        # Add publicly accessible if provided
        if 'publicly_accessible' in collected_data:
            value = collected_data['publicly_accessible'].lower() in ['yes', 'true', '1']
            template += f"    publiclyAccessible: {str(value).lower()}\n"
        
        # Add multi-AZ if provided
        if 'multi_az' in collected_data:
            value = collected_data['multi_az'].lower() in ['yes', 'true', '1']
            template += f"    multiAz: {str(value).lower()}\n"
        
        # Add tags if provided
        if 'tags' in collected_data and collected_data['tags']:
            template += "    tags:\n"
            tags = collected_data['tags']
            if ',' in tags:
                tag_pairs = [pair.strip() for pair in tags.split(',')]
                for pair in tag_pairs:
                    if '=' in pair:
                        key, value = pair.split('=', 1)
                        template += f"      {key.strip()}: {value.strip()}\n"
        
        return template 