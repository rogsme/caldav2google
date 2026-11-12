"""Tests for the auth_google module."""

import pickle
from types import SimpleNamespace

import pytest
from google.auth.exceptions import RefreshError

from src import auth_google
from src.auth_google import authenticate_google, search_calendar_id


class FakeCreds:
    """Picklable stand-in for google.oauth2.credentials.Credentials."""

    def __init__(self, valid=False, expired=True, refresh_token="refresh-token", refresh_error=False):
        """Store the state that authenticate_google inspects."""
        self.valid = valid
        self.expired = expired
        self.refresh_token = refresh_token
        self.refresh_error = refresh_error
        self.refreshed = False

    def refresh(self, request):  # noqa: ARG002
        """Simulate a token refresh, optionally failing like a revoked refresh token."""
        if self.refresh_error:
            raise RefreshError("invalid_grant: Token has been expired or revoked.")
        self.refreshed = True
        self.valid = True
        self.expired = False


@pytest.fixture
def auth_env(tmp_path, monkeypatch, mocker):
    """Run in a temp dir with build and the OAuth flow mocked out."""
    monkeypatch.chdir(tmp_path)
    build = mocker.patch.object(auth_google, "build", return_value="service")
    flow_creds = FakeCreds(valid=True, expired=False)
    flow = mocker.patch.object(auth_google, "InstalledAppFlow")
    flow.from_client_secrets_file.return_value.run_local_server.return_value = flow_creds
    return SimpleNamespace(build=build, flow=flow, flow_creds=flow_creds)


def _write_token(creds):
    with open(auth_google.TOKEN_FILE, "wb") as token:
        pickle.dump(creds, token)


def _read_token():
    with open(auth_google.TOKEN_FILE, "rb") as token:
        return pickle.load(token)


def _set_interactive(mocker, interactive):
    mocker.patch.object(auth_google, "_is_interactive", return_value=interactive)


def test_authenticate_google_valid_token(auth_env, mocker):
    """A valid token is used as-is, without refreshing or starting the OAuth flow."""
    _set_interactive(mocker, False)
    _write_token(FakeCreds(valid=True, expired=False))

    assert authenticate_google() == "service"
    auth_env.flow.from_client_secrets_file.assert_not_called()


def test_authenticate_google_refreshes_and_saves(auth_env, mocker):
    """An expired token is refreshed without a terminal and the refreshed token is saved."""
    _set_interactive(mocker, False)
    _write_token(FakeCreds())

    assert authenticate_google() == "service"
    assert _read_token().refreshed
    auth_env.flow.from_client_secrets_file.assert_not_called()


def test_authenticate_google_refresh_error_headless(auth_env, mocker, caplog):
    """A revoked refresh token without a terminal logs how to fix it and re-raises."""
    _set_interactive(mocker, False)
    _write_token(FakeCreds(refresh_error=True))

    with pytest.raises(RefreshError):
        authenticate_google()
    assert "In production" in caplog.text
    auth_env.flow.from_client_secrets_file.assert_not_called()


def test_authenticate_google_refresh_error_interactive(auth_env, mocker):
    """A revoked refresh token with a terminal falls back to the OAuth flow."""
    _set_interactive(mocker, True)
    _write_token(FakeCreds(refresh_error=True))

    assert authenticate_google() == "service"
    auth_env.flow.from_client_secrets_file.assert_called_once()
    assert _read_token().valid


def test_authenticate_google_no_token_headless(auth_env, mocker):
    """Without a token or a terminal, fail fast instead of waiting for a browser."""
    _set_interactive(mocker, False)

    with pytest.raises(RuntimeError, match="no terminal"):
        authenticate_google()
    auth_env.flow.from_client_secrets_file.assert_not_called()


def test_authenticate_google_no_token_interactive(auth_env, mocker):
    """Without a token but with a terminal, run the OAuth flow and save the token."""
    _set_interactive(mocker, True)

    assert authenticate_google() == "service"
    auth_env.flow.from_client_secrets_file.assert_called_once_with(auth_google.CREDENTIALS_FILE, auth_google.SCOPES)
    assert _read_token().valid


@pytest.mark.usefixtures("auth_env")
def test_authenticate_google_no_refresh_token_headless(mocker):
    """An expired token without a refresh token cannot be renewed headless."""
    _set_interactive(mocker, False)
    _write_token(FakeCreds(refresh_token=None))

    with pytest.raises(RuntimeError):
        authenticate_google()


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
