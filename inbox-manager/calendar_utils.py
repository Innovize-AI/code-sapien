from pydantic import BaseModel, Field

class GetCalendarEventsSchema(BaseModel):
    # https://developers.google.com/calendar/api/v3/reference/events/list
    start_datetime: str = Field(
        #default=datetime.now().strftime('%Y-%m-%dT%H:%M:%S'),
        description=(
            " The start datetime for the event in the following format: "
            ' YYYY-MM-DDTHH:MM:SS±HH:MM, where "T" separates the date and time '
            " components, "
            ' For example: "2023-06-09T10:30:00" represents June 9th, '
            " 2023, at 10:30 AM"
            "Do not include timezone info as it will be automatically processed."
        )
    )
    end_datetime: str = Field(
        #default=(datetime.now() + timedelta(days=7)).strftime('%Y-%m-%dT%H:%M:%S'),
        description=(
            " The end datetime for the event in the following format: "
            ' YYYY-MM-DDTHH:MM:SS, where "T" separates the date and time '
            " components, "
            ' For example: "2023-06-09T10:30:00" represents June 9th, '
            " 2023, at 10:30 AM"
            "Do not include timezone info as it will be automatically processed."
        )
    )
    max_results: int = Field(
        default=10,
        description="The maximum number of results to return.",
    )
    timezone: str = Field(
        default="Asia/Kolkata",
        description="The timezone in TZ Database Name format, e.g. 'Asia/Kolkata'"
    )    

import datetime
import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import pytz
import sys
from pathlib import Path

from google.auth import default
from google.oauth2 import service_account

tz = pytz.timezone('Asia/Kolkata')  # timezone to use
START_HOUR = 10  # start time (24 hour time) of availability period
END_HOUR = 20  # end time (24 hour time) of availability period
CALENDAR_IDS = ['primary',"admin@innovizeai.com"]  # Google calendars to draw from
MIN_TIME_INTERVAL_LENGTH_IN_MINUTES = 30  # Minimum interval length
MAX_SLOTS=10
CREDENTIALS_NAME_DOWNLOADED_FROM_GOOGLE = 'keys.json'  # Credentials filename
NO_MEETING_DAYS = ['WEDNESDAY','Saturday', 'Sunday']  # Days to skip

now = datetime.datetime.now(tz)  # Current time in the same timezone

SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def load_credentials():
    cwd= os.getcwd()
    service_account_key:Path= os.path.join("d:\innovizeai\code-sapien\inbox-manager",'.credentials', 'keys.json') # temporary
    print("service account key path" , service_account_key)

    if os.path.exists(service_account_key):
        print("found service")
        return service_account.Credentials.from_service_account_file(
            str(service_account_key), scopes=SCOPES
        )

def get_calendar_availabilty(start_time, end_time):
    creds = None
    creds= load_credentials()
    # if (not creds) or (not creds.valid) or (creds and creds.expired and creds.refresh_token):
    #     flow = InstalledAppFlow.from_client_secrets_file(
    #         service_account_key, SCOPES)
    #     creds = flow.run_local_server(port=0)
    #     with open(service_account_key, 'w') as token:
    #         token.write(creds.to_json())

    try:
        service = build('calendar', 'v3', credentials=creds)
        timeMin = tz.localize(datetime.datetime.strptime(start_time, "%Y-%m-%d")).replace(hour=START_HOUR)
        timeMax = tz.localize(datetime.datetime.strptime(end_time, "%Y-%m-%d")).replace(hour=END_HOUR)
        print("scopes", SCOPES)
        print("creds", creds.service_account_email)
        print("start_time", (timeMin - datetime.timedelta(days=1)).isoformat())
        print("end_time", (timeMax + datetime.timedelta(days=1)).isoformat())
        all_events = []
        for calendar_id in CALENDAR_IDS:
            events_result = service.events().list(
                calendarId=calendar_id,
                timeMin=(timeMin - datetime.timedelta(days=1)).isoformat(),
                timeMax=(timeMax + datetime.timedelta(days=1)).isoformat(),
                singleEvents=True,
                orderBy='startTime').execute()
            all_events = all_events + events_result.get('items', [])

        print("all events" , all_events)
       # Parse busy intervals from events
        unified_busy_list = []
        parse_string = "%Y-%m-%dT%H:%M:%S%z"
        for event in all_events:
            if 'dateTime' not in event['start']:
                continue
            unified_busy_list.append({
                'start': datetime.datetime.strptime(event['start']['dateTime'], parse_string),
                'end': datetime.datetime.strptime(event['end']['dateTime'], parse_string)
            })
        unified_busy_list = sorted(unified_busy_list, key=lambda x: x['start'])

        # Generate candidate free intervals
        slot_delta = datetime.timedelta(minutes=MIN_TIME_INTERVAL_LENGTH_IN_MINUTES)
        free_intervals = []
        current_time = timeMin

        while current_time < timeMax:
                # Skip past slots
                if current_time < now:
                    current_time += slot_delta
                    continue

                # Skip no meeting days
                if current_time.strftime('%A').capitalize() in [day.capitalize() for day in NO_MEETING_DAYS]:
                    current_time += datetime.timedelta(days=1)
                    current_time = tz.localize(datetime.datetime(
                        current_time.year, current_time.month, current_time.day, START_HOUR
                    ))
                    continue

                # Adjust start and end time for each day
                if current_time.hour >= END_HOUR:
                    current_time += datetime.timedelta(days=1)
                    current_time = tz.localize(datetime.datetime(current_time.year, current_time.month, current_time.day, START_HOUR))
                    continue

                # Check if the slot overlaps with any busy interval
                is_free = True
                for busy in unified_busy_list:
                    if not ((current_time + slot_delta <= busy['start']) or (current_time >= busy['end'])):
                        is_free = False
                        break

                if is_free:
                    free_intervals.append({
                        "start": current_time.isoformat(),
                        "end": (current_time + slot_delta).isoformat()
                    })

                current_time += slot_delta

        # Limit the number of slots to MAX_SLOTS
        # free_intervals = free_intervals[:MAX_SLOTS]

        return free_intervals


    except HttpError as error:
        print('An error occurred: %s' % error)
        return []
    
def add_calendar_id_to_service_account(calendar_id):

    creds= load_credentials()
    service = build('calendar', 'v3', credentials=creds)

    try:
        # Add the calendar to the service account's calendar list
        calendar_list_entry = {
            'id': calendar_id
        }
        response = service.calendarList().insert(body=calendar_list_entry).execute()

        print(f"Successfully added calendar: {response['id']}")

    except Exception as e:
        print(f"An error occurred: {e}")



def get_calendar_ids():
    creds = load_credentials()
    # Authenticate and authorize the user
    

    try:
        # Build the Google Calendar API service
        service = build('calendar', 'v3', credentials=creds)

        # Fetch the list of calendars
        calendars = service.calendarList().list().execute()
        calendar_ids = []
        for calendar in calendars.get('items', []):
            calendar_ids.append({
                'id': calendar['id'],
                'summary': calendar.get('summary', 'No Title'),
                'primary': calendar.get('primary', False)
            })

        return calendar_ids

    except HttpError as error:
        print(f"An error occurred: {error}")
        return []


if __name__ == '__main__':
    
    # for calendar_id in CALENDAR_IDS:
    #     add_calendar_id_to_service_account(calendar_id)

    calendar_list= get_calendar_ids()

    print("calendar_list", calendar_list)

    available_times = get_calendar_availabilty( "2024-12-31","2025-01-02")
    print("Available times in ISO format:", available_times)
    # for interval in available_times:
    #     print(interval)
