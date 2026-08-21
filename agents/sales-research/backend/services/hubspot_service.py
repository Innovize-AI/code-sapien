import os
import logging

logger = logging.getLogger(__name__)
import httpx
from typing import List, Dict, Any
from datetime import datetime, timedelta

class HubspotService:
    def __init__(self, access_token: str):
        self.access_token = access_token
        self.base_url = "https://api.hubapi.com"
        self.headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }

    async def get_recent_deals(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Fetch deals modified in the last N days.
        """
        endpoint = f"{self.base_url}/crm/v3/objects/deals/search"
        since_date = (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z"
        
        payload = {
            "filterGroups": [
                {
                    "filters": [
                        {
                            "propertyName": "hs_lastmodifieddate",
                            "operator": "GTE",
                            "value": since_date
                        }
                    ]
                }
            ],
            "properties": ["dealname", "dealstage", "amount", "closed_lost_reason", "hs_lastmodifieddate"],
            "limit": 100
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json().get("results", [])

    async def get_deal_contacts(self, deal_id: str) -> List[Dict[str, Any]]:
        """
        Get contacts associated with a deal.
        """
        endpoint = f"{self.base_url}/crm/v3/objects/deals/{deal_id}/associations/contacts"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=self.headers)
            response.raise_for_status()
            associations = response.json().get("results", [])
            
            contacts = []
            for assoc in associations:
                contact_info = await self.get_contact(assoc["id"])
                if contact_info:
                    contacts.append(contact_info)
            return contacts

    async def get_contact(self, contact_id: str) -> Dict[str, Any]:
        """
        Fetch contact details.
        """
        endpoint = f"{self.base_url}/crm/v3/objects/contacts/{contact_id}"
        params = {
            "properties": "email,firstname,lastname,linkedin_url,jobtitle,company"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=self.headers, params=params)
            if response.status_code == 404:
                return None
            response.raise_for_status()
            return response.json()

    async def push_note(self, object_type: str, object_id: str, content: str):
        """
        Push a note to a contact or company.
        """
        endpoint = f"{self.base_url}/crm/v3/objects/notes"
        payload = {
            "properties": {
                "hs_note_body": content,
                "hs_timestamp": datetime.utcnow().isoformat() + "Z"
            },
            "associations": [
                {
                    "to": {"id": object_id},
                    "types": [
                        {
                            "associationCategory": "HUBSPOT_DEFINED",
                            "associationTypeId": 202 if object_type == "contact" else 204 # Note to Contact or Note to Company
                        }
                    ]
                }
            ]
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(endpoint, headers=self.headers, json=payload)
            response.raise_for_status()
            return response.json()

    async def get_web_visits(self, days: int = 1) -> List[Dict[str, Any]]:
        """
        Fetch recent website visits using the Events API.
        Note: Requires specific HubSpot scopes and tracking code.
        """
        # HubSpot Events API (v3)
        endpoint = f"{self.base_url}/events/v3/events"
        params = {
            "occurredAfter": (datetime.utcnow() - timedelta(days=days)).isoformat() + "Z",
            "eventType": "DEPRECATED_PAGE_VIEW" # Or use custom events if configured
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(endpoint, headers=self.headers, params=params)
            # This is a placeholder as the Events API might differ based on HubSpot tier
            if response.status_code != 200:
                logger.info(f"Web Visits API Error: {response.text}")
                return []
            return response.json().get("results", [])
