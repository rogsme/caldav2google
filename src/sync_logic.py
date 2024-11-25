"""Logic for syncing events between a local calendar and Google Calendar."""

import json
import os
import time
from datetime import datetime
from typing import Any, Dict, List, Tuple

from googleapiclient.discovery import Resource

EventDict = Dict[str, Any]
EventsDict = Dict[str, EventDict]

error_events = []


def _sanitize_event_for_json(event_data: Dict[str, Any]) -> Dict[str, Any]:
    """Sanitize event data to ensure it's JSON serializable.

    Args:
        event_data: Dictionary containing event details.

    Returns:
        Dict[str, Any]: Sanitized dictionary.

    Raises:
        TypeError: If the event data is not JSON serializable.
    """
    sanitized = event_data.copy()

    if "rrule" in sanitized and sanitized["rrule"]:
        rrule = sanitized["rrule"].copy()
        for key, value in rrule.items():
            if isinstance(value, list):
                rrule[key] = [item.isoformat() if isinstance(item, datetime) else item for item in value]
        sanitized["rrule"] = rrule

    return sanitized


def load_local_sync(file_path: str) -> EventsDict:
    """Load the locally synced events from a JSON file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        EventsDict: Dictionary of previously synced events.
    """
    if not os.path.exists(file_path):
        return {}
    with open(file_path, "r") as file:
        return json.load(file)


def save_local_sync(file_path: str, events: EventsDict) -> None:
    """Save the events to the local sync JSON file.

    Args:
        file_path: Path to the JSON file.
        events: Dictionary of events to save.
    """
    sanitized_events = {}
    for event_id, event_data in events.items():
        try:
            sanitized_events[event_id] = _sanitize_event_for_json(event_data)
        except Exception as e:
            print(f"Warning: Could not sanitize event {event_id}: {e}")
            continue

    try:
        with open(file_path, "w") as file:
            json.dump(sanitized_events, file, indent=4)
    except TypeError as e:
        print(f"Error saving events: {e}")
        for event_id, event_data in sanitized_events.items():
            try:
                json.dumps(event_data)
            except TypeError as e:
                print(f"Problem found in event {event_id}: {e}")
                for key, value in event_data.items():
                    try:
                        json.dumps({key: value})
                    except TypeError as e:
                        print(f"  Problem field: {key} = {value} (type: {type(value)})")


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
            event["google_event_id"] = local_events[uid].get("google_event_id")
            updated_events.append(event)

    for uid in local_events:
        if uid not in server_events:
            deleted_events.append(local_events[uid])

    return new_events, updated_events, deleted_events


def add_event_to_google(service: Resource, event: EventDict, calendar_id: str) -> None:
    """Add a single event to Google Calendar.

    Args:
        service: Authenticated Google Calendar API service object.
        event: Dictionary containing event details.
        calendar_id: ID of the target Google Calendar.
    """
    try:
        print(f"Adding event to Google Calendar: {event['summary']}")
        google_event = {
            "summary": event["summary"],
            "description": event.get("description", ""),
            "location": event.get("location", ""),
            "start": {"dateTime": event["start"], "timeZone": "UTC"},
            "end": {"dateTime": event["end"], "timeZone": "UTC"},
        }

        if event.get("rrule"):
            rrule_parts = []
            for key, value in event["rrule"].items():
                if isinstance(value, list):
                    value = [item.isoformat() if isinstance(item, datetime) else item for item in value]
                    value = ",".join(str(v) for v in value)
                rrule_parts.append(f"{key}={value}")
            google_event["recurrence"] = [f"RRULE:{';'.join(rrule_parts)}"]

            if event.get("exdate"):
                exdates = [f"EXDATE;TZID=UTC:{date}" for date in event["exdate"]]
                google_event["recurrence"].extend(exdates)

        created_event = (
            service.events()
            .insert(
                calendarId=calendar_id,
                body=google_event,
            )
            .execute()
        )

        event["google_event_id"] = created_event["id"]
        print(f"Event created: {created_event.get('htmlLink')}")
        time.sleep(0.5)
    except Exception as e:
        print(f"Failed to add event: {event['summary']} - {e}")
        error_events.append(event)


def delete_event_from_google(service: Resource, event: EventDict, calendar_id: str) -> None:
    """Delete a single event from Google Calendar.

    Args:
        service: Authenticated Google Calendar API service object.
        event: Dictionary containing event details.
        calendar_id: ID of the target Google Calendar.
    """
    google_event_id = event.get("google_event_id")
    if not google_event_id:
        raise ValueError(f"Cannot delete event {event['summary']}: missing Google Calendar ID")
    try:
        service.events().delete(calendarId=calendar_id, eventId=google_event_id).execute()
        print(f"Deleted event: {event['summary']}")
    except Exception as e:
        print(f"Failed to delete event: {event['summary']} - {e}")
