from .aws_resource_agent import AWSResourceAgent

class AWSS3Agent(AWSResourceAgent):
    def __init__(self, llm):
        super().__init__(llm)
        self.required_fields = [
            {"name": "name", "question": "What name would you like for your S3 bucket?", 
             "description": "the name for the S3 bucket (must be globally unique)"},
            {"name": "region", "question": "Which AWS region should the bucket be created in? (e.g., us-east-1)", 
             "description": "the AWS region where the bucket will be created"},
            {"name": "acl", "question": "What ACL would you like to set? (e.g., private, public-read)", 
             "description": "the access control list for the bucket (e.g., private, public-read)"}
        ]
        self.optional_fields = [
            {"name": "versioning", "question": "Would you like to enable versioning for this bucket? (yes/no)", 
             "description": "whether to enable versioning for the bucket"},
            {"name": "encryption", "question": "Would you like to enable server-side encryption? (yes/no)", 
             "description": "whether to enable server-side encryption for the bucket"},
            {"name": "tags", "question": "Enter any tags you'd like to add in the format 'key1=value1,key2=value2'", 
             "description": "any tags to add to the bucket in key-value format"}
        ]
    
    def generate_manifest(self, collected_data):
        """Generate a Crossplane manifest for an S3 bucket"""
        template = f"""apiVersion: s3.aws.upbound.io/v1beta1
                        kind: Bucket
                        metadata:
                        name: {collected_data.get('name', 'my-s3-bucket')}
                        spec:
                        forProvider:
                            region: {collected_data.get('region', 'us-east-1')}
                            acl: {collected_data.get('acl', 'private')}
                    """
                            
        if 'versioning' in collected_data and collected_data['versioning'].lower() in ['yes', 'true', '1']:
            template += """    versioningConfiguration:
      status: Enabled
"""
        
        if 'encryption' in collected_data and collected_data['encryption'].lower() in ['yes', 'true', '1']:
            template += """    serverSideEncryptionConfiguration:
      rules:
        - applyServerSideEncryptionByDefault:
            sseAlgorithm: AES256
"""
        
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