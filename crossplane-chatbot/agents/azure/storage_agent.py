from .azure_resource_agent import AzureResourceAgent

class AzureStorageAgent(AzureResourceAgent):
    def __init__(self, llm):
        super().__init__(llm)
        self.required_fields = [
            {"name": "name", "question": "What name would you like for your Storage Account?",
             "description": "the name for the Azure Storage Account (must be globally unique, lowercase letters and numbers only)"},
            {"name": "resource_group", "question": "What Resource Group should the Storage Account be created in?",
             "description": "the name of the Resource Group where the Storage Account will be created"},
            {"name": "location", "question": "In which Azure region should the Storage Account be created? (e.g., eastus)",
             "description": "the Azure region where the Storage Account will be created"},
            {"name": "kind", "question": "What kind of Storage Account would you like? (e.g., StorageV2, BlobStorage)",
             "description": "the kind of Storage Account (StorageV2, BlobStorage, FileStorage, etc.)"}
        ]
        self.optional_fields = [
            {"name": "tier", "question": "What performance tier? (Standard or Premium)",
             "description": "the performance tier of the Storage Account (Standard or Premium)"},
            {"name": "replication", "question": "What data replication strategy? (e.g., LRS, GRS, ZRS)",
             "description": "the data replication strategy (Locally Redundant Storage, Geo-Redundant Storage, etc.)"},
            {"name": "access_tier", "question": "What access tier would you like? (Hot or Cool)",
             "description": "the access tier determining storage costs and access latency (Hot or Cool)"},
            {"name": "tags", "question": "Enter any tags you'd like to add in the format 'key1=value1,key2=value2'",
             "description": "any tags to add to the Storage Account in key-value format"}
        ]
    
    def generate_manifest(self, collected_data):
        """Generate a Crossplane manifest for an Azure Storage Account"""
        template = f"""apiVersion: storage.azure.upbound.io/v1beta1
kind: Account
metadata:
  name: {collected_data.get('name', 'mystorageaccount')}
spec:
  forProvider:
    resourceGroupName: {collected_data.get('resource_group')}
    location: {collected_data.get('location', 'eastus')}
    accountKind: {collected_data.get('kind', 'StorageV2')}
"""
        
        # Add tier if provided
        if 'tier' in collected_data and collected_data['tier']:
            template += f"    accountTier: {collected_data['tier']}\n"
        
        # Add replication if provided
        if 'replication' in collected_data and collected_data['replication']:
            template += f"    accountReplicationType: {collected_data['replication']}\n"
        
        # Add access tier if provided
        if 'access_tier' in collected_data and collected_data['access_tier']:
            template += f"    accessTier: {collected_data['access_tier']}\n"
        
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