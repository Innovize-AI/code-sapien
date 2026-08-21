from langchain_core.tools import tool
from langgraph.prebuilt import ToolNode
from workflow.state import AgentGraphState
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate

import calendar_utils 
import json

from datetime import datetime
from dateutil.parser import isoparse
import random
import pytz
from pydantic import BaseModel, Field

class ProposedDate(BaseModel):

    proposed_type: str = Field(
        description="proposed meeting type, 'client' or 'innovize'"
    )
    proposed_times: list[str]= Field(
        description="list of all proposed times"
    )
    


CALENDAR_PROMPT="""
# Task
Your task is to identify the timezone and to return all the meeting times and days that the prospect proposed. Meetings are always 30 min.
Use this step-by-step process to ensure you are analyzing things correctly:
1. You will make sure to take into account the current date: {current_date}, to be able to define the right GMT current timezone for the place or timezone. 
2. identify the timezone that was mentioned by the prospect for the meeting and according to the timezone you attach it to the ISO string format of the time. For example GMT+1 is "2024-04-29T11:00:00+01:00" where the “01:00” is the timezone.
3. You will identify all the possible 30 min meeting slots that the prospect proposed. if the proposed time is "monday at 11AM (Sao Paulo time)", and the email was sent on Thursday April 25th 2024, you bring back the start date and time of monday the 29th of April at 11am in the following way: "2024-04-29T11:00:00-03:00”.
4. You will bring back ONLY the ISO formatted strings of all the available 30 min meeting timeslots that the prospect has mentioned as being available, nothing else, no explanation, no summary, nothing but the timeslots.
# Specifics
**IMPORTANT RULES (THIS IS VERY IMPORTANT TO MY CAREER):**
- Sometimes prospects will propose a range of times, for example between 11AM - 1PM (EST) on the 29th of April. In that case you will bring back ALL the possible 30 min timeslots in that range of time: "2024-04-29T11:00:00-04:00, 2024-04-29T11:30:00-04:00, 024-04-29T12:00:00-04:00, 2024-04-29T12:30:00-04:00"
- Sometimes prospects will propose different days and ranges, you will bring back ALL the possible 30 min timeslots in those range of times and days.
- As some timezones will change according to winter or summer times, you can figure out what the right timezone should be by looking at the current date here:
- If the prospect doesnot propose a particular day or time, use the {current_date} to identify possible dates for the week mentioned in the message. For Example, if the message to analyze is "this week", identify next days available for the week and return those dates.
{current_date}
.
- There will be a variety of ways prospects mention timezones, your goal is to match that and bring back the name of that timezone according to the GMT timezones.
- If you can't identify a timezone you will use always use IST(GMT +5:30) timezone".

**List of timezone naming that you have to use in your output:**
GMT = “+00:00”
GMT+0 = “+00:00”
GMT+1 = “+01:00”
GMT+2 = “+02:00”
GMT+3 = “+03:00”
GMT+4 = “+04:00”
GMT+5 = “+05:00”
GMT+6 = “+06:00”
GMT+7 = “+07:00”
GMT+8 = “+08:00”
GMT+9 = “+09:00”
GMT+10 = “+10:00”
GMT+11 = “+11:00”
GMT+12 = “+12:00”
GMT-0 = “+00:00”
GMT-1 = “-01:00”
GMT-2 = “-02:00”
GMT-3 = “-03:00”
GMT-4 = “-04:00”
GMT-5 = “-05:00”
GMT-6 = “-06:00”
GMT-7 = “-07:00”
GMT-8 = “-08:00”
GMT-9 = “-09:00”
GMT-10 = “-10:00”
GMT-11 = “-11:00”
GMT-12 = “-12:00”
GMT-13 = “-13:00”
GMT-14 = “-14:00”
GMT0 = “+00:00”
# Examples
- **EXAMPLE 1:**
**Input:**
current_date: 2024-12-30T15:33:07+05:30
Hi pavan, Is next Monday at 11 AM (UK time) good for a quick meeting? Thanks, Bailey
**Output response:**
2025-01-06T11:00:00+00:00
- **Example 2:**
**Input:**
Hi Oskar, Is next Monday between 11 - 1PM (Sao Paulo time) good for you? 
Thanks, Casey
**Output response:**
2025-01-06T11:00:00-03:00,
2025-01-06T11:30:00-03:00,
2025-01-06T12:00:00-03:00,
2025-01-06T12:30:00-03:00

**Input:**
Hi pavan, this week? 

**Output response:**
2025-01-02T00:00:00+5:30,
2025-01-03T00:00:00+5:30,
2025-01-04T00:00:00+5:30,
2025-01-05T00:30:00+5:30

# The is the message you have to analyze
{proposed_time}"""

CALENDAR_PROMPT_TEMPLATE = PromptTemplate(
    input_variables=["current_date", "proposed_time"],
    template= CALENDAR_PROMPT
)

GET_PROPOSED_DATES_PROMPT= """
# Role
You are world class message analyzer, with a particular knack for identifying the earliest and latest date and time in a list of ISO formatted strings of date and times. 
# Task
You will think step by step to ensure a good outcome.
1. You will identify the earliest date and latest date in the list of ISO formatted strings of date and times you will be provided with below. 
2. When you have identified those you will return ONLY return the ISO-formatted string of the earliest date and the latest date, NOT the time. 
3 You will return the 2 dates in a JSON format with the exact labels from the examples below. 
# Context
Your goal is to analyze the message and return some data in a JSON format, this data will be used in a google calender API to check the calender availability of the meeting time proposed
# Specifics
It is extremely important to my career you follow the following rules. 
- If the start and end date are the same date you will still return both the dates in the JSON format. 
- 
# Examples
**example 1:**
**Input:**
2024-05-06T20:00:00+02:00,
2024-05-06T20:30:00+02:00,
2024-05-06T21:00:00+02:00,
2024-05-06T21:30:00+02:00,
2024-05-06T22:00:00+02:00,
2024-05-07T20:00:00+02:00,
2024-05-07T20:30:00+02:00,
2024-05-07T21:00:00+02:00,
2024-05-07T21:30:00+02:00,
2024-05-07T22:00:00+02:00,
2024-05-08T20:00:00+02:00,
2024-05-08T20:30:00+02:00,
2024-05-08T21:00:00+02:00,
2024-05-08T21:30:00+02:00,
2024-05-08T22:00:00+02:00
**Output:**
{
"startDateTime": "2024-05-06",
"endDateTime": "2024-05-08",
}
**example 2:**
**Input:**
2024-04-29T12:00:00+02:00
**Output:**
{
"startDateTime": "2024-04-29",
"endDateTime": "2024-04-29",
}
# The times and dates you have to analyze:
{proposed_times}

"""

SLOT_AVAILABILITY_PROMPT= """Analyze the given input JSON structure. 
If the type is intersection_slots, extract the first available slot ' 
If the type is available_slots, retrieve and display the first two slots in the slots list and respond with a message indicating 'I'm not available for the proposed slot, but here are two alternatives.' 
Ensure the response with a message indicating 'I'm available at that time.and includes the day, date, time and timezone for the mentioned slots.


input: {context}

"""

SLOT_AVAILABILITY_PROMPT_TEMPLATE= PromptTemplate(
    input_variables=["context"],
    template= SLOT_AVAILABILITY_PROMPT
)

@tool
def calender_check(time:str):
    '''use when query related to scheduling meeting or meeting request. Get the calendar availability based on request'''

    current_time= datetime.now().isoformat()
    # print("current time ", current_time.strftime("%Y-%m-%d"))
    print("time from calendar agent ", time)

    # create a llm chain in tool
    # convert raw time into ISO format 
    # proposed_iso_chain= CALENDAR_PROMPT |llm 

    available_times_slots= get_available_times(time)

    # convert this into a friendly text with llm
    return available_times_slots
    
def get_min_max_dates(dateslist):    

    # Convert strings to datetime objects
    date_objects = [datetime.fromisoformat(date) for date in dateslist]

    # Find the earliest and latest datetime objects
    earliest_date = min(date_objects)
    latest_date = max(date_objects)

    # Remove the time part and format the date as YYYY-MM-DD
    earliest_date_str = earliest_date.date().strftime('%Y-%m-%d')
    latest_date_str = latest_date.date().strftime('%Y-%m-%d')

    return {
        "startDateTime": earliest_date_str,
        "endDateTime": latest_date_str,
        }
            


def get_available_times(proposed_time:str):

    # Get the current time in UTC
    current_time = datetime.now(pytz.UTC)

    # Remove microseconds
    current_time_without_microseconds = current_time.replace(microsecond=0)

    # Convert to ISO 8601 format
    current_time = current_time_without_microseconds.isoformat()

    print('current_time', current_time)
    # create a llm chain in tool
    llm_4o= ChatOpenAI(model="gpt-4o", temperature=0)
    llm_4o_mini= ChatOpenAI(model="gpt-4o-mini", temperature=0)
    # convert raw time into ISO format 
    chain = CALENDAR_PROMPT_TEMPLATE | llm_4o
    proposed_times= chain.invoke({"current_date": current_time,"proposed_time":proposed_time })

    if(proposed_times.content)=="No time zone specified":
        return "Please specify timezone for creating a meeting"

    proposed_ist_times= convert_to_ist(proposed_times.content)
    print("proposed ist times", proposed_ist_times)
    proposed_dates= get_min_max_dates(proposed_ist_times)

    print("proposed dates" , proposed_dates)

    # check calendar availability
    available_times= calendar_utils.get_calendar_availabilty(proposed_dates['startDateTime'], proposed_dates['endDateTime'])
    print("available_times" , available_times)
    available_times_slots= find_intersection(proposed_ist_times, available_times)
    
    print("available_times_slots", available_times_slots)
    processed_slots= process_slots(available_times_slots) 
    # convert this into a friendly text with llm
    slot_availabilty_chain= SLOT_AVAILABILITY_PROMPT_TEMPLATE | llm_4o_mini

    response= slot_availabilty_chain.invoke({"context":  processed_slots })

    return response.content



def convert_to_ist(times):
    
    date_strings = times.split(',')
  
    converted_date_strings = []

    try:
        # Process each date string in the list
        for date_string in date_strings:
            # Convert the date string into a datetime object
            dt = datetime.fromisoformat(date_string.strip())

            # Set the original timezone if not set in the date string
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=pytz.timezone('UTC'))

            # Convert the datetime to IST timezone
            ist_timezone = pytz.timezone('Asia/Kolkata')
            dt_ist = dt.astimezone(ist_timezone)

            # Format the datetime back to ISO format and add to the list
            converted_date_strings.append(dt_ist.isoformat())

        return converted_date_strings

    except Exception as e:
        print(f"Error processing the date(s): {e}")
        return str(e)


def find_intersection(proposed_times, available_times):
    # Directly build the dictionary for available times
    available_times_dict = {
        isoparse(slot["start"]): {
            "start": isoparse(slot["start"]),
            "end": isoparse(slot["end"]),
        }
        for slot in available_times
    }

    # Cache parsed proposed times to improve efficiency
    parsed_proposed_cache = {}

    # Find all intersections based on start times
    intersections = []
    for time in proposed_times:
        if time not in parsed_proposed_cache:
            parsed_proposed_cache[time] = isoparse(time)
        proposed = parsed_proposed_cache[time]
        if proposed in available_times_dict:
            available = available_times_dict[proposed]
            intersections.append( {
                    "start": available["start"].isoformat(),
                    "end": available["end"].isoformat(),
                },
            )

    # Return all intersections or an empty list if no intersection is found
    # If no intersections, return 2 random available time slots with a label
    if not intersections:
        random_slots = random.sample(available_times, min(2, len(available_times)))
        return {
            "type": "available_slots",
            "slots": [
                {
                    "start": slot["start"],
                    "end": slot["end"]
                } for slot in random_slots
            ]
        }

    return {
        "type": "intersection_slots",
        "slots": intersections
    }

def process_slots(input_data: dict) -> dict:
    import utils
    """
    Processes the input data to convert all slots' start and end times to a readable format.

    Args:
        input_data (dict): Input data containing a type and a list of slots with start and end times.
        timezone_str (str): The timezone string to use for conversion (e.g., "Asia/Kolkata", "GMT").
    
    Returns:
        dict: A dictionary with the same structure, but with formatted start and end times.
    """
    try:
        if input_data.get("type") in ["available_slots", "intersection_slots"] and "slots" in input_data:
            formatted_slots = []
            for slot in input_data["slots"]:
                print("slot start", slot["start"])
                start_readable = utils.convert_iso_to_readable(slot["start"])
                end_readable = utils.convert_iso_to_readable(slot["end"])
                formatted_slots.append({"start": start_readable, "end": end_readable})
            
            return {"type": input_data["type"], "slots": formatted_slots}
        else:
            return {"error": "Invalid input structure or type"}
    except Exception as e:
        return {"error": str(e)}