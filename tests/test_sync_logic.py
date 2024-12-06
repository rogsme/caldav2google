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
    save_local_sync,
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
    events = mock_google_service.events.return_value
    insert = events.insert.return_value
    insert.execute.return_value = mock_google_response

    error_events.clear()

    add_event_to_google(mock_google_service, sample_event, "calendar-id")

    events.insert.assert_called_once()
    insert.execute.assert_called_once()
    assert sample_event["google_event_id"] == "google-event-123"
    assert len(error_events) == 0
    mock_sleep.assert_called_once_with(0.5)


def test_update_existing_event_in_google(mock_google_service, sample_event, mock_google_response, mock_sleep):
    """Test updating an existing event in Google Calendar."""
    sample_event["google_event_id"] = "existing-event-id"

    events = mock_google_service.events.return_value
    update = events.update.return_value
    update.execute.return_value = mock_google_response

    error_events.clear()

    add_event_to_google(mock_google_service, sample_event, "calendar-id")

    events.update.assert_called_once()
    update.execute.assert_called_once()
    assert len(error_events) == 0
    mock_sleep.assert_called_once_with(0.5)


def test_add_event_to_google_api_error(mock_google_service, sample_event, mock_sleep):
    """Test handling of API errors when adding event to Google Calendar."""
    events = mock_google_service.events.return_value
    insert = events.insert.return_value
    insert.execute.side_effect = Exception("API Error")

    error_events.clear()

    add_event_to_google(mock_google_service, sample_event, "calendar-id")

    events.insert.assert_called_once()
    insert.execute.assert_called_once()
    assert len(error_events) == 1
    assert error_events[0] == sample_event
    mock_sleep.assert_called_once_with(0.5)


def test_add_recurring_event_to_google(mock_google_service, sample_event, mock_google_response, mock_sleep):
    """Test adding a recurring event to Google Calendar."""
    sample_event["rrule"] = {
        "FREQ": "WEEKLY",
        "COUNT": 4,
        "BYDAY": ["MO", "WE", "FR"],
    }

    events = mock_google_service.events.return_value
    insert = events.insert.return_value
    insert.execute.return_value = mock_google_response

    error_events.clear()

    add_event_to_google(mock_google_service, sample_event, "calendar-id")

    events.insert.assert_called_once()
    call_args = events.insert.call_args[1]
    assert "recurrence" in call_args["body"]
    assert "RRULE:" in call_args["body"]["recurrence"][0]
    assert sample_event["google_event_id"] == "google-event-123"
    assert len(error_events) == 0
    mock_sleep.assert_called_once_with(0.5)


def test_update_event_with_api_error(mock_google_service, sample_event, mock_sleep):
    """Test handling of API errors when updating an existing event."""
    sample_event["google_event_id"] = "existing-event-id"

    events = mock_google_service.events.return_value
    update = events.update.return_value
    update.execute.side_effect = Exception("Update API Error")

    error_events.clear()

    add_event_to_google(mock_google_service, sample_event, "calendar-id")

    events.update.assert_called_once()
    update.execute.assert_called_once()
    assert len(error_events) == 1
    assert error_events[0] == sample_event
    mock_sleep.assert_called_once_with(0.5)


def test_add_event_verifies_required_fields(mock_google_service, mock_sleep):
    """Test that adding event with missing required fields is handled properly."""
    incomplete_event = {
        "uid": "test-uid-1",
        "summary": "Test Event",
    }

    events = mock_google_service.events.return_value
    insert = events.insert.return_value
    insert.execute.return_value = {"id": "new-id"}

    error_events.clear()

    add_event_to_google(mock_google_service, incomplete_event, "calendar-id")

    assert len(error_events) == 1
    assert error_events[0] == incomplete_event
    mock_sleep.assert_called_once_with(0.5)


def test_delete_event_successful(mock_google_service, sample_event_for_deletion, mock_sleep):
    """Test successful deletion of an event from Google Calendar."""
    events = mock_google_service.events.return_value
    delete = events.delete.return_value
    delete.execute.return_value = None  # Delete operation returns None on success

    delete_event_from_google(mock_google_service, sample_event_for_deletion, "calendar-id")

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

    delete_event_from_google(mock_google_service, event_without_id, "calendar-id")

    mock_google_service.events.return_value.delete.assert_not_called()
    mock_sleep.assert_called_once_with(0.5)


def test_delete_event_api_error(mock_google_service, sample_event_for_deletion, mock_sleep):
    """Test handling of API errors when deleting an event."""
    events = mock_google_service.events.return_value
    delete = events.delete.return_value
    delete.execute.side_effect = Exception("API Error")

    delete_event_from_google(mock_google_service, sample_event_for_deletion, "calendar-id")

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

    delete_event_from_google(mock_google_service, event_empty_id, "calendar-id")

    mock_google_service.events.return_value.delete.assert_not_called()
    mock_sleep.assert_called_once_with(0.5)


def test_delete_multiple_events_rate_limiting(mock_google_service, sample_event_for_deletion, mock_sleep):
    """Test rate limiting when deleting multiple events."""
    event1 = sample_event_for_deletion
    event2 = {**sample_event_for_deletion, "google_event_id": "google-event-456"}

    delete_event_from_google(mock_google_service, event1, "calendar-id")
    delete_event_from_google(mock_google_service, event2, "calendar-id")

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
        "google_event_id": "google-event-123",
    }

    delete_event_from_google(mock_google_service, incomplete_event, "calendar-id")

    mock_google_service.events.return_value.delete.assert_called_once()
    mock_sleep.assert_called_once_with(0.5)


@pytest.fixture
def sample_events():
    """Create sample events for testing."""
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


def test_save_local_sync_basic(sample_events):
    """Test basic saving of events to a file."""
    m = mock_open()

    with patch("builtins.open", m):
        save_local_sync("test.json", sample_events)

    write_calls = [call[0][0] for call in m().write.call_args_list]

    written_data = "".join(write_calls)

    saved_events = json.loads(written_data)

    assert "test-uid-1" in saved_events
    assert saved_events["test-uid-1"]["summary"] == "Test Event 1"
    assert saved_events["test-uid-1"]["google_event_id"] == "google-event-1"


def test_save_local_sync_empty_events():
    """Test saving an empty events dictionary."""
    m = mock_open()

    with patch("builtins.open", m):
        save_local_sync("test.json", {})

    write_calls = [call[0][0] for call in m().write.call_args_list]
    written_data = "".join(write_calls)
    saved_events = json.loads(written_data)
    assert saved_events == {}


def test_save_local_sync_unicode_characters():
    """Test saving events with unicode characters."""
    events = {
        "test-uid-1": {
            "summary": "Test Event with Unicode ñáéíóú",
            "description": "Description with emojis 🎉🎊",
            "location": "Location with characters デパート",
        },
    }

    m = mock_open()

    with patch("builtins.open", m):
        save_local_sync("test.json", events)

    write_calls = [call[0][0] for call in m().write.call_args_list]
    written_data = "".join(write_calls)
    saved_events = json.loads(written_data)

    assert saved_events["test-uid-1"]["summary"] == "Test Event with Unicode ñáéíóú"
    assert saved_events["test-uid-1"]["description"] == "Description with emojis 🎉🎊"
    assert saved_events["test-uid-1"]["location"] == "Location with characters デパート"


def test_save_local_sync_nested_data():
    """Test saving events with deeply nested data structures."""
    events = {
        "test-uid-1": {
            "summary": "Nested Event",
            "metadata": {
                "categories": ["work", "important"],
                "tags": {
                    "priority": "high",
                    "project": {
                        "name": "Test Project",
                        "phase": 1,
                    },
                },
            },
        },
    }

    m = mock_open()

    with patch("builtins.open", m):
        save_local_sync("test.json", events)

    write_calls = [call[0][0] for call in m().write.call_args_list]
    written_data = "".join(write_calls)
    saved_events = json.loads(written_data)

    assert saved_events["test-uid-1"]["metadata"]["categories"] == ["work", "important"]
    assert saved_events["test-uid-1"]["metadata"]["tags"]["priority"] == "high"
    assert saved_events["test-uid-1"]["metadata"]["tags"]["project"]["name"] == "Test Project"


def test_save_local_sync_write_error():
    """Test handling of file write errors."""
    m = mock_open()
    m.side_effect = IOError("Mock write error")

    with patch("builtins.open", m):
        save_local_sync("test.json", {"test-uid-1": {"summary": "Test Event"}})


def test_save_local_sync_sanitization():
    """Test that event data is properly sanitized before saving."""
    events = {
        "test-uid-1": {
            "summary": "Test Event",
            "rrule": {
                "FREQ": "WEEKLY",
                "COUNT": 4,
                "UNTIL": "2024-12-31T00:00:00+00:00",  # Changed from datetime to string
                "BYDAY": ["MO", "WE", "FR"],
            },
        },
    }

    m = mock_open()

    with patch("builtins.open", m):
        save_local_sync("test.json", events)

    write_calls = [call[0][0] for call in m().write.call_args_list]
    written_data = "".join(write_calls)
    saved_events = json.loads(written_data)

    assert "test-uid-1" in saved_events
    assert isinstance(saved_events["test-uid-1"]["rrule"], dict)
    assert saved_events["test-uid-1"]["rrule"]["FREQ"] == "WEEKLY"
    assert saved_events["test-uid-1"]["rrule"]["COUNT"] == 4  # noqa PLR2004
    assert saved_events["test-uid-1"]["rrule"]["UNTIL"] == "2024-12-31T00:00:00+00:00"
    assert saved_events["test-uid-1"]["rrule"]["BYDAY"] == ["MO", "WE", "FR"]


def test_save_local_sync_sanitize_error():
    """Test handling of event sanitization failures."""
    events = {
        "valid-event": {
            "uid": "valid-event",
            "summary": "Valid Event",
            "description": "This event should be saved",
        },
        "problem-event": {
            "uid": "problem-event",
            "summary": "Problem Event",
            "rrule": {
                "FREQ": "WEEKLY",
                "UNTIL": "2024-12-31T00:00:00+00:00",
            },
        },
    }

    def mock_sanitize(event_data):
        """Mock sanitization that fails for the problem event."""
        if event_data.get("uid") == "problem-event":
            raise ValueError("Mock sanitization error")
        return event_data.copy()

    m = mock_open()

    with patch("builtins.open", m), patch("src.sync_logic._sanitize_event_for_json", side_effect=mock_sanitize):
        save_local_sync("test.json", events)

    assert m().write.called

    write_calls = [call[0][0] for call in m().write.call_args_list]
    written_data = "".join(write_calls)
    saved_events = json.loads(written_data)

    assert "valid-event" in saved_events
    assert "problem-event" not in saved_events
    assert saved_events["valid-event"]["summary"] == "Valid Event"
    assert saved_events["valid-event"]["description"] == "This event should be saved"


def test_save_local_sync_type_error_handling():
    """Test handling of TypeError during JSON serialization and problematic field identification."""

    class UnserializableObject:
        def __str__(self):
            return "test object"

    events = {
        "problem-event": {
            "uid": "problem-event",
            "summary": "Event With Bad Data",
            "normal_field": "This is fine",
            "bad_field": UnserializableObject(),  # This will cause TypeError
            "another_bad_field": [1, 2, 3],  # This will also cause TypeError
        },
    }

    m = mock_open()

    with patch("builtins.open", m), patch("src.logger.logging.Logger.error") as mock_logger_error:
        save_local_sync("test.json", events)

    error_calls = mock_logger_error.call_args_list

    assert any(
        "Failed to save sync file: Object of type UnserializableObject is not JSON serializable" in str(call)
        for call in error_calls
    )
    assert any("JSON serialization failed for event: problem-event" in str(call) for call in error_calls)
    assert any("Event summary: Event With Bad Data" in str(call) for call in error_calls)

    assert any("bad_field" in str(call) and "UnserializableObject" in str(call) for call in error_calls)

    assert m().write.called


def test_save_local_sync_invalid_data_handling():
    """Test handling of non-serializable data types."""
    events = {
        "test-uid-1": {
            "summary": "Valid Event",
        },
        "test-uid-2": {
            "summary": "Invalid Event",
            "invalid_data": [1, 2, 3],
        },
    }

    m = mock_open()

    with patch("builtins.open", m):
        save_local_sync("test.json", events)

    assert m().write.called
