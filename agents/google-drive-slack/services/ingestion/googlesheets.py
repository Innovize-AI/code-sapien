import os
import re
from pathlib import Path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/spreadsheets.readonly"]

# The ID and range of a sample spreadsheet.
SAMPLE_SPREADSHEET_ID = "1KwlqM_FzUlcgGoI53KgQ9srEpEbF_5DiqBrY9dqOEXw"
SAMPLE_RANGE_NAME = "Class Data!A2:E"

cwd= os.getcwd()

service_account_key:Path= os.path.join( cwd,'.credentials', 'keys.json')

def _load_credentials():
        """Load credentials."""
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
                str(service_account_key), scopes=SCOPES
            )
        else:
            print("not found service key")

        # if token_path.exists():
        #     creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

        # if not creds or not creds.valid:
        #     if creds and creds.expired and creds.refresh_token:
        #         creds.refresh(Request())
        #     elif "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
        #         creds, project = default()
        #         creds = creds.with_scopes(SCOPES)
        #         # no need to write to file
        #         if creds:
        #             return creds
        #     else:
        #         flow = InstalledAppFlow.from_client_secrets_file(
        #             str(credentials_path), SCOPES
        #         )
        #         creds = flow.run_local_server(port=0)
        #     with open(token_path, "w") as token:
        #         token.write(creds.to_json())

        return creds


def get_google_sheets_data(spreadsheetId, creds):
  """Shows basic usage of the Sheets API.
  Prints values from a sample spreadsheet.
  """
#   creds = _load_credentials()
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
#   if os.path.exists("token.json"):
#     creds = Credentials.from_authorized_user_file("token.json", SCOPES)
#   # If there are no (valid) credentials available, let the user log in.
#   if not creds or not creds.valid:
#     if creds and creds.expired and creds.refresh_token:
#       creds.refresh(Request())
#     else:
#       flow = InstalledAppFlow.from_client_secrets_file(
#           "credentials.json", SCOPES
#       )
#       creds = flow.run_local_server(port=0)
#     # Save the credentials for the next run
#     with open("token.json", "w") as token:
#       token.write(creds.to_json())

  try:
    service = build("sheets", "v4", credentials=creds)

    # Call the Sheets API
    sheet_service = service.spreadsheets()
    sheet_metadata = sheet_service.get(spreadsheetId=spreadsheetId).execute()
    sheets = sheet_metadata.get('sheets')

    for sheet in sheets:
        if sheet['properties']['title']!='master':
            dataset= sheet_service.values().get(
                spreadsheetId=spreadsheetId,
                range=sheet['properties']['title'],
                majorDimension='ROWS'
            ).execute()
            print(dataset)
            
  except HttpError as err:
    print(err)

def convert_google_sheet_url(url):
    # Regular expression to match and capture the necessary part of the URL
    pattern = r'https://docs\.google\.com/spreadsheets/d/([a-zA-Z0-9-_]+)(/edit#gid=(\d+)|/edit.*)?'

    # Replace function to construct the new URL for CSV export
    # If gid is present in the URL, it includes it in the export URL, otherwise, it's omitted
    replacement = lambda m: f'https://docs.google.com/spreadsheets/d/{m.group(1)}/export?' + (f'gid={m.group(3)}&' if m.group(3) else '') + 'format=csv'

    # Replace using regex
    new_url = re.sub(pattern, replacement, url)

    return new_url