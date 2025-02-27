from .azure_resource_agent import AzureResourceAgent

class AzureAKSAgent(AzureResourceAgent):
    def __init__(self, llm):
        super().__init__(llm)
        self.required_fields = [
            {"name": "name", "question": "What name would you like for your AKS cluster?", 
             "description": "the name for the Azure Kubernetes Service cluster"},
            {"name": "resource_group", "question": "What Resource Group should the AKS cluster be created in?", 
             "description": "the name of the Resource Group where the AKS cluster will be created"},
            {"name": "location", "question": "In which Azure region should the AKS cluster be created? (e.g., eastus)", 
             "description": "the Azure region where the AKS cluster will be created"},
            {"name": "kubernetes_version", "question": "What Kubernetes version would you like to use? (e.g., 1.24.9)", 
             "description": "the Kubernetes version to use for the cluster"},
            {"name": "node_count", "question": "How many nodes would you like in the default node pool?", 
             "description": "the number of nodes in the default node pool"},
            {"name": "vm_size", "question": "What VM size would you like for the nodes? (e.g., Standard_DS2_v2)", 
             "description": "the VM size for the nodes in the cluster"}
        ]
        self.optional_fields = [
            {"name": "dns_prefix", "question": "What DNS prefix would you like to use for the cluster?", 
             "description": "the DNS prefix to use for the cluster's FQDN"},
            {"name": "network_plugin", "question": "What network plugin would you like to use? (azure, kubenet)", 
             "description": "the network plugin to use for the cluster (azure or kubenet)"},
            {"name": "enable_rbac", "question": "Would you like to enable RBAC? (yes/no)", 
             "description": "whether to enable role-based access control for the cluster"},
            {"name": "tags", "question": "Enter any tags you'd like to add in the format 'key1=value1,key2=value2'", 
             "description": "any tags to add to the AKS cluster in key-value format"}
        ]
    
    def generate_manifest(self, collected_data):
        """Generate a Crossplane manifest for an AKS cluster"""
        template = f"""apiVersion: container.azure.upbound.io/v1beta1
kind: KubernetesCluster
metadata:
  name: {collected_data.get('name', 'my-aks-cluster')}
spec:
  forProvider:
    resourceGroupName: {collected_data.get('resource_group')}
    location: {collected_data.get('location', 'eastus')}
    kubernetesVersion: {collected_data.get('kubernetes_version', '1.24.9')}
    defaultNodePool:
      name: default
      nodeCount: {collected_data.get('node_count', '3')}
      vmSize: {collected_data.get('vm_size', 'Standard_DS2_v2')}
    identity:
      type: SystemAssigned
"""
        
        # Add DNS prefix if provided
        if 'dns_prefix' in collected_data and collected_data['dns_prefix']:
            template += f"    dnsPrefix: {collected_data['dns_prefix']}\n"
        
        # Add network profile if provided
        if 'network_plugin' in collected_data and collected_data['network_plugin']:
            template += f"""    networkProfile:
      networkPlugin: {collected_data['network_plugin']}
"""
        
        # Add RBAC if provided
        if 'enable_rbac' in collected_data:
            value = collected_data['enable_rbac'].lower() in ['yes', 'true', '1']
            template += f"    enableRBAC: {str(value).lower()}\n"
        
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