# Crossplane GCP Resource Guide

## Introduction

This guide explains how to create Crossplane YAML manifests for Google Cloud Platform (GCP) resources. Crossplane enables you to define GCP infrastructure using Kubernetes-style resources, bringing cloud-native infrastructure as code to your GCP deployments.

## GCP Provider Configuration

Before creating resources, you must configure the GCP provider:

apiVersion: gcp.crossplane.io/v1beta1
kind: ProviderConfig
metadata:
  name: gcp-provider
spec:
  projectID: your-gcp-project-id
  credentials:
    source: Secret
    secretRef:
      namespace: crossplane-system
      name: gcp-credentials
      key: credentials

The GCP credentials secret should be created as follows:

apiVersion: v1
kind: Secret
metadata:
  name: gcp-credentials
  namespace: crossplane-system
type: Opaque
data:
  credentials: <base64-encoded GCP service account key json>

The service account key should have the necessary IAM roles assigned to it for provisioning the resources you intend to create.

## GCP Resource Structure

GCP resources follow this basic structure:

apiVersion: <service>.gcp.crossplane.io/<version>
kind: <ResourceType>
metadata:
  name: <resource-name>
spec:
  forProvider:
    # GCP-specific configuration
  writeConnectionSecretToRef:
    name: <connection-secret-name>
    namespace: <namespace>
  providerConfigRef:
    name: gcp-provider

## Common GCP Resources

### GKE Cluster

apiVersion: container.gcp.crossplane.io/v1beta1
kind: GKECluster
metadata:
  name: my-gke
spec:
  forProvider:
    location: us-central1-a
    initialClusterVersion: "1.24"
    network: default
    subnetwork: default
    ipAllocationPolicy:
      createSubnetwork: true
      useIpAliases: true
    clusterAutoscaling:
      enabled: true
      autoscalingProfile: BALANCED
      resourceLimits:
        - resourceType: cpu
          minimum: 1
          maximum: 10
        - resourceType: memory
          minimum: 2
          maximum: 32
    nodePools:
      - name: default-pool
        initialNodeCount: 3
        autoscaling:
          enabled: true
          minNodeCount: 1
          maxNodeCount: 5
        config:
          machineType: n1-standard-2
          diskSizeGb: 100
          oauthScopes:
            - https://www.googleapis.com/auth/devstorage.read_only
            - https://www.googleapis.com/auth/logging.write
            - https://www.googleapis.com/auth/monitoring
          metadata:
            disable-legacy-endpoints: "true"
    loggingService: logging.googleapis.com/kubernetes
    monitoringService: monitoring.googleapis.com/kubernetes
    privateClusterConfig:
      enablePrivateNodes: true
      enablePrivateEndpoint: false
      masterIpv4CidrBlock: "172.16.0.0/28"
    masterAuthorizedNetworksConfig:
      enabled: true
      cidrBlocks:
        - displayName: CompanyOffice
          cidrBlock: "203.0.113.0/24"
    resourceLabels:
      environment: production
  writeConnectionSecretToRef:
    name: my-gke-conn
    namespace: crossplane-system
  providerConfigRef:
    name: gcp-provider

### Cloud SQL Instance

apiVersion: database.gcp.crossplane.io/v1beta1
kind: CloudSQLInstance
metadata:
  name: my-cloudsql
spec:
  forProvider:
    databaseVersion: POSTGRES_13
    region: us-central1
    settings:
      tier: db-custom-2-8192
      dataDiskSizeGb: 20
      dataDiskType: PD_SSD
      backupConfiguration:
        enabled: true
        startTime: "20:00"
        backupRetentionSettings:
          retainedBackups: 7
      ipConfiguration:
        ipv4Enabled: true
        requireSsl: true
        authorizedNetworks:
          - name: office
            value: "203.0.113.0/24"
      locationPreference:
        zone: us-central1-a
      maintenanceWindow:
        day: 7
        hour: 3
      availabilityType: REGIONAL
      databaseFlags:
        - name: max_connections
          value: "100"
      userLabels:
        environment: production
  writeConnectionSecretToRef:
    name: my-cloudsql-conn
    namespace: crossplane-system
  providerConfigRef:
    name: gcp-provider

### GCP Storage Bucket

apiVersion: storage.gcp.crossplane.io/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
spec:
  forProvider:
    location: US
    storageClass: STANDARD
    versioning:
      enabled: true
    cors:
      - origin: ["https://example.com"]
        method: ["GET", "POST", "PUT"]
        responseHeader: ["Content-Type"]
        maxAgeSeconds: 3600
    lifecycle:
      rules:
        - action:
            type: SetStorageClass
            storageClass: NEARLINE
          condition:
            age: 30
            createdBefore: "2021-01-01"
            numNewerVersions: 3
            withState: LIVE
    logging:
      logBucket: logging-bucket
      logObjectPrefix: my-bucket-logs
    encryption:
      defaultKmsKeyName: projects/your-project/locations/global/keyRings/my-keyring/cryptoKeys/my-key
    labels:
      environment: production
  writeConnectionSecretToRef:
    name: my-bucket-conn
    namespace: crossplane-system
  providerConfigRef:
    name: gcp-provider

### Cloud Pub/Sub Topic

apiVersion: pubsub.gcp.crossplane.io/v1alpha1
kind: Topic
metadata:
  name: my-topic
spec:
  forProvider:
    labels:
      environment: production
    messageStoragePolicy:
      allowedPersistenceRegions:
        - us-central1
    kmsKeyName: projects/your-project/locations/global/keyRings/my-keyring/cryptoKeys/my-key
    messageRetentionDuration: 86400s
  providerConfigRef:
    name: gcp-provider

### Cloud Pub/Sub Subscription

apiVersion: pubsub.gcp.crossplane.io/v1alpha1
kind: Subscription
metadata:
  name: my-subscription
spec:
  forProvider:
    topic: my-topic
    ackDeadlineSeconds: 20
    retainAckedMessages: true
    messageRetentionDuration: 604800s
    expirationPolicy:
      ttl: 2592000s
    retryPolicy:
      minimumBackoff: 10s
      maximumBackoff: 600s
    deadLetterPolicy:
      deadLetterTopic: projects/your-project/topics/dead-letter
      maxDeliveryAttempts: 5
    filter: "attributes.event_type = \"user.created\""
    labels:
      environment: production
  providerConfigRef:
    name: gcp-provider

### Cloud Spanner Instance

apiVersion: spanner.gcp.crossplane.io/v1alpha1
kind: Instance
metadata:
  name: my-spanner
spec:
  forProvider:
    displayName: "Production Spanner Instance"
    config: projects/your-project/instanceConfigs/regional-us-central1
    nodeCount: 3
    labels:
      environment: production
  writeConnectionSecretToRef:
    name: my-spanner-conn
    namespace: crossplane-system
  providerConfigRef:
    name: gcp-provider

### Cloud Spanner Database

apiVersion: spanner.gcp.crossplane.io/v1alpha1
kind: Database
metadata:
  name: my-spanner-db
spec:
  forProvider:
    instanceRef:
      name: my-spanner
    ddl:
      - "CREATE TABLE Users (UserID INT64 NOT NULL, Name STRING(100), Email STRING(100)) PRIMARY KEY(UserID)"
      - "CREATE TABLE Orders (OrderID INT64 NOT NULL, UserID INT64 NOT NULL, OrderDate TIMESTAMP) PRIMARY KEY(OrderID)"
    versionRetentionPeriod: 1h
  writeConnectionSecretToRef:
    name: my-spanner-db-conn
    namespace: crossplane-system
  providerConfigRef:
    name: gcp-provider

## Using Resource References

GCP Crossplane providers support references to other resources instead of hardcoded values:

apiVersion: pubsub.gcp.crossplane.io/v1alpha1
kind: Subscription
metadata:
  name: my-subscription
spec:
  forProvider:
    topicRef:
      name: my-topic
    # ... other configuration
  providerConfigRef:
    name: gcp-provider

## GCP-Specific Best Practices

1. **Project ID**: The project ID is automatically injected from the provider configuration into each resource
   apiVersion: gcp.crossplane.io/v1beta1
   kind: ProviderConfig
   metadata:
     name: gcp-provider
   spec:
     projectID: your-gcp-project-id

2. **Use Labels**: Add consistent labels to all resources for better organization
   labels:
     environment: production
     team: platform
     costcenter: "123456"

3. **Regional Resources**: Deploy critical resources across multiple zones or regions when available
   availabilityType: REGIONAL

4. **IAM Integration**: Use least privilege principles when setting up the service account for Crossplane
   Assign only the IAM roles needed for the specific resources you plan to provision.

5. **Use References**: Link resources together using references instead of hardcoding names
   instanceRef:
     name: my-instance

6. **Security Settings**: Always configure security settings appropriately
   requireSsl: true
   privateClusterConfig:
     enablePrivateNodes: true

7. **Resource Isolation**: Use separate projects for different environments (dev, staging, prod)

## Troubleshooting GCP Resources

1. **Check Resource Status**: Use kubectl to check the current status
   kubectl describe gkecluster my-gke

2. **Check Events**: Look for events related to your resource
   kubectl get events | grep my-gke

3. **Provider Logs**: Check the GCP provider controller logs
   kubectl logs -n crossplane-system deployment/provider-gcp -c provider-gcp

4. **Common Issues**:
   - Service account missing required IAM permissions
   - Quota limits reached in GCP project
   - Regional availability for specific resource types
   - Resource naming conflicts with existing GCP resources

5. **GCP Console**: Verify the state of resources in the GCP Console

6. **Error Messages**: Pay attention to specific GCP error codes in the status
   kubectl get gkecluster my-gke -o jsonpath='{.status.conditions[?(@.type=="Ready")].message}'

For more detailed information, refer to the Crossplane GCP Provider Documentation.