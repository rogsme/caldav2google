"""Module for authenticating with Google Calendar API."""

import os
import pickle
import sys
from typing import List

from google.auth.credentials import Credentials
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import Resource, build

from src.logger import setup_logger

logger = setup_logger(__name__)

SCOPES: List[str] = ["https://www.googleapis.com/auth/calendar"]
TOKEN_FILE = "token.pickle"
CREDENTIALS_FILE = "credentials.json"

REAUTH_HINT = (
    "Run `uv run python -m src.auth_google` on a machine with a browser, then copy token.pickle to this machine. "
    "If this happens about every 7 days, the OAuth consent screen is in 'Testing': "
    "publish it to 'In production' in Google Auth Platform > Audience, then authenticate once more."
)


def _is_interactive() -> bool:
    """Return True when a person is at a terminal and can complete the browser OAuth flow."""
    return sys.stdin is not None and sys.stdin.isatty()


def _save_credentials(creds: Credentials) -> None:
    """Write credentials to the token file."""
    logger.debug(f"Saving credentials to {TOKEN_FILE}")
    with open(TOKEN_FILE, "wb") as token:
        pickle.dump(creds, token)


def run_oauth_flow() -> Credentials:
    """Run the browser OAuth2 flow, save the resulting credentials and return them.

    Returns:
        Credentials: Fresh credentials that include a refresh token.
    """
    logger.info("Starting new OAuth2 flow")
    flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_FILE, SCOPES)
    creds = flow.run_local_server(port=0)
    _save_credentials(creds)
    return creds


def authenticate_google() -> Resource:
    """Authenticate with Google Calendar API and return a service object.

    Loads credentials from the token file and refreshes them when expired. The browser
    OAuth2 flow only runs when a terminal is attached; without one (for example under
    cron) a clear error is raised instead of blocking while waiting for a browser.

    Returns:
        Resource: An authenticated Google Calendar API service object.

    Raises:
        RefreshError: If the refresh token is expired or revoked and no terminal is attached.
        RuntimeError: If there are no usable credentials and no terminal is attached.
    """
    creds = None
    if os.path.exists(TOKEN_FILE):
        logger.debug(f"Loading existing credentials from {TOKEN_FILE}")
        with open(TOKEN_FILE, "rb") as token:
            creds = pickle.load(token)

    if creds and creds.valid:
        return build("calendar", "v3", credentials=creds)

    if creds and creds.expired and creds.refresh_token:
        logger.info("Refreshing expired credentials")
        try:
            creds.refresh(Request())
        except RefreshError:
            if not _is_interactive():
                logger.error(f"Google refresh token is expired or revoked. {REAUTH_HINT}")
                raise
            logger.warning("Google refresh token is expired or revoked, starting a new OAuth2 flow")
            creds = run_oauth_flow()
        else:
            _save_credentials(creds)
    elif _is_interactive():
        creds = run_oauth_flow()
    else:
        error_msg = f"No usable Google credentials in {TOKEN_FILE} and no terminal to run the OAuth2 flow. {REAUTH_HINT}"
        logger.error(error_msg)
        raise RuntimeError(error_msg)

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
    logger.info(f"Searching for calendar: {calendar_name}")
    calendars_result = service.calendarList().list().execute()
    calendars = calendars_result.get("items", [])
    logger.debug(f"Found {len(calendars)} calendars in total")

    for calendar in calendars:
        if calendar["summary"].lower() == calendar_name.lower():
            logger.info(f"Found matching calendar with ID: {calendar['id']}")
            return calendar["id"]

    error_msg = f"No calendar named '{calendar_name}' found"
    logger.error(error_msg)
    raise ValueError(error_msg)


if __name__ == "__main__":
    run_oauth_flow()
    logger.info(f"Google credentials saved to {TOKEN_FILE}")
