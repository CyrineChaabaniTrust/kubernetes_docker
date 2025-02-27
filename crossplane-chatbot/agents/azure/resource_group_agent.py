from .azure_resource_agent import AzureResourceAgent

class AzureResourceGroupAgent(AzureResourceAgent):
    def __init__(self, llm):
        super().__init__(llm)
        self.required_fields = [
            {"name": "name", "question": "What name would you like for your Resource Group?", 
             "description": "the name for the Azure Resource Group"},
            {"name": "location", "question": "In which Azure region should the Resource Group be created? (e.g., eastus, westeurope)", 
             "description": "the Azure region where the Resource Group will be created"}
        ]
        self.optional_fields = [
            {"name": "tags", "question": "Enter any tags you'd like to add in the format 'key1=value1,key2=value2'", 
             "description": "any tags to add to the Resource Group in key-value format"}
        ]
    
    def generate_manifest(self, collected_data):
        """Generate a Crossplane manifest for an Azure Resource Group"""
        template = f"""apiVersion: azure.upbound.io/v1beta1
kind: ResourceGroup
metadata:
  name: {collected_data.get('name', 'my-resource-group')}
spec:
  forProvider:
    location: {collected_data.get('location', 'eastus')}
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