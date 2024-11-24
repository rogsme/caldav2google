"""Module to interact with a CalDAV server and fetch events from a calendar."""

from typing import Any, Dict

from caldav import Calendar as CalDAVCalendar
from caldav import DAVClient, Principal
from icalendar import Calendar

EventDict = Dict[str, Any]
EventsDict = Dict[str, EventDict]


def connect_to_caldav(url: str, username: str, password: str) -> Principal:
    """Connect to the CalDAV server and return the principal object.

    Args:
        url: URL of the CalDAV server.
        username: Username for authentication.
        password: Password for authentication.

    Returns:
        Principal: The authenticated CalDAV principal object.
    """
    client = DAVClient(url, username=username, password=password)
    return client.principal()


def get_calendar(principal: Principal, calendar_name: str) -> CalDAVCalendar:
    """Get a specific calendar from the CalDAV principal.

    Args:
        principal: Authenticated CalDAV principal object.
        calendar_name: Name of the calendar to fetch.

    Returns:
        CalDAVCalendar: The selected calendar object.

    Raises:
        ValueError: If no matching calendar is found.
    """
    calendars = principal.calendars()
    if not calendars:
        raise ValueError("No calendars found on the server.")

    for cal in calendars:
        if cal.name.lower() == calendar_name.lower():
            return cal

    raise ValueError(f"No calendar named '{calendar_name}' found.")


def fetch_events(calendar: CalDAVCalendar) -> EventsDict:
    """Fetch all events from the CalDAV calendar.

    Args:
        calendar: CalDAV calendar object to fetch events from.

    Returns:
        EventsDict: Dictionary of events indexed by their UIDs.
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
                    "google_event_id": None,
                }

    return events
