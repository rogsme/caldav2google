"""Module to interact with a CalDAV server and fetch events from a calendar."""

from typing import Any, Dict

from caldav import Calendar as CalDAVCalendar
from caldav import DAVClient, Principal
from icalendar import Calendar

from src.logger import setup_logger

logger = setup_logger(__name__)

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
    logger.info(f"Connecting to CalDAV server at {url}")
    client = DAVClient(url, username=username, password=password)
    principal = client.principal()
    logger.info("Successfully connected to CalDAV server")
    return principal


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
    logger.info("Retrieving list of calendars")
    calendars = principal.calendars()
    if not calendars:
        error_msg = "No calendars found on the server"
        logger.error(error_msg)
        raise ValueError(error_msg)

    logger.debug(f"Found {len(calendars)} calendars")
    for cal in calendars:
        if cal.name.lower() == calendar_name.lower():
            logger.info(f"Found matching calendar: {cal.name}")
            return cal

    error_msg = f"No calendar named '{calendar_name}' found"
    logger.error(error_msg)
    raise ValueError(error_msg)


def _process_exdate(exdate: Any) -> list:
    """Process EXDATE field which can be either a single date or a list of dates.

    Args:
        exdate: EXDATE field from an iCalendar event.

    Returns:
        list: List of dates in ISO format or None if no EXDATE field is present.
    """
    if not exdate:
        return None

    if isinstance(exdate, list):
        dates = []
        for date in exdate:
            if hasattr(date, "dts"):
                dates.extend(dt.dt.isoformat() for dt in date.dts)
            elif hasattr(date, "dt"):
                dates.append(date.dt.isoformat())
        return dates

    if hasattr(exdate, "dts"):
        return [dt.dt.isoformat() for dt in exdate.dts]
    if hasattr(exdate, "dt"):
        return [exdate.dt.isoformat()]

    return None


def fetch_events(calendar: CalDAVCalendar) -> EventsDict:
    """Fetch all events from the CalDAV calendar.

    Args:
        calendar: CalDAV calendar object to fetch events from.

    Returns:
        EventsDict: Dictionary of events indexed by their UIDs.
    """
    logger.info(f"Fetching events from calendar: {calendar.name}")
    events: EventsDict = {}
    event_count = 0
    recurrence_count = 0

    for event in calendar.events():
        ical = Calendar.from_ical(event.data)
        for component in ical.walk():
            if component.name == "VEVENT":
                event_count += 1
                uid = str(component.get("UID"))
                dtstart = component.get("DTSTART")
                dtend = component.get("DTEND")
                last_modified = component.get("LAST-MODIFIED")
                rrule = component.get("RRULE")
                exdate = component.get("EXDATE")

                recurrence_id = component.get("RECURRENCE-ID")
                if recurrence_id:
                    uid = f"{uid}-{recurrence_id.dt.isoformat()}"
                    recurrence_count += 1

                description = component.get("DESCRIPTION")
                description = str(description) if description else ""

                location = component.get("LOCATION")
                location = str(location) if location else ""

                events[uid] = {
                    "uid": uid,
                    "summary": str(component.get("SUMMARY")),
                    "description": description,
                    "location": location,
                    "start": dtstart.dt.isoformat() if dtstart else None,
                    "end": dtend.dt.isoformat() if dtend else None,
                    "last_modified": last_modified.dt.isoformat() if last_modified else None,
                    "rrule": dict(rrule) if rrule else None,
                    "exdate": _process_exdate(exdate),
                    "recurrence_id": recurrence_id.dt.isoformat() if recurrence_id else None,
                    "google_event_id": None,
                }

    logger.info(f"Retrieved {event_count} events ({recurrence_count} recurring instances) from CalDAV calendar")
    return events
