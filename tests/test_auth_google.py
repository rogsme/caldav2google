"""Tests for the auth_google module."""

import pytest

from src.auth_google import search_calendar_id


def test_search_calendar_id_found(mock_google_service):
    """Test searching for a calendar ID that exists in the list of calendars."""
    calendar_name = "Test Calendar"
    calendars = {
        "items": [
            {"summary": "Wrong Calendar", "id": "wrong-id"},
            {"summary": "Test Calendar", "id": "correct-id"},
        ],
    }
    mock_google_service.calendarList().list().execute.return_value = calendars

    result = search_calendar_id(mock_google_service, calendar_name)

    assert result == "correct-id"


def test_search_calendar_id_not_found(mock_google_service):
    """Test searching for a calendar ID that does not exist in the list of calendars."""
    calendar_name = "Nonexistent Calendar"
    calendars = {
        "items": [
            {"summary": "Wrong Calendar", "id": "wrong-id"},
            {"summary": "Test Calendar", "id": "correct-id"},
        ],
    }
    mock_google_service.calendarList().list().execute.return_value = calendars

    with pytest.raises(ValueError, match=f"No calendar named '{calendar_name}' found"):
        search_calendar_id(mock_google_service, calendar_name)
