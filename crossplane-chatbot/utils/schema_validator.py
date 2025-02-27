import os
import json
import logging
import jsonschema
from jsonschema import validate

logger = logging.getLogger(__name__)

AWS_SCHEMA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'aws_schemas')
AZURE_SCHEMA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data', 'azure_schemas')

def load_schema(provider, resource_type):
    """Load a JSON schema for a specific resource type"""
    if provider == 'aws':
        schema_path = os.path.join(AWS_SCHEMA_DIR, f"{resource_type}.json")
    elif provider == 'azure':
        schema_path = os.path.join(AZURE_SCHEMA_DIR, f"{resource_type}.json")
    else:
        logger.error(f"Unsupported provider: {provider}")
        return None
    
    try:
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                return json.load(f)
        else:
            logger.warning(f"No schema file found for {provider} {resource_type} at {schema_path}")
            return None
    except Exception as e:
        logger.error(f"Error loading schema for {provider} {resource_type}: {str(e)}")
        return None

def validate_aws_resource(resource_type, data):
    """Validate AWS resource data against its schema"""
    schema = load_schema('aws', resource_type)
    if not schema:
        return []  
    
    try:
        validate(instance=data, schema=schema)
        return []  
    except jsonschema.exceptions.ValidationError as e:
        return [f"Validation error: {e.message}"]
    except Exception as e:
        logger.error(f"Unexpected error during AWS validation: {str(e)}")
        return [f"Unexpected validation error: {str(e)}"]

def validate_azure_resource(resource_type, data):
    """Validate Azure resource data against its schema"""
    schema = load_schema('azure', resource_type)
    if not schema:
        return []  
    try:
        validate(instance=data, schema=schema)
        return []  
    except jsonschema.exceptions.ValidationError as e:
        return [f"Validation error: {e.message}"]
    except Exception as e:
        logger.error(f"Unexpected error during Azure validation: {str(e)}")
        return [f"Unexpected validation error: {str(e)}"]

def validate_yaml(yaml_str):
    """Validate a YAML string for syntactic correctness"""
    try:
        import yaml
        yaml.safe_load(yaml_str)
        return True, None
    except yaml.YAMLError as e:
        return False, f"YAML validation error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during YAML validation: {str(e)}")
        return False, f"Unexpected YAML validation error: {str(e)}"