
"""
Recursively extracts the text from a Google Doc.
"""
import os
from pathlib import Path
from typing import Optional,Any

import googleapiclient.discovery as discovery
from httplib2 import Http
from googleapiclient.discovery import build

from pydantic import BaseModel, root_validator, validator

# current working directory
cwd= os.getcwd()

service_account_key:Path= os.path.join( cwd,'.credentials', 'keys.json')
credentials_path:Path= os.path.join( cwd,'.credentials', 'credentials.json')

@validator("credentials_path")
def validate_credentials_path(cls, v: Any, **kwargs: Any) -> Any:
        """Validate that credentials_path exists."""
        if not v.exists():
            raise ValueError(f"credentials_path {v} does not exist")
        return v

def load_credentials(scopes:list[str], token_path:Optional[Path]=None )-> Any:
        """Load credentials from the credentials directory."""
        print(str(service_account_key))
        # Adapted from https://developers.google.com/drive/api/v3/quickstart/python
        try:
            from google.auth import default
            from google.auth.transport.requests import Request
            from google.oauth2 import service_account
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
        except ImportError:
            raise ImportError(
                "You must run "
                "`pip install --upgrade "
                "google-api-python-client google-auth-httplib2 "
                "google-auth-oauthlib` "
                "to use the Google Drive loader."
            )

        creds = None
        if Path(service_account_key).exists():
            print("found service key")
            return service_account.Credentials.from_service_account_file(
                str(service_account_key), scopes=scopes
            )
        else:
            print("not found service key")

        if token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), scopes)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            elif "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
                creds, project = default()
                creds = creds.with_scopes(scopes)
                # no need to write to file
                if creds:
                    return creds
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    str(credentials_path), scopes
                )
                creds = flow.run_local_server(port=0)
            with open(token_path, "w") as token:
                token.write(creds.to_json())

        return creds
