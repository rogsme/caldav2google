"""Module for authenticating with Google Calendar API."""

import os
import pickle
from typing import List

from google.auth.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

SCOPES: List[str] = ["https://www.googleapis.com/auth/calendar"]


def authenticate_google() -> Resource:
    """Authenticate with Google Calendar API and return a service object.

    Attempts to load credentials from a pickle file, refresh them if expired,
    or create new ones through OAuth2 flow if necessary.

    Returns:
        Resource: An authenticated Google Calendar API service object.
    """
    creds: Credentials | None = None
    if os.path.exists("token.pickle"):
        with open("token.pickle", "rb") as token:
            creds = pickle.load(token)

    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)

        with open("token.pickle", "wb") as token:
            pickle.dump(creds, token)

    return build("calendar", "v3", credentials=creds)


def search_calendar_id(service: Resource, calendar_name: str) -> str:
    """List all available Google calendars and return the ID of the target calendar.

    Args:
        service: Authenticated Google Calendar API service object.
        calendar_name: Name of the target Google Calendar.

    Returns:
        str: The calendar ID of the target Google Calendar.

    Raises:
        ValueError: If the target calendar is not found.
    """
    calendars_result = service.calendarList().list().execute()
    calendars = calendars_result.get("items", [])

    for calendar in calendars:
        if calendar["summary"].lower() == calendar_name.lower():
            return calendar["id"]

    raise ValueError(f"No calendar named '{calendar_name}' found.")
