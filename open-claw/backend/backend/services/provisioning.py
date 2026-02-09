from sqlalchemy.ext.asyncio import AsyncSession
from ..models import Instance, User, ProviderEnum, InstanceStatus
from ..providers.base import CloudProvider
from ..providers.digitalocean import DigitalOceanProvider
from ..providers.aws import AWSProvider
from ..providers.gcp import GCPProvider
import os

class ProvisioningService:
    def __init__(self, db: AsyncSession):
        self.db = db

    def _get_provider(self, provider_name: ProviderEnum) -> CloudProvider:
        if provider_name == ProviderEnum.digitalocean:
            return DigitalOceanProvider()
        elif provider_name == ProviderEnum.aws:
            return AWSProvider()
        elif provider_name == ProviderEnum.gcp:
            return GCPProvider()
        else:
            raise ValueError(f"Unknown provider: {provider_name}")

    async def provision_instance(self, user_id: str, provider_name: ProviderEnum, region: str, size: str):
        # 1. Create DB record (pending)
        instance = Instance(
            user_id=user_id,
            provider=provider_name,
            region=region,
            status=InstanceStatus.provisioning
        )
        self.db.add(instance)
        await self.db.commit()
        await self.db.refresh(instance)

        try:
            # 2. Call Cloud Provider
            provider = self._get_provider(provider_name)
            
            # Using a fixed image mapping for now
            # In production this should be a config map
            image = "ubuntu-20-04-x64" # DO default
            if provider_name == ProviderEnum.aws:
                 image = "ami-0c55b159cbfafe1f0" # AWS default (example)
            elif provider_name == ProviderEnum.gcp:
                 image = "projects/debian-cloud/global/images/family/debian-11" # GCP default
            
            # We run this in a threadpool since provider creation is sync/blocking
            # FastAPI's background tasks or a proper queue is better, but this works for async def
            import asyncio
            from functools import partial
            
            loop = asyncio.get_running_loop()
            result = await loop.run_in_executor(
                None, 
                partial(provider.create_instance, 
                        name=f"open-claw-{instance.id}", 
                        region=region, 
                        image=image, 
                        size=size)
            )

            # 3. Update DB record
            instance.provider_instance_id = result.get("id")
            instance.ip_address = result.get("ip_address")
            instance.meta = result.get("meta")
            # If IP is missing (common with async provisioning), we might need to poll later
            # For now, we set status to provisioning or active based on result
            instance.status = InstanceStatus.active if result.get("ip_address") else InstanceStatus.provisioning
            
            await self.db.commit()
            return instance
            
        except Exception as e:
            instance.status = InstanceStatus.terminated
            instance.meta = {"error": str(e)}
            await self.db.commit()
            raise e
