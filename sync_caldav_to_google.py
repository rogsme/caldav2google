"""Synchronize CalDAV calendar events with Google Calendar."""

"""
CalDAV2Google.
Copyright (C) 2024 Roger Gonzalez

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""
import json
import os
import pickle
import time
from typing import Any, Dict, List, Tuple

from caldav import DAVClient, Principal, Calendar as CalDAVCalendar
from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build
from icalendar import Calendar
from dotenv import load_dotenv

load_dotenv(".env")

EventDict = Dict[str, Any]
EventsDict = Dict[str, EventDict]

CALDAV_URL: str = os.getenv("CALDAV_URL")
CALDAV_USERNAME: str = os.getenv("CALDAV_USERNAME")
CALDAV_PASSWORD: str = os.getenv("CALDAV_PASSWORD")
CALDAV_CALENDAR_NAME: str = os.getenv("CALDAV_CALENDAR_NAME")
GOOGLE_CALENDAR_NAME: str = os.getenv("GOOGLE_CALENDAR_NAME")

LOCAL_SYNC_FILE: str = "calendar_sync.json"
SCOPES: List[str] = ["https://www.googleapis.com/auth/calendar"]

errored = []

def authenticate_google() -> Resource:
    """Authenticate with Google Calendar API and return a service object.

    Attempts to load credentials from a pickle file, refresh them if expired,
    or create new ones through OAuth2 flow if necessary.

    Returns:
        Resource: An authenticated Google Calendar API service object.

    Raises:
        FileNotFoundError: If credentials.json is not found.
        pickle.PickleError: If token.pickle cannot be read or written.
    """
    creds: Credentials | None = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)

def search_calendar_id(service: Resource) -> str:
    """List all available Google calendars and return the ID of the target calendar.

    Args:
        service: Authenticated Google Calendar API service object.

    Returns:
        str: The calendar ID of the target Google Calendar.

    Raises:
        ValueError: If the target calendar is not found.
    """
    calendars_result = service.calendarList().list().execute()
    calendars: List[Dict[str, Any]] = calendars_result.get("items", [])

    print("Available calendars:")
    for calendar in calendars:
        print(f"{calendar['summary']} (ID: {calendar['id']})")
        if calendar["summary"].lower() == GOOGLE_CALENDAR_NAME.lower():
            return calendar["id"]

    raise ValueError("No calendar named 'Personal' found.")

def add_event_to_google(service: Resource, event: EventDict, calendar_id: str) -> None:
    """Add a single event to Google Calendar.

    It includes a small delay (0.5s) to prevent rate-limiting.

    Args:
        service: Authenticated Google Calendar API service object.
        event: Dictionary containing event details.
        calendar_id: ID of the target Google Calendar.

    Raises:
        Exception: If the event creation fails.
    """
    try:
        print(f"Adding event to Google Calendar: {event['summary']}")
        google_event = {
            "summary": event["summary"],
            "start": {"dateTime": event["start"], "timeZone": "UTC"},
            "end": {"dateTime": event["end"], "timeZone": "UTC"},
        }
        print(f"Google event body: {google_event}")
        created_event = service.events().insert(calendarId=calendar_id, body=google_event).execute()
        print(f"Event created: {created_event.get('htmlLink')}")
        time.sleep(0.5)
    except Exception as e:
        print(f"Failed to add event: {event['summary']}. Error: {str(e)}")
        errored.append(event)

def delete_event_from_google(service: Resource, event: EventDict, calendar_id: str) -> None:
    """Delete a single event from Google Calendar.

    Args:
        service: Authenticated Google Calendar API service object.
        event: Dictionary containing event details.
        calendar_id: ID of the target Google Calendar.

    Raises:
        Exception: If the event deletion fails.
    """
    print(f"Deleting event from Google Calendar: {event['summary']}")
    event_id = event.get("uid")
    try:
        service.events().delete(calendarId=calendar_id, eventId=event_id).execute()
        print(f"Event deleted: {event['summary']}")
    except Exception as e:
        print(f"Failed to delete event: {event['summary']} - {str(e)}")
        raise

def connect_to_caldav() -> Principal:
    """Connect to the CalDAV server and return the principal object.

    Returns:
        Principal: The authenticated CalDAV principal object.

    Raises:
        Exception: If connection to the CalDAV server fails.
    """
    client = DAVClient(CALDAV_URL, username=CALDAV_USERNAME, password=CALDAV_PASSWORD)
    return client.principal()

def get_calendar(principal: Principal) -> CalDAVCalendar:
    """Get a specific calendar from the CalDAV principal.

    Args:
        principal: Authenticated CalDAV principal object.

    Returns:
        CalDAVCalendar: The selected calendar object.

    Raises:
        ValueError: If no calendars are found on the server.
    """
    calendars = principal.calendars()
    if not calendars:
        raise ValueError("No calendars found on the server.")

    print("Available CalDAV calendars:")
    calendar = None
    for i, cal in enumerate(calendars):
        print(f"{i}: {cal.name}")
        if cal.name.lower() == CALDAV_CALENDAR_NAME.lower():
            calendar = cal

    if not calendar:
        raise ValueError(f"No calendar named {CALDAV_CALENDAR_NAME} found.")

    return calendar


def fetch_events(calendar: CalDAVCalendar) -> EventsDict:
    """Fetch all events from the CalDAV calendar.

    Args:
        calendar: CalDAV calendar object to fetch events from.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of events indexed by their UIDs.
    """
    events: EventsDict = {}
    for event in calendar.events():
        ical = Calendar.from_ical(event.data)
        for component in ical.walk():
            if component.name == "VEVENT":
                uid = str(component.get("UID"))
                dtstart = component.get("DTSTART")
                dtend = component.get("DTEND")
                last_modified = component.get("LAST-MODIFIED")

                events[uid] = {
                    "uid": uid,
                    "summary": str(component.get("SUMMARY")),
                    "start": dtstart.dt.isoformat() if dtstart else None,
                    "end": dtend.dt.isoformat() if dtend else None,
                    "last_modified": last_modified.dt.isoformat() if last_modified else None,
                }

    print(f"Total fetched events: {len(events)}")
    return events

def load_local_sync() -> EventsDict:
    """Load the locally synced events from JSON file.

    Returns:
        Dict[str, Dict[str, Any]]: Dictionary of previously synced events.
    """
    if not os.path.exists(LOCAL_SYNC_FILE):
        return {}
    with open(LOCAL_SYNC_FILE, "r") as file:
        return json.load(file)

def save_local_sync(events: EventsDict) -> None:
    """Save the events to the local sync JSON file.

    Args:
        events: Dictionary of events to save.
    """
    with open(LOCAL_SYNC_FILE, "w") as file:
        json.dump(events, file, indent=4)

def compare_events(
    local_events: EventsDict,
    server_events: EventsDict,
) -> Tuple[List[EventDict], List[EventDict], List[EventDict]]:
    """Compare local and server events to determine changes.

    Args:
        local_events: Dictionary of locally stored events.
        server_events: Dictionary of events from the server.

    Returns:
        Tuple containing lists of new, updated, and deleted events.
    """
    new_events: List[EventDict] = []
    updated_events: List[EventDict] = []
    deleted_events: List[EventDict] = []

    for uid, event in server_events.items():
        if uid not in local_events:
            new_events.append(event)
        elif event["last_modified"] != local_events[uid].get("last_modified"):
            updated_events.append(event)

    for uid in local_events:
        if uid not in server_events:
            deleted_events.append(local_events[uid])

    print(f"New events: {len(new_events)}")
    print(f"Updated events: {len(updated_events)}")
    print(f"Deleted events: {len(deleted_events)}")

    return new_events, updated_events, deleted_events

def main() -> None:
    """Run the calendar synchronization process."""
    print("Authenticating with Google Calendar...")
    service = authenticate_google()
    personal_calendar_id = search_calendar_id(service)

    print("Connecting to CalDAV server...")
    principal = connect_to_caldav()
    calendar = get_calendar(principal)

    print(f"Syncing calendar: {calendar.name}")
    server_events = fetch_events(calendar)

    print("Loading local sync...")
    local_events = load_local_sync()
    print(f"Local events: {len(local_events)}")

    print("Comparing events...")
    new_events, updated_events, deleted_events = compare_events(local_events, server_events)

    if new_events or updated_events:
        print(f"Adding {len(new_events) + len(updated_events)} new/updated event(s) to Google Calendar...")
        for event in new_events + updated_events:
            add_event_to_google(service, event, personal_calendar_id)

    if deleted_events:
        print(f"Deleting {len(deleted_events)} event(s) from Google Calendar...")
        for event in deleted_events:
            delete_event_from_google(service, event, personal_calendar_id)

    print("Saving updated sync...")
    save_local_sync(server_events)
    print("Sync completed.")

    if errored:
        print("The following events failed to sync:")
        for event in errored:
            print(event)

if __name__ == "__main__":
    main()
