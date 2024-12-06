"""Main module for the calendar synchronization process."""

import os

from dotenv import load_dotenv

from src.auth_google import authenticate_google, search_calendar_id
from src.caldav_client import connect_to_caldav, fetch_events, get_calendar
from src.logger import setup_logger
from src.sync_logic import (
    add_event_to_google,
    compare_events,
    delete_event_from_google,
    error_events,
    load_local_sync,
    save_local_sync,
)

logger = setup_logger(__name__)

load_dotenv()


def main() -> None:
    """Run the calendar synchronization process."""
    LOCAL_SYNC_FILE = "calendar_sync.json"
    CALDAV_URL = os.getenv("CALDAV_URL")
    CALDAV_USERNAME = os.getenv("CALDAV_USERNAME")
    CALDAV_PASSWORD = os.getenv("CALDAV_PASSWORD")
    CALDAV_CALENDAR_NAME = os.getenv("CALDAV_CALENDAR_NAME")
    GOOGLE_CALENDAR_NAME = os.getenv("GOOGLE_CALENDAR_NAME")

    try:
        logger.info("Starting calendar synchronization process")

        logger.info("Authenticating with Google Calendar...")
        service = authenticate_google()
        google_calendar_id = search_calendar_id(service, GOOGLE_CALENDAR_NAME)
        logger.info("Successfully authenticated with Google Calendar")

        logger.info("Connecting to CalDAV server...")
        principal = connect_to_caldav(CALDAV_URL, CALDAV_USERNAME, CALDAV_PASSWORD)
        caldav_calendar = get_calendar(principal, CALDAV_CALENDAR_NAME)
        logger.info("Successfully connected to CalDAV server")

        logger.info(f"Fetching events from CalDAV calendar: {caldav_calendar.name}")
        server_events = fetch_events(caldav_calendar)
        logger.info(f"Retrieved {len(server_events)} events from CalDAV")

        logger.info("Loading local sync data...")
        local_events = load_local_sync(LOCAL_SYNC_FILE)
        logger.info(f"Loaded {len(local_events)} events from local sync file")

        logger.info("Comparing events...")
        new_events, updated_events, deleted_events = compare_events(local_events, server_events)

        logger.info(f"Adding {len(new_events)} new events and updating {len(updated_events)} events in Google Calendar")
        for event in new_events + updated_events:
            add_event_to_google(service, event, google_calendar_id)

        logger.info(f"Deleting {len(deleted_events)} events from Google Calendar")
        for event in deleted_events:
            delete_event_from_google(service, event, google_calendar_id)

        logger.info("Saving updated sync data...")
        save_local_sync(LOCAL_SYNC_FILE, server_events)

        logger.info("Sync process completed successfully")

        if error_events:
            logger.warning("The following events encountered errors during sync:")
            for event in error_events:
                logger.warning(f"Failed event: {event['summary']} (UID: {event['uid']})")

    except Exception as e:
        logger.error(f"Error occurred during sync: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
