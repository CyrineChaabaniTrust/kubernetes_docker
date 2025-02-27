import logging
import yaml
from utils.schema_validator import validate_azure_resource

logger = logging.getLogger(__name__)

class AzureManifestGenerator:
    """Generator for Azure Crossplane manifests"""
    
    def generate_manifest(self, resource_type, data):
        """Generate a YAML manifest for an Azure resource"""
        # Validate the collected data
        validation_errors = validate_azure_resource(resource_type, data)
        if validation_errors:
            logger.error(f"Validation errors for Azure {resource_type}: {validation_errors}")
            error_msg = "\n".join(validation_errors)
            return f"There were validation errors with your inputs:\n{error_msg}\nPlease try again."
        
        # Call the appropriate generator method based on resource type
        if resource_type == 'resource_group':
            return self.generate_resource_group_manifest(data)
        elif resource_type == 'aks':
            return self.generate_aks_manifest(data)
        elif resource_type == 'storage':
            return self.generate_storage_manifest(data)
        elif resource_type == 'sql':
            return self.generate_sql_manifest(data)
        elif resource_type == 'app_service':
            return self.generate_app_service_manifest(data)
        elif resource_type == 'vnet':
            return self.generate_vnet_manifest(data)
        elif resource_type == 'cosmosdb':
            return self.generate_cosmosdb_manifest(data)
        else:
            logger.error(f"Unsupported Azure resource type: {resource_type}")
            return f"Sorry, {resource_type} is not supported yet."
    
    def generate_resource_group_manifest(self, data):
        """Generate a YAML manifest for an Azure Resource Group"""
        # Create the basic structure
        manifest = {
            "apiVersion": "azure.crossplane.io/v1alpha1",
            "kind": "ResourceGroup",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "location": data['location']
                },
                "providerConfigRef": {
                    "name": "azure-provider"
                }
            }
        }
        
        # Add tags if provided
        if 'tags' in data and data['tags']:
            # Parse tags in format "key1=value1,key2=value2"
            tag_pairs = data['tags'].split(',')
            tags = {}
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tags[key.strip()] = value.strip()
            
            if tags:
                manifest['spec']['forProvider']['tags'] = tags
        
        # Convert to YAML
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def generate_aks_manifest(self, data):
        """Generate a YAML manifest for an Azure Kubernetes Service cluster"""
        # Create the basic structure
        manifest = {
            "apiVersion": "container.azure.crossplane.io/v1alpha1",
            "kind": "AKSCluster",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "resourceGroupName": data['resource_group'],
                    "location": data['location'],
                    "kubernetesVersion": data['kubernetes_version'],
                    "defaultNodePool": {
                        "name": "default",
                        "count": int(data['node_count']),
                        "vmSize": data['vm_size']
                    },
                    "dnsPrefix": data['dns_prefix'],
                    "identity": {
                        "type": "SystemAssigned"
                    }
                },
                "providerConfigRef": {
                    "name": "azure-provider"
                }
            }
        }
        
        # Add network profile if provided
        if 'network_plugin' in data and data['network_plugin']:
            manifest['spec']['forProvider']['networkProfile'] = {
                "networkPlugin": data['network_plugin']
            }
        
        # Add tags if provided
        if 'tags' in data and data['tags']:
            # Parse tags in format "key1=value1,key2=value2"
            tag_pairs = data['tags'].split(',')
            tags = {}
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tags[key.strip()] = value.strip()
            
            if tags:
                manifest['spec']['forProvider']['tags'] = tags
        
        # Add connection secret
        manifest['spec']['writeConnectionSecretToRef'] = {
            "name": f"{data['name']}-conn",
            "namespace": "crossplane-system"
        }
        
        # Convert to YAML
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def generate_storage_manifest(self, data):
        """Generate a YAML manifest for an Azure Storage Account"""
        # Create the basic structure
        manifest = {
            "apiVersion": "storage.azure.crossplane.io/v1alpha1",
            "kind": "Account",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "resourceGroupName": data['resource_group'],
                    "location": data['location'],
                    "kind": "StorageV2",
                    "sku": {
                        "name": data['sku']
                    }
                },
                "providerConfigRef": {
                    "name": "azure-provider"
                }
            }
        }
        
        # Add optional fields if provided
        if 'kind' in data and data['kind']:
            manifest['spec']['forProvider']['kind'] = data['kind']
        
        if 'access_tier' in data and data['access_tier']:
            manifest['spec']['forProvider']['accessTier'] = data['access_tier']
        
        if 'enable_https' in data and data['enable_https'].lower() == 'yes':
            manifest['spec']['forProvider']['supportsHttpsTrafficOnly'] = True
        
        # Add tags if provided
        if 'tags' in data and data['tags']:
            # Parse tags in format "key1=value1,key2=value2"
            tag_pairs = data['tags'].split(',')
            tags = {}
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tags[key.strip()] = value.strip()
            
            if tags:
                manifest['spec']['forProvider']['tags'] = tags
        
        # Add connection secret
        manifest['spec']['writeConnectionSecretToRef'] = {
            "name": f"{data['name']}-conn",
            "namespace": "crossplane-system"
        }
        
        # Convert to YAML
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def generate_sql_manifest(self, data):
        """Generate a YAML manifest for an Azure SQL Server"""
        # Create the basic structure
        manifest = {
            "apiVersion": "database.azure.crossplane.io/v1alpha1",
            "kind": "SQLServer",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "resourceGroupName": data['resource_group'],
                    "location": data['location'],
                    "administratorLogin": data['admin_login']
                },
                "providerConfigRef": {
                    "name": "azure-provider"
                }
            }
        }
        
        # Add password if provided
        if 'admin_password' in data and data['admin_password']:
            manifest['spec']['forProvider']['administratorLoginPassword'] = data['admin_password']
        
        # Add version if provided
        if 'version' in data and data['version']:
            manifest['spec']['forProvider']['version'] = data['version']
        
        # Add TLS version if provided
        if 'minimal_tls_version' in data and data['minimal_tls_version']:
            manifest['spec']['forProvider']['minimalTlsVersion'] = data['minimal_tls_version']
        
        # Add tags if provided
        if 'tags' in data and data['tags']:
            # Parse tags in format "key1=value1,key2=value2"
            tag_pairs = data['tags'].split(',')
            tags = {}
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tags[key.strip()] = value.strip()
            
            if tags:
                manifest['spec']['forProvider']['tags'] = tags
        
        # Add connection secret
        manifest['spec']['writeConnectionSecretToRef'] = {
            "name": f"{data['name']}-conn",
            "namespace": "crossplane-system"
        }
        
        # Convert to YAML
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def generate_app_service_manifest(self, data):
        """Generate a YAML manifest for an Azure App Service"""
        # Create the basic structure
        manifest = {
            "apiVersion": "web.azure.crossplane.io/v1alpha1",
            "kind": "AppService",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "resourceGroupName": data['resource_group'],
                    "location": data['location'],
                    "appServicePlanIdRef": {
                        "name": data['app_service_plan']
                    },
                    "siteConfig": {}
                },
                "providerConfigRef": {
                    "name": "azure-provider"
                }
            }
        }
        
        # Add optional fields if provided
        if 'runtime_stack' in data and data['runtime_stack']:
            manifest['spec']['forProvider']['siteConfig']['linuxFxVersion'] = data['runtime_stack']
        
        if 'always_on' in data and data['always_on'].lower() == 'yes':
            manifest['spec']['forProvider']['siteConfig']['alwaysOn'] = True
        
        if 'https_only' in data and data['https_only'].lower() == 'yes':
            manifest['spec']['forProvider']['httpsOnly'] = True
        
        if 'min_tls_version' in data and data['min_tls_version']:
            manifest['spec']['forProvider']['siteConfig']['minTlsVersion'] = data['min_tls_version']
        
        # Add tags if provided
        if 'tags' in data and data['tags']:
            # Parse tags in format "key1=value1,key2=value2"
            tag_pairs = data['tags'].split(',')
            tags = {}
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tags[key.strip()] = value.strip()
            
            if tags:
                manifest['spec']['forProvider']['tags'] = tags
        
        # Add connection secret
        manifest['spec']['writeConnectionSecretToRef'] = {
            "name": f"{data['name']}-conn",
            "namespace": "crossplane-system"
        }
        
        # Convert to YAML
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def generate_vnet_manifest(self, data):
        """Generate a YAML manifest for an Azure Virtual Network"""
        # Create the basic structure
        manifest = {
            "apiVersion": "network.azure.crossplane.io/v1alpha1",
            "kind": "VirtualNetwork",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "resourceGroupName": data['resource_group'],
                    "location": data['location'],
                    "addressSpace": {
                        "addressPrefixes": [data['address_space']]
                    }
                },
                "providerConfigRef": {
                    "name": "azure-provider"
                }
            }
        }
        
        # Add DNS servers if provided
        if 'dns_servers' in data and data['dns_servers'] and data['dns_servers'].lower() != 'skip':
            dns_servers = [s.strip() for s in data['dns_servers'].split(',')]
            manifest['spec']['forProvider']['dhcpOptions'] = {
                "dnsServers": dns_servers
            }
        
        # Add subnet if provided
        if 'subnet_name' in data and data['subnet_name'] and 'subnet_prefix' in data and data['subnet_prefix']:
            manifest['spec']['forProvider']['subnets'] = [
                {
                    "name": data['subnet_name'],
                    "properties": {
                        "addressPrefix": data['subnet_prefix']
                    }
                }
            ]
        
        # Add tags if provided
        if 'tags' in data and data['tags']:
            # Parse tags in format "key1=value1,key2=value2"
            tag_pairs = data['tags'].split(',')
            tags = {}
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tags[key.strip()] = value.strip()
            
            if tags:
                manifest['spec']['forProvider']['tags'] = tags
        
        # Convert to YAML
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def generate_cosmosdb_manifest(self, data):
        """Generate a YAML manifest for an Azure CosmosDB Account"""
        # Create the basic structure
        manifest = {
            "apiVersion": "database.azure.crossplane.io/v1alpha1",
            "kind": "CosmosDBAccount",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "resourceGroupName": data['resource_group'],
                    "location": data['location'],
                    "kind": data['api'],
                    "locations": [
                        {
                            "locationName": data['location'],
                            "failoverPriority": 0
                        }
                    ]
                },
                "providerConfigRef": {
                    "name": "azure-provider"
                }
            }
        }
        
        # Add consistency level if provided
        if 'consistency_level' in data and data['consistency_level']:
            manifest['spec']['forProvider']['consistencyPolicy'] = {
                "defaultConsistencyLevel": data['consistency_level']
            }
        
        # Add multi-region writes if enabled
        if 'multi_region_write' in data and data['multi_region_write'].lower() == 'yes':
            manifest['spec']['forProvider']['enableMultipleWriteLocations'] = True
        
        # Add backup policy if provided
        if 'backup_policy' in data and data['backup_policy']:
            manifest['spec']['forProvider']['backupPolicy'] = {
                "type": data['backup_policy']
            }
        
        # Add tags if provided
        if 'tags' in data and data['tags']:
            # Parse tags in format "key1=value1,key2=value2"
            tag_pairs = data['tags'].split(',')
            tags = {}
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tags[key.strip()] = value.strip()
            
            if tags:
                manifest['spec']['forProvider']['tags'] = tags
        
        # Add connection secret
        manifest['spec']['writeConnectionSecretToRef'] = {
            "name": f"{data['name']}-conn",
            "namespace": "crossplane-system"
        }
        
        # Convert to YAML
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str