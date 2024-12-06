"""Tests for the connect_to_caldav function."""

from datetime import datetime, timezone
from unittest.mock import MagicMock

import pytest
from caldav import DAVClient, Principal
from icalendar import Calendar, Event

from src.caldav_client import _process_exdate, connect_to_caldav, fetch_events, get_calendar


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


def create_mock_event(  # noqa PLR0913
    uid,
    summary,
    start_time,
    end_time,
    last_modified=None,
    description=None,
    location=None,
    rrule=None,
    exdate=None,
    recurrence_id=None,
):
    """Create a mock CalDAV event."""
    event = Event()
    event.add("uid", uid)
    event.add("summary", summary)
    event.add("dtstart", start_time)
    event.add("dtend", end_time)

    if last_modified:
        event.add("last-modified", last_modified)
    if description:
        event.add("description", description)
    if location:
        event.add("location", location)
    if rrule:
        event.add("rrule", rrule)
    if exdate:
        event.add("exdate", exdate)
    if recurrence_id:
        event.add("recurrence-id", recurrence_id)

    cal = Calendar()
    cal.add_component(event)

    mock_event = MagicMock()
    mock_event.data = cal.to_ical()
    return mock_event


def test_fetch_events_single_event():
    """Test fetching a single simple event."""
    start_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end_time = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
    last_modified = datetime(2024, 1, 1, 9, 0, tzinfo=timezone.utc)

    mock_event = create_mock_event(
        uid="test-event-1",
        summary="Test Event",
        start_time=start_time,
        end_time=end_time,
        last_modified=last_modified,
        description="Test Description",
        location="Test Location",
    )

    mock_calendar = MagicMock()
    mock_calendar.name = "Test Calendar"
    mock_calendar.events.return_value = [mock_event]

    result = fetch_events(mock_calendar)

    assert len(result) == 1
    event = result["test-event-1"]
    assert event["uid"] == "test-event-1"
    assert event["summary"] == "Test Event"
    assert event["description"] == "Test Description"
    assert event["location"] == "Test Location"
    assert event["start"] == start_time.isoformat()
    assert event["end"] == end_time.isoformat()
    assert event["last_modified"] == last_modified.isoformat()
    assert event["rrule"] is None
    assert event["exdate"] is None
    assert event["recurrence_id"] is None


def test_fetch_events_recurring_event():
    """Test fetching a recurring event with exceptions."""
    start_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end_time = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)

    rrule = {
        "FREQ": ["WEEKLY"],
        "COUNT": [4],
        "BYDAY": ["MO", "WE", "FR"],
    }

    exdate = datetime(2024, 1, 8, 10, 0, tzinfo=timezone.utc)

    mock_event = create_mock_event(
        uid="recurring-event-1",
        summary="Recurring Meeting",
        start_time=start_time,
        end_time=end_time,
        rrule=rrule,
        exdate=exdate,
    )

    mock_calendar = MagicMock()
    mock_calendar.name = "Test Calendar"
    mock_calendar.events.return_value = [mock_event]

    result = fetch_events(mock_calendar)

    assert len(result) == 1
    event = result["recurring-event-1"]
    assert event["uid"] == "recurring-event-1"
    assert event["rrule"] == rrule
    assert event["exdate"] == [exdate.isoformat()]


def test_fetch_events_recurring_instance():
    """Test fetching a specific instance of a recurring event."""
    start_time = datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc)
    end_time = datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc)
    recurrence_id = datetime(2024, 1, 8, 10, 0, tzinfo=timezone.utc)

    mock_event = create_mock_event(
        uid="recurring-event-1",
        summary="Modified Instance",
        start_time=start_time,
        end_time=end_time,
        recurrence_id=recurrence_id,
    )

    mock_calendar = MagicMock()
    mock_calendar.name = "Test Calendar"
    mock_calendar.events.return_value = [mock_event]

    result = fetch_events(mock_calendar)

    assert len(result) == 1
    event_key = "recurring-event-1-2024-01-08T10:00:00+00:00"
    assert event_key in result
    assert result[event_key]["recurrence_id"] == recurrence_id.isoformat()


def test_fetch_events_multiple_events():
    """Test fetching multiple events with different properties."""
    events = [
        create_mock_event(
            uid="event-1",
            summary="Regular Event",
            start_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
        ),
        create_mock_event(
            uid="event-2",
            summary="Recurring Event",
            start_time=datetime(2024, 1, 2, 14, 0, tzinfo=timezone.utc),
            end_time=datetime(2024, 1, 2, 15, 0, tzinfo=timezone.utc),
            rrule={"FREQ": ["DAILY"], "COUNT": [3]},
        ),
    ]

    mock_calendar = MagicMock()
    mock_calendar.name = "Test Calendar"
    mock_calendar.events.return_value = events

    result = fetch_events(mock_calendar)

    assert len(result) == 2  # noqa PLR2004
    assert "event-1" in result
    assert "event-2" in result
    assert result["event-2"]["rrule"] == {"FREQ": ["DAILY"], "COUNT": [3]}


def test_fetch_events_empty_calendar():
    """Test fetching events from an empty calendar."""
    mock_calendar = MagicMock()
    mock_calendar.name = "Empty Calendar"
    mock_calendar.events.return_value = []

    result = fetch_events(mock_calendar)

    assert isinstance(result, dict)
    assert len(result) == 0


def test_fetch_events_error_handling():
    """Test handling of errors when fetching events."""
    mock_calendar = MagicMock()
    mock_calendar.name = "Test Calendar"
    mock_calendar.events.side_effect = Exception("Failed to fetch events")

    with pytest.raises(Exception, match="Failed to fetch events"):
        fetch_events(mock_calendar)


def test_fetch_events_malformed_event():
    """Test handling of malformed event data."""
    event1 = Event()
    event2 = Event()
    event2.add("uid", "good-event")

    cal1 = Calendar()
    cal1.add_component(event1)
    mock_event1 = MagicMock()
    mock_event1.data = cal1.to_ical()

    cal2 = Calendar()
    cal2.add_component(event2)
    mock_event2 = MagicMock()
    mock_event2.data = cal2.to_ical()

    mock_calendar = MagicMock()
    mock_calendar.name = "Test Calendar"
    mock_calendar.events.return_value = [mock_event1, mock_event2]

    result = fetch_events(mock_calendar)

    assert "good-event" in result
    assert result["good-event"]["start"] is None
    assert result["good-event"]["end"] is None


def test_fetch_events_with_empty_fields():
    """Test handling of events with empty optional fields."""
    mock_event = create_mock_event(
        uid="event-1",
        summary="Event With Empty Fields",
        start_time=datetime(2024, 1, 1, 10, 0, tzinfo=timezone.utc),
        end_time=datetime(2024, 1, 1, 11, 0, tzinfo=timezone.utc),
        description="",
        location="",
    )

    mock_calendar = MagicMock()
    mock_calendar.name = "Test Calendar"
    mock_calendar.events.return_value = [mock_event]

    result = fetch_events(mock_calendar)

    assert len(result) == 1
    event = result["event-1"]
    assert event["description"] == ""
    assert event["location"] == ""
