"""Tests for the connect_to_caldav function."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from caldav import DAVClient, Principal

from src.caldav_client import _process_exdate, connect_to_caldav, get_calendar


class MockDatetime:
    """Mock class to simulate datetime objects from iCalendar."""

    def __init__(self, dt):
        """Init method to store the datetime object."""
        self.dt = dt

    def isoformat(self):
        """Implement isoformat to match datetime behavior."""
        return self.dt.isoformat()


class MockDt:
    """Mock class to simulate dt objects with dts attribute."""

    def __init__(self, dates):
        """Init method to store the list of datetime objects."""
        self.dts = [MockDatetime(dt) for dt in dates]


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


def test_connect_to_caldav_successful(mocker):
    """Test successful connection to CalDAV server."""
    mock_client = mocker.MagicMock(spec=DAVClient)
    mock_principal = mocker.MagicMock(spec=Principal)
    mock_client.principal.return_value = mock_principal

    mock_davclient = mocker.patch("src.caldav_client.DAVClient", return_value=mock_client)

    url = "https://caldav.example.com"
    username = "testuser"
    password = "testpass"

    result = connect_to_caldav(url, username, password)

    mock_davclient.assert_called_once_with(url, username=username, password=password)

    mock_client.principal.assert_called_once()

    assert result == mock_principal


def test_connect_to_caldav_authentication_error(mocker):
    """Test handling of authentication errors."""
    mock_client = mocker.MagicMock(spec=DAVClient)
    mock_client.principal.side_effect = Exception("Authentication failed")
    mocker.patch("src.caldav_client.DAVClient", return_value=mock_client)

    with pytest.raises(Exception, match="Authentication failed"):
        connect_to_caldav("https://caldav.example.com", "wronguser", "wrongpass")


def test_connect_to_caldav_connection_error(mocker):
    """Test handling of connection errors."""
    mocker.patch(
        "src.caldav_client.DAVClient",
        side_effect=Exception("Could not connect to server"),
    )

    with pytest.raises(Exception, match="Could not connect to server"):
        connect_to_caldav("https://invalid.example.com", "user", "pass")


def test_connect_to_caldav_invalid_url(mocker):
    """Test handling of invalid URL."""
    mocker.patch(
        "src.caldav_client.DAVClient",
        side_effect=ValueError("Invalid URL format"),
    )

    with pytest.raises(ValueError, match="Invalid URL format"):
        connect_to_caldav("not-a-url", "user", "pass")


def test_connect_to_caldav_empty_credentials(mocker):
    """Test handling of empty credentials."""
    mock_client = mocker.MagicMock(spec=DAVClient)
    mock_davclient = mocker.patch("src.caldav_client.DAVClient", return_value=mock_client)

    connect_to_caldav("https://caldav.example.com", "", "")

    mock_davclient.assert_called_once_with(
        "https://caldav.example.com",
        username="",
        password="",
    )


def test_connect_to_caldav_ssl_error(mocker):
    """Test handling of SSL certificate errors."""
    mocker.patch(
        "src.caldav_client.DAVClient",
        side_effect=Exception("SSL certificate verification failed"),
    )

    with pytest.raises(Exception, match="SSL certificate verification failed"):
        connect_to_caldav("https://selfsigned.example.com", "user", "pass")


def test_connect_to_caldav_timeout(mocker):
    """Test handling of connection timeout."""
    mocker.patch(
        "src.caldav_client.DAVClient",
        side_effect=Exception("Connection timed out"),
    )

    with pytest.raises(Exception, match="Connection timed out"):
        connect_to_caldav("https://slow.example.com", "user", "pass")


def test_process_exdate_none():
    """Test handling of None input."""
    assert _process_exdate(None) is None


def test_process_exdate_empty_list():
    """Test handling of empty list input."""
    assert _process_exdate([]) is None


def test_process_exdate_single_date():
    """Test processing a single date."""
    dt = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    mock_date = MockDatetime(dt)

    result = _process_exdate(mock_date)

    assert result == ["2024-01-01T10:00:00+00:00"]


def test_process_exdate_multiple_dates_list():
    """Test processing a list of dates."""
    dates = [
        datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 2, 11, 0, tzinfo=timezone.utc),
    ]
    mock_dates = [MockDatetime(dt) for dt in dates]

    result = _process_exdate(mock_dates)

    assert result == [
        "2024-01-01T10:00:00+00:00",
        "2024-01-02T11:00:00+00:00",
    ]


def test_process_exdate_vdddlists():
    """Test processing vDDDLists object."""
    dates = [
        datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 2, 11, 0, tzinfo=timezone.utc),
    ]
    mock_dt = MockDt(dates)

    result = _process_exdate(mock_dt)

    assert result == [
        "2024-01-01T10:00:00+00:00",
        "2024-01-02T11:00:00+00:00",
    ]


def test_process_exdate_list_of_vdddtypes():
    """Test processing a list containing vDDDTypes objects."""
    dates = [
        datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 2, 11, 0, tzinfo=timezone.utc),
    ]
    mock_dates = [MockDt([date]) for date in dates]

    result = _process_exdate(mock_dates)

    assert result == [
        "2024-01-01T10:00:00+00:00",
        "2024-01-02T11:00:00+00:00",
    ]


def test_process_exdate_invalid_input():
    """Test handling of invalid input types."""
    invalid_inputs = [
        42,
        "not a date",
        {"key": "value"},
    ]

    for invalid_input in invalid_inputs:
        result = _process_exdate(invalid_input)
        assert result is None


def test_process_exdate_mixed_valid_invalid():
    """Test processing a list with both valid and invalid date objects."""
    valid_dt = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    mock_valid = MockDatetime(valid_dt)
    mixed_list = [
        mock_valid,
        "invalid",
        42,
        {"not": "a date"},
    ]

    result = _process_exdate(mixed_list)

    assert result == ["2024-01-01T10:00:00+00:00"]


def test_process_exdate_nested_structure():
    """Test processing a nested structure of dates."""
    dates = [
        datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        datetime(2024, 1, 2, 11, 0, tzinfo=timezone.utc),
    ]
    mock_outer = MockDt(
        [
            MockDatetime(dates[0]),
            MockDatetime(dates[1]),
        ],
    )

    result = _process_exdate(mock_outer)

    assert result == [
        "2024-01-01T10:00:00+00:00",
        "2024-01-02T11:00:00+00:00",
    ]


def test_process_exdate_empty_dates_list():
    """Test processing an empty dates list in a vDDDLists object."""
    mock_dt = MockDt([])

    result = _process_exdate(mock_dt)

    assert result == []
