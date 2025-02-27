from .azure_resource_agent import AzureResourceAgent

class AzureSQLAgent(AzureResourceAgent):
    def __init__(self, llm):
        super().__init__(llm)
        self.required_fields = [
            {"name": "name", "question": "What name would you like for your SQL Database?", 
             "description": "the name for the Azure SQL Database"},
            {"name": "resource_group", "question": "What Resource Group should the SQL Database be created in?", 
             "description": "the name of the Resource Group where the SQL Database will be created"},
            {"name": "server_name", "question": "What is the name of the SQL Server to host the database?", 
             "description": "the name of the SQL Server where the database will be created"},
            {"name": "location", "question": "In which Azure region should the SQL Database be created? (e.g., eastus)", 
             "description": "the Azure region where the SQL Database will be created"}
        ]
        self.optional_fields = [
            {"name": "sku", "question": "What SKU would you like to use? (e.g., Basic, Standard, Premium)", 
             "description": "the pricing tier/SKU for the database"},
            {"name": "max_size_gb", "question": "What is the maximum size in GB for the database?", 
             "description": "the maximum size in GB for the database"},
            {"name": "zone_redundant", "question": "Should the database be zone-redundant? (yes/no)", 
             "description": "whether the database should be zone-redundant"},
            {"name": "tags", "question": "Enter any tags you'd like to add in the format 'key1=value1,key2=value2'", 
             "description": "any tags to add to the SQL Database in key-value format"}
        ]
    
    def generate_manifest(self, collected_data):
        """Generate a Crossplane manifest for an Azure SQL Database"""
        template = f"""apiVersion: sql.azure.upbound.io/v1beta1
kind: Database
metadata:
  name: {collected_data.get('name', 'my-sql-database')}
spec:
  forProvider:
    resourceGroupName: {collected_data.get('resource_group')}
    serverName: {collected_data.get('server_name')}
    location: {collected_data.get('location', 'eastus')}
"""
        
        # Add SKU if provided
        if 'sku' in collected_data and collected_data['sku']:
            template += f"    sku: {collected_data['sku']}\n"
        
        # Add max size if provided
        if 'max_size_gb' in collected_data and collected_data['max_size_gb']:
            template += f"    maxSizeGB: {collected_data['max_size_gb']}\n"
        
        # Add zone redundancy if provided
        if 'zone_redundant' in collected_data:
            value = collected_data['zone_redundant'].lower() in ['yes', 'true', '1']
            template += f"    zoneRedundant: {str(value).lower()}\n"
        
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