# Crossplane Azure Resource Guide

## Introduction

This guide explains how to create Crossplane YAML manifests for Azure resources. Crossplane enables you to define Azure infrastructure using Kubernetes-style resources, bringing cloud-native infrastructure as code to your Azure deployments.

## Azure Provider Configuration

Before creating resources, you must configure the Azure provider:

apiVersion: azure.crossplane.io/v1beta1
kind: ProviderConfig
metadata:
  name: azure-provider
spec:
  credentials:
    source: Secret
    secretRef:
      namespace: crossplane-system
      name: azure-credentials
      key: credentials

The Azure credentials secret should be created as follows:

apiVersion: v1
kind: Secret
metadata:
  name: azure-credentials
  namespace: crossplane-system
type: Opaque
data:
  credentials: <base64-encoded Azure credentials json>

The credentials JSON should contain:

{
  "clientId": "your-client-id",
  "clientSecret": "your-client-secret",
  "subscriptionId": "your-subscription-id",
  "tenantId": "your-tenant-id",
  "activeDirectoryEndpointUrl": "https://login.microsoftonline.com",
  "resourceManagerEndpointUrl": "https://management.azure.com/",
  "activeDirectoryGraphResourceId": "https://graph.windows.net/",
  "sqlManagementEndpointUrl": "https://management.core.windows.net:8443/",
  "galleryEndpointUrl": "https://gallery.azure.com/",
  "managementEndpointUrl": "https://management.core.windows.net/"
}

## Azure Resource Structure

Azure resources follow this basic structure:

apiVersion: <service>.azure.crossplane.io/<version>
kind: <ResourceType>
metadata:
  name: <resource-name>
spec:
  forProvider:
    resourceGroupName: <resource-group>
    location: <azure-region>
    # Azure-specific configuration
  writeConnectionSecretToRef:
    name: <connection-secret-name>
    namespace: <namespace>
  providerConfigRef:
    name: azure-provider

## Resource Group

Almost all Azure resources need a resource group. You can create one like this:

apiVersion: azure.crossplane.io/v1alpha1
kind: ResourceGroup
metadata:
  name: my-resource-group
spec:
  forProvider:
    location: eastus
    tags:
      Environment: Production
  providerConfigRef:
    name: azure-provider

## Common Azure Resources

### Azure Kubernetes Service (AKS)

apiVersion: compute.azure.crossplane.io/v1alpha1
kind: AKSCluster
metadata:
  name: my-aks
spec:
  forProvider:
    location: eastus
    resourceGroupName: my-resource-group
    kubernetesVersion: "1.24.6"
    defaultNodePool:
      name: default
      nodeCount: 3
      vmSize: Standard_DS2_v2
    dnsPrefix: my-aks-dns
    disableRBAC: false
    identity:
      type: SystemAssigned
    networkProfile:
      networkPlugin: azure
      networkPolicy: calico
      serviceCidr: 10.0.0.0/16
      dnsServiceIP: 10.0.0.10
      dockerBridgeCidr: 172.17.0.1/16
    addonProfiles:
      httpApplicationRouting:
        enabled: true
    tags:
      Environment: Production
  writeConnectionSecretToRef:
    name: my-aks-conn
    namespace: crossplane-system
  providerConfigRef:
    name: azure-provider

### Storage Account

apiVersion: storage.azure.crossplane.io/v1alpha1
kind: Account
metadata:
  name: my-storage
spec:
  forProvider:
    resourceGroupName: my-resource-group
    location: eastus
    kind: StorageV2
    sku:
      name: Standard_LRS
    accessTier: Hot
    enableHttpsTrafficOnly: true
    isHnsEnabled: false
    networkRuleSet:
      bypass: AzureServices
      defaultAction: Deny
      ipRules:
        - value: 203.0.113.0/24
          action: Allow
    tags:
      Environment: Production
  writeConnectionSecretToRef:
    name: my-storage-conn
    namespace: crossplane-system
  providerConfigRef:
    name: azure-provider

### SQL Server

apiVersion: database.azure.crossplane.io/v1alpha1
kind: SQLServer
metadata:
  name: my-sql-server
spec:
  forProvider:
    resourceGroupName: my-resource-group
    location: eastus
    administratorLogin: admin
    version: "12.0"
    minimalTlsVersion: "1.2"
    publicNetworkAccess: Enabled
    tags:
      Environment: Production
  writeConnectionSecretToRef:
    name: my-sql-server-conn
    namespace: crossplane-system
  providerConfigRef:
    name: azure-provider

### SQL Database

apiVersion: database.azure.crossplane.io/v1alpha1
kind: SQLServerDatabase
metadata:
  name: my-database
spec:
  forProvider:
    resourceGroupName: my-resource-group
    serverName: my-sql-server
    sku:
      name: S0
      tier: Standard
    maxSizeBytes: 268435456000
    tags:
      Environment: Production
  writeConnectionSecretToRef:
    name: my-database-conn
    namespace: crossplane-system
  providerConfigRef:
    name: azure-provider

### Virtual Network

apiVersion: network.azure.crossplane.io/v1alpha1
kind: VirtualNetwork
metadata:
  name: my-vnet
spec:
  forProvider:
    resourceGroupName: my-resource-group
    location: eastus
    addressSpace:
      - 10.0.0.0/16
    subnets:
      - name: subnet1
        addressPrefix: 10.0.1.0/24
      - name: subnet2
        addressPrefix: 10.0.2.0/24
    tags:
      Environment: Production
  writeConnectionSecretToRef:
    name: my-vnet-conn
    namespace: crossplane-system
  providerConfigRef:
    name: azure-provider

### App Service Plan

apiVersion: web.azure.crossplane.io/v1alpha1
kind: AppServicePlan
metadata:
  name: my-app-plan
spec:
  forProvider:
    resourceGroupName: my-resource-group
    location: eastus
    kind: Linux
    reserved: true
    sku:
      name: P1v2
      tier: PremiumV2
      size: P1v2
      family: Pv2
      capacity: 1
    tags:
      Environment: Production
  writeConnectionSecretToRef:
    name: my-app-plan-conn
    namespace: crossplane-system
  providerConfigRef:
    name: azure-provider

### App Service (Web App)

apiVersion: web.azure.crossplane.io/v1alpha1
kind: AppService
metadata:
  name: my-webapp
spec:
  forProvider:
    resourceGroupName: my-resource-group
    location: eastus
    appServicePlanIdRef:
      name: my-app-plan
    siteConfig:
      linuxFxVersion: "DOCKER|nginx:latest"
      alwaysOn: true
      http20Enabled: true
      minTlsVersion: 1.2
      appSettings:
        - name: DOCKER_REGISTRY_SERVER_URL
          value: https://index.docker.io
        - name: WEBSITES_PORT
          value: "80"
    httpsOnly: true
    identity:
      type: SystemAssigned
    tags:
      Environment: Production
  writeConnectionSecretToRef:
    name: my-webapp-conn
    namespace: crossplane-system
  providerConfigRef:
    name: azure-provider

### CosmosDB Account

apiVersion: database.azure.crossplane.io/v1alpha1
kind: CosmosDBAccount
metadata:
  name: my-cosmos
spec:
  forProvider:
    resourceGroupName: my-resource-group
    location: eastus
    kind: MongoDB
    consistencyPolicy:
      defaultConsistencyLevel: Session
    enableAutomaticFailover: true
    locations:
      - locationName: eastus
        failoverPriority: 0
      - locationName: westus
        failoverPriority: 1
    capabilities:
      - name: EnableMongo
    tags:
      Environment: Production
  writeConnectionSecretToRef:
    name: my-cosmos-conn
    namespace: crossplane-system
  providerConfigRef:
    name: azure-provider

## Using Resource References

Azure Crossplane providers support references to other resources instead of hardcoded values:

apiVersion: web.azure.crossplane.io/v1alpha1
kind: AppService
metadata:
  name: my-webapp
spec:
  forProvider:
    resourceGroupNameRef:
      name: my-resource-group
    appServicePlanIdRef:
      name: my-app-plan
    # ... other configuration
  providerConfigRef:
    name: azure-provider

## Azure-Specific Best Practices

1. **Always include resource group and location**: Most Azure resources require these two fields
   forProvider:
     resourceGroupName: my-resource-group
     location: eastus

2. **Use Managed Identities**: Leverage Azure's managed identities for secure service-to-service authentication
   identity:
     type: SystemAssigned

3. **Tag your resources**: Add consistent tags to all resources
   tags:
     Environment: Production
     CostCenter: "123456"

4. **Multi-region deployment**: For critical services, deploy across multiple regions
   locations:
     - locationName: eastus
       failoverPriority: 0
     - locationName: westus
       failoverPriority: 1

5. **Secure your resources**: Enable security features like HTTPS only and minimum TLS versions
   httpsOnly: true
   minTlsVersion: 1.2

6. **Use references over hardcoded values**: Prefer `resourceGroupNameRef` over `resourceGroupName` where supported

## Troubleshooting Azure Resources

1. **Check Resource Status**: Use kubectl to check the current status
   kubectl describe akscluster my-aks

2. **Check Events**: Look for events related to your resource
   kubectl get events | grep my-aks

3. **Provider Logs**: Check the Azure provider controller logs
   kubectl logs -n crossplane-system deployment/provider-azure -c provider-azure

4. **Common Issues**:
   - Service principal permissions are insufficient
   - Resource naming conflicts with existing Azure resources
   - Location/region availability for specific resource types
   - Resource quota limits

5. **Azure Portal**: Verify the state of resources in the Azure Portal

For more detailed information, refer to the Crossplane Azure Provider Documentation.