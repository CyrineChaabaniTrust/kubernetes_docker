# Crossplane AWS Resource Guide

## Introduction

This guide explains how to create Crossplane YAML manifests for AWS resources. Crossplane enables you to define AWS infrastructure using Kubernetes-style resources, bringing cloud-native infrastructure as code to your AWS deployments.

## AWS Provider Configuration

Before creating resources, you must configure the AWS provider:

apiVersion: aws.crossplane.io/v1beta1
kind: ProviderConfig
metadata:
  name: aws-provider
spec:
  credentials:
    source: Secret
    secretRef:
      namespace: crossplane-system
      name: aws-credentials
      key: credentials

The AWS credentials secret should be created as follows:

apiVersion: v1
kind: Secret
metadata:
  name: aws-credentials
  namespace: crossplane-system
type: Opaque
data:
  credentials: <base64-encoded AWS credentials file>

## AWS Resource Structure

AWS resources follow this basic structure:

apiVersion: <service>.aws.crossplane.io/<version>
kind: <ResourceType>
metadata:
  name: <resource-name>
spec:
  forProvider:
    region: <aws-region>
    # AWS-specific configuration
  writeConnectionSecretToRef:
    name: <connection-secret-name>
    namespace: <namespace>
  providerConfigRef:
    name: aws-provider

## Common AWS Resources

### S3 Bucket

apiVersion: storage.aws.crossplane.io/v1alpha1
kind: Bucket
metadata:
  name: my-bucket
spec:
  forProvider:
    region: us-west-2
    acl: private
    locationConstraint: us-west-2
    versioning: true
    tagging:
      tagSet:
        - key: Environment
          value: Production
        - key: Department
          value: Finance
    serverSideEncryptionConfiguration:
      rules:
        - applyServerSideEncryptionByDefault:
            sseAlgorithm: AES256
  writeConnectionSecretToRef:
    name: my-bucket-conn
    namespace: crossplane-system
  providerConfigRef:
    name: aws-provider

### RDS Instance

apiVersion: database.aws.crossplane.io/v1alpha1
kind: RDSInstance
metadata:
  name: my-db
spec:
  forProvider:
    region: us-east-1
    dbInstanceClass: db.t3.micro
    masterUsername: admin
    allocatedStorage: 20
    engine: mysql
    engineVersion: "8.0"
    skipFinalSnapshotBeforeDeletion: true
    publiclyAccessible: false
    vpcSecurityGroupIDRefs:
      - name: my-sg
    dbSubnetGroupNameRef:
      name: my-subnet-group
    tags:
      - key: Environment
        value: Production
  writeConnectionSecretToRef:
    name: my-db-conn
    namespace: crossplane-system
  providerConfigRef:
    name: aws-provider

### EKS Cluster

apiVersion: container.aws.crossplane.io/v1alpha1
kind: EKSCluster
metadata:
  name: my-eks
spec:
  forProvider:
    region: us-east-1
    version: "1.24"
    roleArnRef:
      name: eks-cluster-role
    resourcesVpcConfig:
      subnetIdRefs:
        - name: subnet-1
        - name: subnet-2
      endpointPrivateAccess: true
      endpointPublicAccess: true
    logging:
      clusterLogging:
        - types:
            - api
            - audit
            - authenticator
          enabled: true
  writeConnectionSecretToRef:
    name: my-eks-conn
    namespace: crossplane-system
  providerConfigRef:
    name: aws-provider

### EC2 Instance

apiVersion: compute.aws.crossplane.io/v1alpha1
kind: Instance
metadata:
  name: my-ec2
spec:
  forProvider:
    region: us-east-1
    instanceType: t2.micro
    imageId: ami-0c55b159cbfafe1f0
    subnetIdRef:
      name: my-subnet
    keyName: my-key-pair
    securityGroupRefs:
      - name: my-sg
    tags:
      - key: Name
        value: MyInstance
      - key: Environment
        value: Development
  writeConnectionSecretToRef:
    name: my-ec2-conn
    namespace: crossplane-system
  providerConfigRef:
    name: aws-provider

### IAM Role

apiVersion: iam.aws.crossplane.io/v1alpha1
kind: Role
metadata:
  name: my-role
spec:
  forProvider:
    assumeRolePolicyDocument: |
      {
        "Version": "2012-10-17",
        "Statement": [
          {
            "Effect": "Allow",
            "Principal": {
              "Service": "ec2.amazonaws.com"
            },
            "Action": "sts:AssumeRole"
          }
        ]
      }
    tags:
      - key: Environment
        value: Production
  providerConfigRef:
    name: aws-provider

## Using Resource References

AWS Crossplane providers support references to other resources instead of hardcoded values:

apiVersion: ec2.aws.crossplane.io/v1alpha1
kind: SecurityGroup
metadata:
  name: my-sg
spec:
  forProvider:
    region: us-east-1
    vpcIdRef:
      name: my-vpc
    groupName: web-sg
    description: "Web security group"
    ingress:
      - fromPort: 80
        toPort: 80
        ipProtocol: tcp
        ipRanges:
          - cidrIp: 0.0.0.0/0
            description: "HTTP from anywhere"
  providerConfigRef:
    name: aws-provider

## AWS-Specific Best Practices

1. **Always specify region**: Each AWS resource requires a region in the `forProvider` block
   forProvider:
     region: us-east-1

2. **Use managed policies when possible**: For IAM roles, reference AWS managed policies
   managedPolicyArns:
     - "arn:aws:iam::aws:policy/AmazonEKSClusterPolicy"

3. **Tag your resources**: Add consistent tags to all resources
   tags:
     - key: Environment
       value: Production
     - key: CostCenter
       value: "123456"

4. **Use references over hard-coded values**: Prefer `vpcIdRef` over `vpcId`

5. **Handle secrets properly**: Use `writeConnectionSecretToRef` to capture sensitive data

6. **Configure deletion policies**: Many resources support configuration for what happens during deletion
   skipFinalSnapshotBeforeDeletion: false
   finalDBSnapshotIdentifier: final-snapshot

## Troubleshooting AWS Resources

1. **Check Resource Status**: Use kubectl to check the current status
   kubectl describe bucket my-bucket

2. **Check Events**: Look for events related to your resource
   kubectl get events | grep my-bucket

3. **Provider Logs**: Check the AWS provider controller logs
   kubectl logs -n crossplane-system deployment/provider-aws -c provider-aws

4. **Common Issues**:
   - IAM permissions are insufficient
   - Region mismatch between resources that need to be in the same region
   - VPC or subnet configuration issues
   - Resource name conflicts with existing AWS resources

5. **AWS Console**: Verify the state of resources in the AWS Console

For more detailed information, refer to the Crossplane AWS Provider Documentation.