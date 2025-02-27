import logging
from generators.aws_generator import AWSManifestGenerator
from generators.azure_generator import AzureManifestGenerator

logger = logging.getLogger(__name__)

class ManifestGenerator:
    """Base class for generating Crossplane YAML manifests"""
    
    def __init__(self):
        self.generators = {
            'aws': AWSManifestGenerator(),
            'azure': AzureManifestGenerator()
        }
    
    def generate_manifest(self, cloud_provider, resource_type, collected_data):
        """Generate a Crossplane YAML manifest based on the cloud provider and resource type"""
        logger.info(f"Generating manifest for {cloud_provider} {resource_type}")
        
        if cloud_provider not in self.generators:
            logger.error(f"Unsupported cloud provider: {cloud_provider}")
            return f"Sorry, {cloud_provider} is not supported yet."
        
        return self.generators[cloud_provider].generate_manifest(resource_type, collected_data)