from .aws_resource_agent import AWSResourceAgent

class AWSEKSAgent(AWSResourceAgent):
    def __init__(self, llm):
        super().__init__(llm)
        self.required_fields = [
            {"name": "name", "question": "What name would you like for your EKS cluster?", 
             "description": "the name for the Kubernetes cluster"},
            {"name": "region", "question": "Which AWS region should the cluster be created in? (e.g., us-east-1)", 
             "description": "the AWS region where the cluster will be created"},
            {"name": "version", "question": "What Kubernetes version would you like to use? (e.g., 1.24)", 
             "description": "the Kubernetes version to use for the cluster"}
        ]
        self.optional_fields = [
            {"name": "node_type", "question": "What instance type would you like for the worker nodes? (e.g., t3.medium)", 
             "description": "the EC2 instance type for worker nodes"},
            {"name": "node_count", "question": "How many worker nodes would you like?", 
             "description": "the number of worker nodes to create initially"},
            {"name": "private_access", "question": "Should the cluster have private API access? (yes/no)", 
             "description": "whether the Kubernetes API server should be accessible from within your VPC"},
            {"name": "public_access", "question": "Should the cluster have public API access? (yes/no)", 
             "description": "whether the Kubernetes API server should be accessible from the internet"},
            {"name": "tags", "question": "Enter any tags you'd like to add in the format 'key1=value1,key2=value2'", 
             "description": "any tags to add to the cluster in key-value format"}
        ]
    
    def generate_manifest(self, collected_data):
        """Generate a Crossplane manifest for an EKS cluster"""
        template = f"""apiVersion: eks.aws.upbound.io/v1beta1
kind: Cluster
metadata:
  name: {collected_data.get('name', 'my-eks-cluster')}
spec:
  forProvider:
    region: {collected_data.get('region', 'us-east-1')}
    version: {collected_data.get('version', '1.24')}
    roleArnRef:
      name: eks-cluster-role
"""
        
        # Add node group configuration if node type and count are provided
        if ('node_type' in collected_data and collected_data['node_type']) or \
           ('node_count' in collected_data and collected_data['node_count']):
            template += f"""    nodeGroups:
      - name: {collected_data.get('name', 'my-eks-cluster')}-workers
        instanceType: {collected_data.get('node_type', 't3.medium')}
        desiredSize: {collected_data.get('node_count', '2')}
        minSize: 1
        maxSize: 4
        amiType: AL2_x86_64
"""
        
        # Add VPC config for API access
        if 'private_access' in collected_data or 'public_access' in collected_data:
            private_access = collected_data.get('private_access', '').lower() in ['yes', 'true', '1']
            public_access = collected_data.get('public_access', '').lower() in ['yes', 'true', '1'] 
            template += f"""    vpcConfig:
      endpointPrivateAccess: {str(private_access).lower()}
      endpointPublicAccess: {str(public_access).lower()}
"""
        
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