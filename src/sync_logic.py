"""Logic for syncing events between a local calendar and Google Calendar."""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

from googleapiclient.discovery import Resource

from src.logger import setup_logger

logger = setup_logger(__name__)

EventDict = Dict[str, Any]
EventsDict = Dict[str, EventDict]

error_events: List[EventDict] = []


def _sanitize_event_for_json(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize event data to ensure it's JSON serializable.

    Args:
        event_data: Dictionary containing event details.

    Returns:
        Dict[str, Any]: Sanitized dictionary.
    """
    sanitized = event_data.copy()

    if "rrule" in sanitized and sanitized["rrule"]:
        rrule = sanitized["rrule"].copy()
        for key, value in rrule.items():
            if isinstance(value, list):
                rrule[key] = [item.isoformat() if isinstance(item, datetime) else item for item in value]
        sanitized["rrule"] = rrule

    return sanitized


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

    logger.info(f"Comparing {len(server_events)} server events with {len(local_events)} local events")

    # Update server_events with Google event IDs from local_events
    for uid, event in server_events.items():
        if uid in local_events:
            event["google_event_id"] = local_events[uid].get("google_event_id")

    for uid, event in server_events.items():
        if uid not in local_events:
            logger.debug(f"New event found: {event['summary']} (UID: {uid})")
            new_events.append(event)
        elif event["last_modified"] != local_events[uid].get("last_modified"):
            logger.debug(f"Modified event found: {event['summary']} (UID: {uid})")
            updated_events.append(event)

    for uid, event in local_events.items():
        if uid not in server_events:
            logger.debug(f"Deleted event found: {event['summary']} (UID: {uid})")
            deleted_events.append(event)

    logger.info(
        f"Found {len(new_events)} new events, {len(updated_events)} modified events, "
        f"and {len(deleted_events)} deleted events",
    )
    return new_events, updated_events, deleted_events


def load_local_sync(file_path: str) -> EventsDict:
    """Load the locally synced events from a JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        EventsDict: Dictionary of previously synced events.
    """
    logger.info(f"Loading local sync data from {file_path}")
    if not os.path.exists(file_path):
        logger.info("No existing sync file found, starting fresh")
        return {}

    try:
        with open(file_path, "r") as file:
            events = json.load(file)
            logger.info(f"Successfully loaded {len(events)} events from local sync file")
            return events
    except json.JSONDecodeError as e:
        logger.error(f"Error decoding JSON from {file_path}: {str(e)}")
        return {}
    except Exception as e:
        logger.error(f"Unexpected error loading sync file: {str(e)}")
        return {}


def save_local_sync(file_path: str, events: EventsDict) -> None:
    """Save the events to the local sync JSON file.

    Args:
        file_path: Path to the JSON file.
        events: Dictionary of events to save.
    """
    logger.info(f"Saving {len(events)} events to local sync file")
    sanitized_events = {}

    for event_id, event_data in events.items():
        try:
            sanitized_events[event_id] = _sanitize_event_for_json(event_data)
        except Exception as e:
            logger.error(f"Failed to sanitize event {event_id} ({event_data.get('summary', 'No summary')}): {str(e)}")
            continue

    try:
        with open(file_path, "w") as file:
            json.dump(sanitized_events, file, indent=4)
            logger.info(f"Successfully saved {len(sanitized_events)} events to {file_path}")
    except Exception as e:
        logger.error(f"Failed to save sync file: {str(e)}")
        logger.debug("Attempting to identify problematic events...")

        for event_id, event_data in sanitized_events.items():
            try:
                json.dumps(event_data)
            except TypeError as e:
                logger.error(f"JSON serialization failed for event: {event_id}")
                logger.error(f"Event summary: {event_data.get('summary', 'No summary')}")
                logger.error(f"Error: {str(e)}")

                for key, value in event_data.items():
                    try:
                        json.dumps({key: value})
                    except TypeError:
                        logger.error(f"Problematic field: {key} = {value} (type: {type(value)})")


def _create_google_event_body(event: EventDict) -> Dict[str, Any]:
    """Create the event body for Google Calendar API.

    Args:
        event: Dictionary containing event details.

    Returns:
        Dict[str, Any]: Formatted event body for Google Calendar API.
    """
    google_event = {
        "summary": event["summary"],
        "description": event.get("description", ""),
        "location": event.get("location", ""),
        "start": {"dateTime": event["start"], "timeZone": "UTC"},
        "end": {"dateTime": event["end"], "timeZone": "UTC"},
    }

    if event.get("rrule"):
        logger.debug(f"Processing recurring event rules for {event['summary']}")
        rrule_parts = []
        for key, value in event["rrule"].items():
            if isinstance(value, list):
                value = [item.isoformat() if isinstance(item, datetime) else item for item in value]
                value = ",".join(str(v) for v in value)
            rrule_parts.append(f"{key}={value}")
        google_event["recurrence"] = [f"RRULE:{';'.join(rrule_parts)}"]

        if event.get("exdate"):
            logger.debug(f"Processing {len(event['exdate'])} excluded dates")
            exdates = [f"EXDATE;TZID=UTC:{date}" for date in event["exdate"]]
            google_event["recurrence"].extend(exdates)

    return google_event


def add_event_to_google(service: Resource, event: EventDict, calendar_id: str) -> None:
    """Add or update a single event in Google Calendar.

    Args:
        service: Authenticated Google Calendar API service object.
        event: Dictionary containing event details.
        calendar_id: ID of the target Google Calendar.
    """
    logger.info(f"Processing event: {event['summary']} (UID: {event['uid']})")

    try:
        google_event = _create_google_event_body(event)

        if event.get("google_event_id"):
            logger.info(
                f"Updating existing event in Google Calendar: {event['summary']} (GoogleID: {event['google_event_id']})",
            )
            created_event = (
                service.events()
                .update(
                    calendarId=calendar_id,
                    eventId=event["google_event_id"],
                    body=google_event,
                )
                .execute()
            )
            logger.info(f"Successfully updated event: {event['summary']} (Google ID: {created_event['id']})")
        else:
            logger.info(f"Creating new event in Google Calendar: {event['summary']}")
            created_event = (
                service.events()
                .insert(
                    calendarId=calendar_id,
                    body=google_event,
                )
                .execute()
            )
            event["google_event_id"] = created_event["id"]
            logger.info(f"Successfully created event: {event['summary']} (Google ID: {created_event['id']})")

    except Exception as e:
        logger.error(f"Failed to add/update event {event['summary']} (UID: {event['uid']})")
        logger.error(f"Error: {str(e)}")
        error_events.append(event)

    finally:
        time.sleep(0.5)


def delete_event_from_google(service: Resource, event: EventDict, calendar_id: str) -> None:
    """Delete a single event from Google Calendar.

    Args:
        service: Authenticated Google Calendar API service object.
        event: Dictionary containing event details.
        calendar_id: ID of the target Google Calendar.
    """
    try:
        google_event_id = event.get("google_event_id")
        if not google_event_id:
            logger.warning(
                f"No Google Calendar ID found for event {event.get('summary', 'Unknown')} "
                f"(UID: {event.get('uid', 'Unknown')})",
            )
            return

        summary = event.get("summary", "Unknown Event")

        logger.info(f"Deleting event: {summary} (Google ID: {google_event_id})")
        service.events().delete(calendarId=calendar_id, eventId=google_event_id).execute()
        logger.info(f"Successfully deleted event: {summary}")

    except Exception as e:
        logger.error(f"Failed to delete event: {event.get('summary', 'Unknown')} (UID: {event.get('uid', 'Unknown')})")
        logger.error(f"Error: {str(e)}")

    finally:
        time.sleep(0.5)
