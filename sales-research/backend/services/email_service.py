import json
from datetime import date, datetime
from typing import List, Optional, Dict, Any
from imap_tools import MailBox, AND
from pydantic import BaseModel

class EmailConfig(BaseModel):
    imap_server: str
    email_user: str
    email_password: str
    imap_port: int = 993

class EmailMessage(BaseModel):
    subject: str
    sender: str
    to: List[str]
    date: datetime
    body: str
    flags: List[str]

class EmailService:
    def __init__(self, config: EmailConfig):
        self.config = config

    def fetch_email_history(self, target_email: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch emails exchanged with the target_email (files sent to or received from).
        This is a simplified version. authentic history often requires checking references/message-ids.
        For MVP, we fetch emails WHERE (FROM = target) OR (TO = target).
        """
        history = []
        
        try:
            with MailBox(self.config.imap_server).login(self.config.email_user, self.config.email_password) as mailbox:
                # 1. Fetch emails FROM the target
                # Note: This depends on the folder structure. Standard is INBOX.
                # Query: FROM target_email
                try:
                    for msg in mailbox.fetch(AND(from_=target_email), limit=limit, reverse=True):
                        history.append(self._parse_msg(msg, "received"))
                except Exception as e:
                    print(f"Error fetching received emails: {e}")

                # 2. Fetch emails TO the target (usually in Sent items)
                # We need to find the sent folder name (Sent, Sent Items, etc.)
                sent_folder = "Sent" # Default guess
                for folder in mailbox.folder.list():
                    # FolderInfo has .name attribute, not dictionary access
                    if "sent" in folder.name.lower():
                        sent_folder = folder.name
                        break
                
                try:
                    mailbox.folder.set(sent_folder)
                    for msg in mailbox.fetch(AND(to=target_email), limit=limit, reverse=True):
                         history.append(self._parse_msg(msg, "sent"))
                except Exception as e:
                    print(f"Error fetching sent emails from {sent_folder}: {e}")

        except Exception as e:
            print(f"IMAP Connection Error: {e}")
            return []

        # Sort by date
        history.sort(key=lambda x: x['date'], reverse=True)
        return history[:limit]

    def _parse_msg(self, msg, direction: str) -> Dict[str, Any]:
        return {
            "id": msg.uid,
            "subject": msg.subject,
            "from": msg.from_,
            "to": msg.to,
            "date": msg.date.isoformat() if msg.date else None,
            "text": msg.text or msg.html,
            "direction": direction # 'sent' or 'received'
        }
