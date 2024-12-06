"""Tests for the load_local_sync function in sync_logic module."""

import json
from datetime import datetime, timezone
from unittest.mock import call, mock_open, patch

import pytest

from src.sync_logic import (
    _create_google_event_body,
    _sanitize_event_for_json,
    add_event_to_google,
    compare_events,
    delete_event_from_google,
    error_events,
    load_local_sync,
)


@pytest.fixture
def sample_sync_data():
    """Create sample sync data for testing."""
    return {
        "test-uid-1": {
            "uid": "test-uid-1",
            "summary": "Test Event 1",
            "description": "Test Description",
            "start": "2024-01-01T10:00:00+00:00",
            "end": "2024-01-01T11:00:00+00:00",
            "last_modified": "2024-01-01T09:00:00+00:00",
            "google_event_id": "google-event-1",
        },
    }


@pytest.fixture
def mock_sleep():
    """Mock time.sleep to speed up tests."""
    with patch("time.sleep") as mock:
        yield mock


@pytest.fixture
def sample_event():
    """Create a sample event fixture."""
    return {
        "uid": "test-uid-1",
        "summary": "Test Event",
        "description": "Test Description",
        "location": "Test Location",
        "start": "2024-01-01T10:00:00+00:00",
        "end": "2024-01-01T11:00:00+00:00",
        "google_event_id": None,
    }


@pytest.fixture
def sample_event_for_deletion():
    """Create a sample event with Google Calendar ID."""
    return {
        "uid": "test-uid-1",
        "summary": "Event To Delete",
        "google_event_id": "google-event-123",
        "start": "2024-01-01T10:00:00+00:00",
        "end": "2024-01-01T11:00:00+00:00",
    }


@pytest.fixture
def mock_google_response():
    """Create a sample Google Calendar API response."""
    return {
        "id": "google-event-123",
        "status": "confirmed",
        "htmlLink": "https://calendar.google.com/event?id=123",
    }


def test_compare_events_new(sample_event_data):
    """Test comparing events with a new event."""
    local_events = {}
    server_events = sample_event_data

    new_events, updated_events, deleted_events = compare_events(local_events, server_events)

    assert len(new_events) == 1
    assert len(updated_events) == 0
    assert len(deleted_events) == 0
    assert new_events[0]["uid"] == "test-uid-1"


def test_compare_events_updated(sample_event_data):
    """Test comparing events with an updated event."""
    local_events = {
        "test-uid-1": {
            **sample_event_data["test-uid-1"],
            "last_modified": "2024-01-01T08:00:00+00:00",  # Earlier modification time
        },
    }
    server_events = sample_event_data

    new_events, updated_events, deleted_events = compare_events(local_events, server_events)

    assert len(new_events) == 0
    assert len(updated_events) == 1
    assert len(deleted_events) == 0
    assert updated_events[0]["uid"] == "test-uid-1"


def test_compare_events_deleted(sample_event_data):
    """Test comparing events with a deleted event."""
    local_events = sample_event_data
    server_events = {}

    new_events, updated_events, deleted_events = compare_events(local_events, server_events)

    assert len(new_events) == 0
    assert len(updated_events) == 0
    assert len(deleted_events) == 1
    assert deleted_events[0]["uid"] == "test-uid-1"


def test_sanitize_event_for_json(sample_event_data):
    """Test sanitizing an event for JSON serialization."""
    test_datetime = datetime(2024, 12, 31, tzinfo=timezone.utc)

    event = sample_event_data["test-uid-1"].copy()
    event["rrule"] = {
        "FREQ": "WEEKLY",
        "COUNT": 4,
        "UNTIL": test_datetime,
        "BYDAY": ["MO", "WE", "FR"],
    }

    sanitized = _sanitize_event_for_json(event)

    assert sanitized["rrule"]["FREQ"] == "WEEKLY"
    assert sanitized["rrule"]["COUNT"] == 4  # noqa PLR2004
    assert isinstance(sanitized["rrule"]["UNTIL"], datetime)
    assert sanitized["rrule"]["BYDAY"] == ["MO", "WE", "FR"]


def test_load_local_sync_file_exists(sample_sync_data):
    """Test loading sync data from an existing valid JSON file."""
    mock_json = json.dumps(sample_sync_data)

    with patch("builtins.open", mock_open(read_data=mock_json)), patch("os.path.exists", return_value=True):
        result = load_local_sync("fake_path.json")

    assert result == sample_sync_data
    assert len(result) == 1
    assert "test-uid-1" in result
    assert result["test-uid-1"]["summary"] == "Test Event 1"
    assert result["test-uid-1"]["google_event_id"] == "google-event-1"


def test_load_local_sync_file_not_exists():
    """Test loading sync data when file doesn't exist."""
    with patch("os.path.exists", return_value=False):
        result = load_local_sync("nonexistent.json")

    assert result == {}


def test_load_local_sync_invalid_json():
    """Test loading sync data from a corrupted JSON file."""
    invalid_json = "{ this is not valid json }"

    with patch("builtins.open", mock_open(read_data=invalid_json)), patch("os.path.exists", return_value=True):
        result = load_local_sync("corrupted.json")

    assert result == {}


def test_load_local_sync_file_read_error():
    """Test handling of file read errors."""
    with patch("os.path.exists", return_value=True), patch("builtins.open", side_effect=IOError("Mock IO Error")):
        result = load_local_sync("error.json")

    assert result == {}


def test_load_local_sync_empty_file():
    """Test loading sync data from an empty file."""
    with patch("builtins.open", mock_open(read_data="")), patch("os.path.exists", return_value=True):
        result = load_local_sync("empty.json")

    assert result == {}


def test_load_local_sync_whitespace_only():
    """Test loading sync data from a file containing only whitespace."""
    with patch("builtins.open", mock_open(read_data="   \n   \t   ")), patch("os.path.exists", return_value=True):
        result = load_local_sync("whitespace.json")

    assert result == {}


def test_create_google_event_body_basic():
    """Test creating a basic Google Calendar event body without recurrence."""
    event = {
        "summary": "Test Event",
        "description": "Test Description",
        "location": "Test Location",
        "start": "2024-01-01T10:00:00+00:00",
        "end": "2024-01-01T11:00:00+00:00",
    }

    result = _create_google_event_body(event)

    assert result["summary"] == "Test Event"
    assert result["description"] == "Test Description"
    assert result["location"] == "Test Location"
    assert result["start"] == {"dateTime": "2024-01-01T10:00:00+00:00", "timeZone": "UTC"}
    assert result["end"] == {"dateTime": "2024-01-01T11:00:00+00:00", "timeZone": "UTC"}


def test_create_google_event_body_minimal():
    """Test creating event body with minimal required fields."""
    event = {
        "summary": "Minimal Event",
        "start": "2024-01-01T10:00:00+00:00",
        "end": "2024-01-01T11:00:00+00:00",
    }

    result = _create_google_event_body(event)

    assert result["summary"] == "Minimal Event"
    assert result["description"] == ""
    assert result["location"] == ""
    assert result["start"] == {"dateTime": "2024-01-01T10:00:00+00:00", "timeZone": "UTC"}
    assert result["end"] == {"dateTime": "2024-01-01T11:00:00+00:00", "timeZone": "UTC"}


def test_create_google_event_body_with_rrule():
    """Test creating event body with recurrence rule."""
    event = {
        "summary": "Recurring Event",
        "start": "2024-01-01T10:00:00+00:00",
        "end": "2024-01-01T11:00:00+00:00",
        "rrule": {
            "FREQ": "WEEKLY",
            "COUNT": 4,
            "BYDAY": ["MO", "WE", "FR"],
        },
    }

    result = _create_google_event_body(event)

    assert "recurrence" in result
    assert len(result["recurrence"]) == 1
    assert result["recurrence"][0].startswith("RRULE:")
    assert "FREQ=WEEKLY" in result["recurrence"][0]
    assert "COUNT=4" in result["recurrence"][0]
    assert "BYDAY=MO,WE,FR" in result["recurrence"][0]


def test_create_google_event_body_with_rrule_and_exdate():
    """Test creating event body with recurrence rule and exclusion dates."""
    event = {
        "summary": "Recurring Event with Exclusions",
        "start": "2024-01-01T10:00:00+00:00",
        "end": "2024-01-01T11:00:00+00:00",
        "rrule": {
            "FREQ": "WEEKLY",
            "COUNT": 4,
        },
        "exdate": [
            "2024-01-08T10:00:00+00:00",
            "2024-01-15T10:00:00+00:00",
        ],
    }

    result = _create_google_event_body(event)

    assert len(result["recurrence"]) == 3  # noqa PLR2004
    assert result["recurrence"][0].startswith("RRULE:")
    assert result["recurrence"][1] == "EXDATE;TZID=UTC:2024-01-08T10:00:00+00:00"
    assert result["recurrence"][2] == "EXDATE;TZID=UTC:2024-01-15T10:00:00+00:00"


def test_create_google_event_body_with_datetime_in_rrule():
    """Test creating event body with datetime objects in recurrence rule."""
    until_date = datetime(2024, 12, 31, tzinfo=timezone.utc)
    event = {
        "summary": "Event with DateTime",
        "start": "2024-01-01T10:00:00+00:00",
        "end": "2024-01-01T11:00:00+00:00",
        "rrule": {
            "FREQ": "WEEKLY",
            "UNTIL": until_date,
        },
    }

    result = _create_google_event_body(event)

    assert "recurrence" in result
    assert "UNTIL=2024-12-31" in result["recurrence"][0]


def test_add_new_event_to_google(mock_google_service, sample_event, mock_google_response, mock_sleep):
    """Test adding a new event to Google Calendar."""
    # Setup mock
    events = mock_google_service.events.return_value
    insert = events.insert.return_value
    insert.execute.return_value = mock_google_response

    # Clear any previous error events
    error_events.clear()

    # Execute
    add_event_to_google(mock_google_service, sample_event, "calendar-id")

    # Verify
    events.insert.assert_called_once()
    insert.execute.assert_called_once()
    assert sample_event["google_event_id"] == "google-event-123"
    assert len(error_events) == 0
    mock_sleep.assert_called_once_with(0.5)


def test_update_existing_event_in_google(mock_google_service, sample_event, mock_google_response, mock_sleep):
    """Test updating an existing event in Google Calendar."""
    # Modify sample event to include google_event_id
    sample_event["google_event_id"] = "existing-event-id"

    # Setup mock
    events = mock_google_service.events.return_value
    update = events.update.return_value
    update.execute.return_value = mock_google_response

    # Clear any previous error events
    error_events.clear()

    # Execute
    add_event_to_google(mock_google_service, sample_event, "calendar-id")

    # Verify
    events.update.assert_called_once()
    update.execute.assert_called_once()
    assert len(error_events) == 0
    mock_sleep.assert_called_once_with(0.5)


def test_add_event_to_google_api_error(mock_google_service, sample_event, mock_sleep):
    """Test handling of API errors when adding event to Google Calendar."""
    # Setup mock to raise an exception
    events = mock_google_service.events.return_value
    insert = events.insert.return_value
    insert.execute.side_effect = Exception("API Error")

    # Clear any previous error events
    error_events.clear()

    # Execute
    add_event_to_google(mock_google_service, sample_event, "calendar-id")

    # Verify
    events.insert.assert_called_once()
    insert.execute.assert_called_once()
    assert len(error_events) == 1
    assert error_events[0] == sample_event
    mock_sleep.assert_called_once_with(0.5)


def test_add_recurring_event_to_google(mock_google_service, sample_event, mock_google_response, mock_sleep):
    """Test adding a recurring event to Google Calendar."""
    # Add recurrence rule to sample event
    sample_event["rrule"] = {
        "FREQ": "WEEKLY",
        "COUNT": 4,
        "BYDAY": ["MO", "WE", "FR"],
    }

    # Setup mock
    events = mock_google_service.events.return_value
    insert = events.insert.return_value
    insert.execute.return_value = mock_google_response

    # Clear any previous error events
    error_events.clear()

    # Execute
    add_event_to_google(mock_google_service, sample_event, "calendar-id")

    # Verify
    events.insert.assert_called_once()
    call_args = events.insert.call_args[1]
    assert "recurrence" in call_args["body"]
    assert "RRULE:" in call_args["body"]["recurrence"][0]
    assert sample_event["google_event_id"] == "google-event-123"
    assert len(error_events) == 0
    mock_sleep.assert_called_once_with(0.5)


def test_update_event_with_api_error(mock_google_service, sample_event, mock_sleep):
    """Test handling of API errors when updating an existing event."""
    # Setup event with existing Google ID
    sample_event["google_event_id"] = "existing-event-id"

    # Setup mock to raise an exception
    events = mock_google_service.events.return_value
    update = events.update.return_value
    update.execute.side_effect = Exception("Update API Error")

    # Clear any previous error events
    error_events.clear()

    # Execute
    add_event_to_google(mock_google_service, sample_event, "calendar-id")

    # Verify
    events.update.assert_called_once()
    update.execute.assert_called_once()
    assert len(error_events) == 1
    assert error_events[0] == sample_event
    mock_sleep.assert_called_once_with(0.5)


def test_add_event_verifies_required_fields(mock_google_service, mock_sleep):
    """Test that adding event with missing required fields is handled properly."""
    # Create event missing required fields
    incomplete_event = {
        "uid": "test-uid-1",
        "summary": "Test Event",
        # Missing start and end times
    }

    # Setup mock
    events = mock_google_service.events.return_value
    insert = events.insert.return_value
    insert.execute.return_value = {"id": "new-id"}

    # Clear any previous error events
    error_events.clear()

    # Execute
    add_event_to_google(mock_google_service, incomplete_event, "calendar-id")

    # Verify
    assert len(error_events) == 1
    assert error_events[0] == incomplete_event
    mock_sleep.assert_called_once_with(0.5)


def test_delete_event_successful(mock_google_service, sample_event_for_deletion, mock_sleep):
    """Test successful deletion of an event from Google Calendar."""
    # Setup mock
    events = mock_google_service.events.return_value
    delete = events.delete.return_value
    delete.execute.return_value = None  # Delete operation returns None on success

    # Execute
    delete_event_from_google(mock_google_service, sample_event_for_deletion, "calendar-id")

    # Verify
    events.delete.assert_called_once_with(
        calendarId="calendar-id",
        eventId="google-event-123",
    )
    delete.execute.assert_called_once()
    mock_sleep.assert_called_once_with(0.5)


def test_delete_event_no_google_id(mock_google_service, mock_sleep):
    """Test attempting to delete an event with no Google Calendar ID."""
    event_without_id = {
        "uid": "test-uid-1",
        "summary": "Event Without Google ID",
        "google_event_id": None,
    }

    # Execute
    delete_event_from_google(mock_google_service, event_without_id, "calendar-id")

    # Verify
    mock_google_service.events.return_value.delete.assert_not_called()
    mock_sleep.assert_called_once_with(0.5)


def test_delete_event_api_error(mock_google_service, sample_event_for_deletion, mock_sleep):
    """Test handling of API errors when deleting an event."""
    # Setup mock to raise an exception
    events = mock_google_service.events.return_value
    delete = events.delete.return_value
    delete.execute.side_effect = Exception("API Error")

    # Execute
    delete_event_from_google(mock_google_service, sample_event_for_deletion, "calendar-id")

    # Verify
    events.delete.assert_called_once()
    delete.execute.assert_called_once()
    mock_sleep.assert_called_once_with(0.5)


def test_delete_event_empty_id(mock_google_service, mock_sleep):
    """Test attempting to delete an event with an empty Google Calendar ID."""
    event_empty_id = {
        "uid": "test-uid-1",
        "summary": "Event With Empty ID",
        "google_event_id": "",
    }

    # Execute
    delete_event_from_google(mock_google_service, event_empty_id, "calendar-id")

    # Verify
    mock_google_service.events.return_value.delete.assert_not_called()
    mock_sleep.assert_called_once_with(0.5)


def test_delete_multiple_events_rate_limiting(mock_google_service, sample_event_for_deletion, mock_sleep):
    """Test rate limiting when deleting multiple events."""
    # Create two events
    event1 = sample_event_for_deletion
    event2 = {**sample_event_for_deletion, "google_event_id": "google-event-456"}

    # Execute
    delete_event_from_google(mock_google_service, event1, "calendar-id")
    delete_event_from_google(mock_google_service, event2, "calendar-id")

    # Verify
    assert mock_sleep.call_count == 2  # noqa PLR2004
    mock_sleep.assert_has_calls(
        [
            call(0.5),
            call(0.5),
        ],
    )


def test_delete_event_missing_required_fields(mock_google_service, mock_sleep):
    """Test attempting to delete an event with missing required fields."""
    incomplete_event = {
        # Missing summary and uid
        "google_event_id": "google-event-123",
    }

    # Execute
    delete_event_from_google(mock_google_service, incomplete_event, "calendar-id")

    # Verify
    mock_google_service.events.return_value.delete.assert_called_once()
    mock_sleep.assert_called_once_with(0.5)
