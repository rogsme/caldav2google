"""Main module for the calendar synchronization process."""

import os

from auth_google import authenticate_google, search_calendar_id
from caldav_client import connect_to_caldav, fetch_events, get_calendar
from dotenv import load_dotenv
from sync_logic import (
    add_event_to_google,
    compare_events,
    delete_event_from_google,
    error_events,
    load_local_sync,
    save_local_sync,
)

load_dotenv()

LOCAL_SYNC_FILE = "calendar_sync.json"
CALDAV_URL = os.getenv("CALDAV_URL")
CALDAV_USERNAME = os.getenv("CALDAV_USERNAME")
CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD")
CALDAV_CALENDAR_NAME = os.getenv("CALDAV_CALENDAR_NAME")
GOOGLE_CALENDAR_NAME = os.getenv("GOOGLE_CALENDAR_NAME")


def main() -> None:
    """Run the calendar synchronization process."""
    try:
        print("Authenticating with Google Calendar...")
        service = authenticate_google()
        google_calendar_id = search_calendar_id(service, GOOGLE_CALENDAR_NAME)

        print("Connecting to CalDAV server...")
        principal = connect_to_caldav(CALDAV_URL, CALDAV_USERNAME, CALDAV_PASSWORD)
        caldav_calendar = get_calendar(principal, CALDAV_CALENDAR_NAME)

        print(f"Fetching events from CalDAV calendar: {caldav_calendar.name}")
        server_events = fetch_events(caldav_calendar)

        print("Loading local sync data...")
        local_events = load_local_sync(LOCAL_SYNC_FILE)

        print("Comparing events...")
        new_events, updated_events, deleted_events = compare_events(local_events, server_events)

        print(f"Adding/Updating {len(new_events) + len(updated_events)} events to Google Calendar...")
        for event in new_events + updated_events:
            add_event_to_google(service, event, google_calendar_id)

        print(f"Deleting {len(deleted_events)} events from Google Calendar...")
        for event in deleted_events:
            delete_event_from_google(service, event, google_calendar_id)

        print("Saving updated sync data...")
        save_local_sync(LOCAL_SYNC_FILE, server_events)

        print("Sync process completed successfully.")

        if error_events:
            print("The following events encountered errors during sync:")
            for event in error_events:
                print(event)

    except Exception as e:
        print(f"Error occurred during sync: {e}")


if __name__ == "__main__":
    main()
