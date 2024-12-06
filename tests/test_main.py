"""Tests for the main module."""

from unittest.mock import MagicMock, patch

import pytest

from src.main import main


@pytest.fixture
def mock_env_vars(monkeypatch):
    """Fixture to mock environment variables."""
    monkeypatch.setenv("CALDAV_URL", "http://mock-caldav-url.com")
    monkeypatch.setenv("CALDAV_USERNAME", "mock_user")
    monkeypatch.setenv("CALDAV_PASSWORD", "mock_password")
    monkeypatch.setenv("CALDAV_CALENDAR_NAME", "Mock CalDAV Calendar")
    monkeypatch.setenv("GOOGLE_CALENDAR_NAME", "Mock Google Calendar")


@patch("src.main.authenticate_google")
@patch("src.main.search_calendar_id")
@patch("src.main.connect_to_caldav")
@patch("src.main.get_calendar")
@patch("src.main.fetch_events")
@patch("src.main.load_local_sync")
@patch("src.main.compare_events")
@patch("src.main.add_event_to_google")
@patch("src.main.delete_event_from_google")
@patch("src.main.save_local_sync")
def test_main(  # noqa PLR0913
    mock_save_local_sync,
    mock_delete_event_from_google,  # noqa ARG001
    mock_add_event_to_google,
    mock_compare_events,
    mock_load_local_sync,
    mock_fetch_events,
    mock_get_calendar,
    mock_connect_to_caldav,
    mock_search_calendar_id,
    mock_authenticate_google,
    mock_env_vars,  # noqa ARG001
):
    """Test the main function with mocked dependencies."""
    # Mock returns
    mock_authenticate_google.return_value = "mock_service"
    mock_search_calendar_id.return_value = "mock_google_calendar_id"
    mock_connect_to_caldav.return_value = "mock_principal"
    mock_get_calendar.return_value = MagicMock(name="Mock CalDAV Calendar")
    mock_fetch_events.return_value = [{"uid": "event1"}, {"uid": "event2"}]
    mock_load_local_sync.return_value = [{"uid": "event1"}]
    mock_compare_events.return_value = (
        [{"uid": "event2"}],  # new events
        [],  # updated events
        [],  # deleted events
    )

    # Call the main function
    main()

    # Assert calls
    mock_authenticate_google.assert_called_once()
    mock_search_calendar_id.assert_called_once_with("mock_service", "Mock Google Calendar")
    mock_connect_to_caldav.assert_called_once_with(
        "http://mock-caldav-url.com",
        "mock_user",
        "mock_password",
    )
    mock_get_calendar.assert_called_once_with("mock_principal", "Mock CalDAV Calendar")
    mock_fetch_events.assert_called_once_with(mock_get_calendar.return_value)
    mock_load_local_sync.assert_called_once_with("calendar_sync.json")
    mock_compare_events.assert_called_once_with(
        mock_load_local_sync.return_value,
        mock_fetch_events.return_value,
    )
    mock_add_event_to_google.assert_called_once_with(
        "mock_service",
        {"uid": "event2"},
        "mock_google_calendar_id",
    )
    mock_save_local_sync.assert_called_once_with(
        "calendar_sync.json",
        mock_fetch_events.return_value,
    )


@patch("src.main.logger.error")
def test_main_exception(mock_logger_error, mock_env_vars):  # noqa ARG001
    """Test the main function handles exceptions gracefully."""
    with (
        patch("src.main.authenticate_google", side_effect=Exception("Mock error")),
        pytest.raises(Exception, match="Mock error"),
    ):
        main()

    mock_logger_error.assert_called_once_with(
        "Error occurred during sync: Mock error",
        exc_info=True,
    )
