"""Tests for the caldav_client module."""

from unittest.mock import MagicMock

import pytest

from src.caldav_client import get_calendar


def test_get_calendar_found(mock_caldav_principal):
    """Test getting a calendar that exists in the list of calendars."""
    calendar_name = "Test Calendar"
    mock_calendar = MagicMock()
    mock_calendar.name = calendar_name
    mock_caldav_principal.calendars.return_value = [mock_calendar]

    result = get_calendar(mock_caldav_principal, calendar_name)

    assert result == mock_calendar


def test_get_calendar_not_found(mock_caldav_principal):
    """Test getting a calendar that does not exist in the list of calendars."""
    calendar_name = "Nonexistent Calendar"
    mock_calendar = MagicMock()
    mock_calendar.name = "Different Calendar"
    mock_caldav_principal.calendars.return_value = [mock_calendar]

    with pytest.raises(ValueError, match=f"No calendar named '{calendar_name}' found"):
        get_calendar(mock_caldav_principal, calendar_name)
