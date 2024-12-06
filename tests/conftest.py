"""Fixtures for testing caldav2google."""

from unittest.mock import MagicMock

import pytest


@pytest.fixture
def mock_google_service():
    """Create a mock Google Calendar service."""
    service = MagicMock()
    events = MagicMock()
    service.events.return_value = events
    return service


@pytest.fixture
def mock_caldav_principal():
    """Create a mock CalDAV principal."""
    return MagicMock()


@pytest.fixture
def sample_event_data():
    """Create sample event data for testing."""
    return {
        "test-uid-1": {
            "uid": "test-uid-1",
            "summary": "Test Event 1",
            "description": "Test Description",
            "location": "Test Location",
            "start": "2024-01-01T10:00:00+00:00",
            "end": "2024-01-01T11:00:00+00:00",
            "last_modified": "2024-01-01T09:00:00+00:00",
            "rrule": None,
            "exdate": None,
            "recurrence_id": None,
            "google_event_id": "google-event-1",
        },
    }
