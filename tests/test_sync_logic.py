"""Tests for the load_local_sync function in sync_logic module."""

import json
from datetime import datetime, timezone
from unittest.mock import mock_open, patch

import pytest

from src.sync_logic import _sanitize_event_for_json, compare_events, load_local_sync


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
