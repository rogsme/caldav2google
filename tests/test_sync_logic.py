"""Tests for the sync_logic module."""

from datetime import datetime, timezone

from src.sync_logic import _sanitize_event_for_json, compare_events


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
