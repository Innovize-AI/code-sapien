from google.cloud import compute_v1
import os
from typing import Dict, List, Optional
from .base import CloudProvider
from dotenv import load_dotenv

load_dotenv()

class GCPProvider(CloudProvider):
    def __init__(self):
        self.project_id = os.getenv("GCP_PROJECT_ID")
        self.zone = os.getenv("GCP_ZONE", "us-central1-a")
        # Ensure GOOGLE_APPLICATION_CREDENTIALS env var is set or credentials are passed
        
    def create_instance(self, name: str, region: str, image: str, size: str, ssh_key_id: Optional[str] = None) -> Dict:
        # Region in GCP needs to be mapping to zone
        zone = f"{region}-a" # Simplified logic
        
        instance_client = compute_v1.InstancesClient()
        
        # User Data
        startup_script = """#!/bin/bash
        apt-get update
        apt-get install -y docker.io
        docker run -d -p 80:8000 ghcr.io/open-claw/open-claw:latest
        """

        instance = compute_v1.Instance()
        instance.name = name
        instance.machine_type = f"zones/{zone}/machineTypes/{size}"
        
        # Disk config
        disk = compute_v1.AttachedDisk()
        initialize_params = compute_v1.AttachedDiskInitializeParams()
        initialize_params.source_image = image # e.g. "projects/debian-cloud/global/images/family/debian-11"
        initialize_params.disk_size_gb = 10
        disk.initialize_params = initialize_params
        disk.boot = True
        disk.auto_delete = True
        instance.disks = [disk]
        
        # Network interface
        network_interface = compute_v1.NetworkInterface()
        network_interface.name = "global/networks/default"
        config = compute_v1.AccessConfig()
        config.name = "External NAT"
        config.type_ = "ONE_TO_ONE_NAT"
        network_interface.access_configs = [config]
        instance.network_interfaces = [network_interface]
        
        # Metadata
        metadata = compute_v1.Metadata()
        metadata.items = [{"key": "startup-script", "value": startup_script}]
        instance.metadata = metadata

        operation = instance_client.insert(project=self.project_id, zone=zone, instance_resource=instance)
        
        # We can wait for operation but that blocks. For now return operation name/id
        return {
            "id": name, # GCP uses name as ID effectively within a zone
            "status": "provisioning",
            "meta": {"operation_name": operation.name, "zone": zone}
        }

    def get_instance_status(self, instance_id: str) -> str:
        # instance_id here is name
        instance_client = compute_v1.InstancesClient()
        try:
            instance = instance_client.get(project=self.project_id, zone=self.zone, instance=instance_id)
            return instance.status
        except:
            return "unknown"

    def delete_instance(self, instance_id: str) -> bool:
        instance_client = compute_v1.InstancesClient()
        try:
            instance_client.delete(project=self.project_id, zone=self.zone, instance=instance_id)
            return True
        except:
            return False

    def list_regions(self) -> List[str]:
        return ["us-central1", "europe-west1", "asia-east1"]

    def list_sizes(self) -> List[str]:
        return ["e2-micro", "e2-small", "e2-medium"]
