from .azure_resource_agent import AzureResourceAgent

class AzureAppServiceAgent(AzureResourceAgent):
    def __init__(self, llm):
        super().__init__(llm)
        self.required_fields = [
            {"name": "name", "question": "What name would you like for your App Service?",
             "description": "the name for the Azure App Service (must be globally unique)"},
            {"name": "resource_group", "question": "What Resource Group should the App Service be created in?",
             "description": "the name of the Resource Group where the App Service will be created"},
            {"name": "location", "question": "In which Azure region should the App Service be created? (e.g., eastus)",
             "description": "the Azure region where the App Service will be created"},
            {"name": "os_type", "question": "What operating system would you like to use? (Windows or Linux)",
             "description": "the operating system for the App Service (Windows or Linux)"}
        ]
        self.optional_fields = [
            {"name": "sku", "question": "What pricing tier would you like? (e.g., F1, B1, S1)",
             "description": "the pricing tier/service plan SKU for the App Service"},
            {"name": "runtime_stack", "question": "What runtime stack would you like to use? (e.g., .NET, Python, Node)",
             "description": "the programming language/framework for the App Service"},
            {"name": "always_on", "question": "Should the app be always on? (yes/no)",
             "description": "whether the app should be always running or can idle out"},
            {"name": "tags", "question": "Enter any tags you'd like to add in the format 'key1=value1,key2=value2'",
             "description": "any tags to add to the App Service in key-value format"}
        ]
    
    def generate_manifest(self, collected_data):
        """Generate a Crossplane manifest for an Azure App Service"""
        template = f"""apiVersion: web.azure.upbound.io/v1beta1
kind: AppService
metadata:
  name: {collected_data.get('name', 'my-app-service')}
spec:
  forProvider:
    resourceGroupName: {collected_data.get('resource_group')}
    location: {collected_data.get('location', 'eastus')}
    appServicePlanId: {collected_data.get('service_plan_id', 'TO_BE_CREATED')}
    siteConfig:
      - linuxFxVersion: {collected_data.get('runtime_stack', '')}
        windowsFxVersion: {collected_data.get('runtime_stack', '')}
"""
        
        # Add OS type specific configuration
        os_type = collected_data.get('os_type', '').lower()
        if os_type == 'linux':
            template += "      - linuxFxVersion: {}\n".format(collected_data.get('runtime_stack', ''))
        elif os_type == 'windows':
            template += "      - windowsFxVersion: {}\n".format(collected_data.get('runtime_stack', ''))
        
        # Add SKU if provided
        if 'sku' in collected_data and collected_data['sku']:
            template += f"    sku: {collected_data['sku']}\n"
        
        # Add always on if provided
        if 'always_on' in collected_data:
            value = collected_data['always_on'].lower() in ['yes', 'true', '1']
            template += f"    siteConfig:\n      - alwaysOn: {str(value).lower()}\n"
        
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