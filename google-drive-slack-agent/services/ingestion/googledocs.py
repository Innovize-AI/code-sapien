# Copyright 2019 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Recursively extracts the text from a Google Doc.
"""
import os
import googleapiclient.discovery as discovery
from httplib2 import Http
from googleapiclient.discovery import build
from pathlib import Path
# from oauth2client import client
# from oauth2client import file
# from oauth2client import tools

SCOPES = ['https://www.googleapis.com/auth/documents']
DISCOVERY_DOC = 'https://docs.googleapis.com/$discovery/rest?version=v1'
DOCUMENT_ID = '1h1dVnclOrZ35JSC3xZXhqu0Zu9xXeNuNQoRauW9K0ek'

cwd= os.getcwd()

service_account_key:Path= os.path.join( cwd,'.credentials', 'keys.json')


# def _load_credentials():
#         """Load credentials."""
#         print(str(service_account_key))
#         # Adapted from https://developers.google.com/drive/api/v3/quickstart/python
#         try:
#             from google.auth import default
#             from google.auth.transport.requests import Request
#             from google.oauth2 import service_account
#             from google.oauth2.credentials import Credentials
#             from google_auth_oauthlib.flow import InstalledAppFlow
#         except ImportError:
#             raise ImportError(
#                 "You must run "
#                 "`pip install --upgrade "
#                 "google-api-python-client google-auth-httplib2 "
#                 "google-auth-oauthlib` "
#                 "to use the Google Drive loader."
#             )

#         creds = None
#         if Path(service_account_key).exists():
#             print("found service key")
#             return service_account.Credentials.from_service_account_file(
#                 str(service_account_key), scopes=SCOPES
#             )
#         else:
#             print("not found service key")

#         # if token_path.exists():
#         #     creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)

#         # if not creds or not creds.valid:
#         #     if creds and creds.expired and creds.refresh_token:
#         #         creds.refresh(Request())
#         #     elif "GOOGLE_APPLICATION_CREDENTIALS" not in os.environ:
#         #         creds, project = default()
#         #         creds = creds.with_scopes(SCOPES)
#         #         # no need to write to file
#         #         if creds:
#         #             return creds
#         #     else:
#         #         flow = InstalledAppFlow.from_client_secrets_file(
#         #             str(credentials_path), SCOPES
#         #         )
#         #         creds = flow.run_local_server(port=0)
#         #     with open(token_path, "w") as token:
#         #         token.write(creds.to_json())

#         return creds

def read_paragraph_element(element):
    """Returns the text in the given ParagraphElement.

        Args:
            element: a ParagraphElement from a Google Doc.
    """
    text_run = element.get('textRun')
    if not text_run:
        return ''
    return text_run.get('content')


def read_structural_elements(elements):
    """Recurses through a list of Structural Elements to read a document's text where text may be
        in nested elements.

        Args:
            elements: a list of Structural Elements.
    """
    text = ''
    for value in elements:
        if 'paragraph' in value:
            elements = value.get('paragraph').get('elements')
            for elem in elements:
                text += read_paragraph_element(elem)
        elif 'table' in value:
            # The text in table cells are in nested Structural Elements and tables may be
            # nested.
            table = value.get('table')
            for row in table.get('tableRows'):
                cells = row.get('tableCells')
                for cell in cells:
                    text += read_structural_elements(cell.get('content'))
        elif 'tableOfContents' in value:
            # The text in the TOC is also in a Structural Element.
            toc = value.get('tableOfContents')
            text += read_structural_elements(toc.get('content'))
    return text


def load_data_from_document_id(documentID,creds)->str:
    """Uses the Docs API to print out the text of a document."""
    # print(service_account_key)
    # http = credentials.authorize(Http())
    service = build('docs', 'v1', credentials=creds)
    doc = service.documents().get(documentId=documentID).execute()
    doc_content = doc.get('body').get('content')
    return read_structural_elements(doc_content)