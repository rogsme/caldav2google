"""Logic for syncing events between a local calendar and Google Calendar."""

import json
import os
import time
from typing import Any, Dict, List, Tuple

from googleapiclient.discovery import Resource

EventDict = Dict[str, Any]
EventsDict = Dict[str, EventDict]

error_events = []


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
    with open(file_path, "w") as file:
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
                    value = ",".join(str(v) for v in value)
                rrule_parts.append(f"{key}={value}")
            google_event["recurrence"] = [f"RRULE:{';'.join(rrule_parts)}"]

            if event.get("exdate"):
                exdates = [f"EXDATE;TZID=UTC:{date}" for date in event["exdate"]]
                google_event["recurrence"].extend(exdates)

        if event.get("recurrence_id"):
            original_id = event["uid"].rsplit("-", 1)[0]
            instance_id = event["recurrence_id"]

            original_events = (
                service.events()
                .list(
                    calendarId=calendar_id,
                    iCalUID=original_id,
                )
                .execute()
                .get("items", [])
            )

            if original_events:
                original_event_id = original_events[0]["id"]
                google_event["originalStartTime"] = {
                    "dateTime": instance_id,
                    "timeZone": "UTC",
                }
                created_event = (
                    service.events()
                    .update(
                        calendarId=calendar_id,
                        eventId=original_event_id,
                        body=google_event,
                    )
                    .execute()
                )
            else:
                raise ValueError(f"Original recurring event not found for exception: {event['uid']}")
        else:
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
