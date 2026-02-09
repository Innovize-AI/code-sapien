import os
import digitalocean
from typing import Dict, List, Optional
from .base import CloudProvider
from dotenv import load_dotenv

load_dotenv()

class DigitalOceanProvider(CloudProvider):
    def __init__(self):
        self.token = os.getenv("DO_TOKEN")
        if not self.token:
             # In production we might want to log a warning or raise an error if critical
             print("Warning: DO_TOKEN not set")
        self.manager = digitalocean.Manager(token=self.token)

    def create_instance(self, name: str, region: str, image: str, size: str, ssh_key_id: Optional[str] = None) -> Dict:
        keys = []
        if ssh_key_id:
             keys.append(digitalocean.SSHKey(id=ssh_key_id))
        
        # User Data to install Docker and run Open Claw (simplified)
        user_data = """#!/bin/bash
        apt-get update
        apt-get install -y docker.io
        docker run -d -p 80:8000 ghcr.io/open-claw/open-claw:latest
        """

        droplet = digitalocean.Droplet(token=self.token,
                                       name=name,
                                       region=region,
                                       image=image,
                                       size_slug=size,
                                       ssh_keys=keys,
                                       user_data=user_data,
                                       backups=False)
        droplet.create()
        return {
            "id": str(droplet.id),
            "ip_address": droplet.ip_address,
            "status": droplet.status,
            "meta": {"droplet_id": droplet.id}
        }
    
    def get_instance_status(self, instance_id: str) -> str:
        try:
            droplet = self.manager.get_droplet(instance_id)
            return droplet.status
        except Exception as e:
            return "unknown"
        
    def delete_instance(self, instance_id: str) -> bool:
        try:
            droplet = self.manager.get_droplet(instance_id)
            droplet.destroy()
            return True
        except:
            return False
        
    def list_regions(self) -> List[str]:
         return ["nyc1", "sfo2", "fra1", "lon1"]

    def list_sizes(self) -> List[str]:
         return ["s-1vcpu-1gb", "s-1vcpu-2gb", "s-2vcpu-2gb"]
