from abc import ABC, abstractmethod
from typing import Optional, Dict, List

class CloudProvider(ABC):
    @abstractmethod
    def create_instance(self, name: str, region: str, image: str, size: str, ssh_key_id: Optional[str] = None) -> Dict:
        """
        Creates a new instance.
        Returns a dict with 'id', 'ip_address', 'status', 'meta'.
        """
        pass

    @abstractmethod
    def get_instance_status(self, instance_id: str) -> str:
        """
        Returns the status string (e.g. 'active', 'provisioning').
        """
        pass

    @abstractmethod
    def delete_instance(self, instance_id: str) -> bool:
        """
        Deletes the instance.
        """
        pass
        
    @abstractmethod
    def list_regions(self) -> List[str]:
        pass
        
    @abstractmethod
    def list_sizes(self) -> List[str]:
        pass
