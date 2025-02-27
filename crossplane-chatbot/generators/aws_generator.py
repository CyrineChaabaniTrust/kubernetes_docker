import logging
import yaml
from utils.schema_validator import validate_aws_resource

logger = logging.getLogger(__name__)

class AWSManifestGenerator:
    """Generator for AWS Crossplane manifests"""
    
    def generate_manifest(self, resource_type, data):
        """Generate a YAML manifest for an AWS resource"""
        validation_errors = validate_aws_resource(resource_type, data)
        if validation_errors:
            logger.error(f"Validation errors for AWS {resource_type}: {validation_errors}")
            error_msg = "\n".join(validation_errors)
            return f"There were validation errors with your inputs:\n{error_msg}\nPlease try again."
        
        if resource_type == 's3':
            return self.generate_s3_manifest(data)
        elif resource_type == 'rds':
            return self.generate_rds_manifest(data)
        elif resource_type == 'eks':
            return self.generate_eks_manifest(data)
        elif resource_type == 'ec2':
            return self.generate_ec2_manifest(data)
        elif resource_type == 'iam':
            return self.generate_iam_manifest(data)
        else:
            logger.error(f"Unsupported AWS resource type: {resource_type}")
            return f"Sorry, {resource_type} is not supported yet."
    
    def generate_s3_manifest(self, data):
        """Generate a YAML manifest for an S3 bucket"""
        manifest = {
            "apiVersion": "storage.aws.crossplane.io/v1alpha1",
            "kind": "Bucket",
            "metadata": {
                "name": data['bucket_name']
            },
            "spec": {
                "forProvider": {
                    "region": data['region'],
                    "acl": data['acl']
                },
                "providerConfigRef": {
                    "name": "aws-provider"
                }
            }
        }
        
        # Add optional fields if they exist
        if 'versioning' in data and data['versioning'].lower() == 'yes':
            manifest['spec']['forProvider']['versioning'] = True
        
        if 'encryption' in data and data['encryption'].lower() == 'yes':
            manifest['spec']['forProvider']['serverSideEncryptionConfiguration'] = {
                "rules": [
                    {
                        "applyServerSideEncryptionByDefault": {
                            "sseAlgorithm": "AES256"
                        }
                    }
                ]
            }
        
        if 'tags' in data and data['tags']:
            tag_pairs = data['tags'].split(',')
            tag_set = []
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tag_set.append({"key": key.strip(), "value": value.strip()})
            
            if tag_set:
                manifest['spec']['forProvider']['tagging'] = {
                    "tagSet": tag_set
                }
        
        manifest['spec']['writeConnectionSecretToRef'] = {
            "name": f"{data['bucket_name']}-conn",
            "namespace": "crossplane-system"
        }
        
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def generate_rds_manifest(self, data):
        """Generate a YAML manifest for an RDS instance"""
        manifest = {
            "apiVersion": "database.aws.crossplane.io/v1alpha1",
            "kind": "RDSInstance",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "region": data['region'],
                    "dbInstanceClass": data['instance_class'],
                    "masterUsername": data['master_username'],
                    "allocatedStorage": int(data['allocated_storage']),
                    "engine": data['engine'],
                    "skipFinalSnapshotBeforeDeletion": True
                },
                "providerConfigRef": {
                    "name": "aws-provider"
                }
            }
        }
        
        if 'engine_version' in data and data['engine_version']:
            manifest['spec']['forProvider']['engineVersion'] = data['engine_version']
        
        if 'storage_type' in data and data['storage_type']:
            manifest['spec']['forProvider']['storageType'] = data['storage_type']
        
        if 'password_secret_name' in data and data['password_secret_name']:
            manifest['spec']['forProvider']['masterPasswordSecretRef'] = {
                "key": "password",
                "name": data['password_secret_name'],
                "namespace": "crossplane-system"
            }
        
        manifest['spec']['writeConnectionSecretToRef'] = {
            "name": f"{data['name']}-conn",
            "namespace": "crossplane-system"
        }
        
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def generate_eks_manifest(self, data):
        """Generate a YAML manifest for an EKS cluster"""
        manifest = {
            "apiVersion": "container.aws.crossplane.io/v1alpha1",
            "kind": "EKSCluster",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "region": data['region'],
                    "version": data['version'],
                    "roleArn": data['role_arn']
                },
                "providerConfigRef": {
                    "name": "aws-provider"
                }
            }
        }
        
        if 'subnet_ids' in data and data['subnet_ids']:
            subnet_ids = [s.strip() for s in data['subnet_ids'].split(',')]
            manifest['spec']['forProvider']['subnetIds'] = subnet_ids
        
        if 'tags' in data and data['tags']:
            tag_pairs = data['tags'].split(',')
            tags = {}
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tags[key.strip()] = value.strip()
            
            if tags:
                manifest['spec']['forProvider']['tags'] = tags
        
        manifest['spec']['writeConnectionSecretToRef'] = {
            "name": f"{data['name']}-conn",
            "namespace": "crossplane-system"
        }
        
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def generate_ec2_manifest(self, data):
        """Generate a YAML manifest for an EC2 instance"""
        manifest = {
            "apiVersion": "compute.aws.crossplane.io/v1alpha1",
            "kind": "Instance",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "region": data['region'],
                    "instanceType": data['instance_type'],
                    "imageId": data['ami']
                },
                "providerConfigRef": {
                    "name": "aws-provider"
                }
            }
        }
        
        if 'key_name' in data and data['key_name']:
            manifest['spec']['forProvider']['keyName'] = data['key_name']
        
        if 'subnet' in data and data['subnet']:
            manifest['spec']['forProvider']['subnetId'] = data['subnet']
        
        if 'security_groups' in data and data['security_groups']:
            sec_groups = [s.strip() for s in data['security_groups'].split(',')]
            manifest['spec']['forProvider']['securityGroupIds'] = sec_groups
        
        if 'tags' in data and data['tags']:
            tag_pairs = data['tags'].split(',')
            tags = {}
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tags[key.strip()] = value.strip()
            
            if tags:
                manifest['spec']['forProvider']['tags'] = tags
        
        manifest['spec']['writeConnectionSecretToRef'] = {
            "name": f"{data['name']}-conn",
            "namespace": "crossplane-system"
        }
        
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def generate_iam_manifest(self, data):
        """Generate a YAML manifest for an IAM role"""
        manifest = {
            "apiVersion": "identity.aws.crossplane.io/v1alpha1",
            "kind": "IAMRole",
            "metadata": {
                "name": data['name']
            },
            "spec": {
                "forProvider": {
                    "assumeRolePolicyDocument": self._generate_assume_role_policy(data['assume_role_policy'])
                },
                "providerConfigRef": {
                    "name": "aws-provider"
                }
            }
        }
        
        if 'managed_policies' in data and data['managed_policies']:
            policies = [p.strip() for p in data['managed_policies'].split(',')]
            manifest['spec']['forProvider']['managedPolicyArns'] = policies
        
        if 'tags' in data and data['tags']:
            tag_pairs = data['tags'].split(',')
            tags = {}
            for pair in tag_pairs:
                if '=' in pair:
                    key, value = pair.split('=', 1)
                    tags[key.strip()] = value.strip()
            
            if tags:
                manifest['spec']['forProvider']['tags'] = tags
        
        yaml_str = yaml.dump(manifest, default_flow_style=False, sort_keys=False)
        return yaml_str
    
    def _generate_assume_role_policy(self, service):
        """Generate an assume role policy document for a service"""
        service_map = {
            'ec2': 'ec2.amazonaws.com',
            'lambda': 'lambda.amazonaws.com',
            'eks': 'eks.amazonaws.com',
            'ecs-tasks': 'ecs-tasks.amazonaws.com',
            'ecs': 'ecs.amazonaws.com',
            'sagemaker': 'sagemaker.amazonaws.com',
            'cloudwatch': 'cloudwatch.amazonaws.com'
        }
        
        service_principal = service_map.get(service.lower(), service)
        
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {
                        "Service": service_principal
                    },
                    "Action": "sts:AssumeRole"
                }
            ]
        }
        
        import json
        return json.dumps(policy)