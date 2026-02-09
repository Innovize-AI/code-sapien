import boto3
import os
from typing import Dict, List, Optional
from .base import CloudProvider
from dotenv import load_dotenv

load_dotenv()

class AWSProvider(CloudProvider):
    def __init__(self):
        self.region = os.getenv("AWS_REGION", "us-east-1")
        self.ec2 = boto3.client(
            'ec2',
            region_name=self.region,
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY")
        )

    def create_instance(self, name: str, region: str, image: str, size: str, ssh_key_id: Optional[str] = None) -> Dict:
        # User Data to install Docker and run Open Claw
        user_data = """#!/bin/bash
        yum update -y
        amazon-linux-extras install docker
        service docker start
        usermod -a -G docker ec2-user
        docker run -d -p 80:8000 ghcr.io/open-claw/open-claw:latest
        """
        
        run_args = {
            'ImageId': image, # e.g., ami-0c55b159cbfafe1f0 (Amazon Linux 2)
            'InstanceType': size, # e.g., t2.micro
            'MinCount': 1,
            'MaxCount': 1,
            'UserData': user_data,
            'TagSpecifications': [
                {
                    'ResourceType': 'instance',
                    'Tags': [{'Key': 'Name', 'Value': name}]
                },
            ]
        }
        
        if ssh_key_id:
            run_args['KeyName'] = ssh_key_id

        response = self.ec2.run_instances(**run_args)
        instance = response['Instances'][0]
        
        return {
            "id": instance['InstanceId'],
            "ip_address": instance.get('PublicIpAddress'), # Might not be available immediately
            "status": instance['State']['Name'],
            "meta": {"instance_id": instance['InstanceId']}
        }

    def get_instance_status(self, instance_id: str) -> str:
        try:
            response = self.ec2.describe_instances(InstanceIds=[instance_id])
            if not response['Reservations']:
                return "terminated"
            return response['Reservations'][0]['Instances'][0]['State']['Name']
        except:
            return "unknown"

    def delete_instance(self, instance_id: str) -> bool:
        try:
            self.ec2.terminate_instances(InstanceIds=[instance_id])
            return True
        except:
            return False

    def list_regions(self) -> List[str]:
        response = self.ec2.describe_regions()
        return [r['RegionName'] for r in response['Regions']]

    def list_sizes(self) -> List[str]:
        return ["t2.micro", "t3.micro", "t3.small", "m5.large"]
