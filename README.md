# CalDAV2GoogleCalendar

<p align="center">
  <img src="https://gitlab.com/uploads/-/system/project/avatar/64798757/logo.jpg" alt="caldav2google"/>
</p>

[![codecov](https://codecov.io/gl/rogs/caldav2google/graph/badge.svg?token=W12CFCUKP0)](https://codecov.io/gl/rogs/caldav2google)
[![CI](https://git.rogs.me/rogs/caldav2google/actions/workflows/ci.yml/badge.svg)](https://git.rogs.me/rogs/caldav2google/actions)

A Python utility to synchronize events from a CalDAV calendar to Google Calendar, maintaining a local state to track changes.

## Features
- One-way synchronization from CalDAV to Google Calendar
- Intelligent change detection using event UIDs and modification timestamps:
  - Adds new events not present in Google Calendar
  - Updates modified events based on last-modified timestamp
  - Removes events deleted from CalDAV source
- Local state management via JSON file to track synchronized events
- Detailed logging of synchronization activities
- Built-in rate limiting (0.5s delay between API calls) to prevent Google Calendar API throttling
- Comprehensive error tracking with failed events reporting
- UTC timezone handling for consistent event timing

## Prerequisites

### 1. Python Environment
- Python 3.9 or higher
- Poetry for dependency management
- Required Python packages (automatically installed via Poetry):
  - `caldav` (^1.4.0) - For CalDAV server interaction
  - `icalendar` (^6.1.0) - For iCalendar format parsing
  - `google-api-python-client` (^2.154.0) - For Google Calendar API
  - `python-dotenv` (^1.0.1) - For environment variable management

### 2. CalDAV Server Details
You'll need:
- CalDAV server URL
- Username
- Password
- Calendar name to synchronize (case-insensitive matching)

### 3. Google Calendar Setup

To interact with the Google Calendar API, follow these steps:

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Create a new project or select an existing one.
3. Enable the **Google Calendar API** for the project.
4. Create OAuth 2.0 credentials:
   - Go to **APIs & Services > Credentials**.
   - Click **Create Credentials** > **OAuth Client ID**.
   - Configure the consent screen (if not already done).
   - Select **Desktop App** as the application type.
   - Download the `credentials.json` file.
5. Place the `credentials.json` file in the project directory.

## Installation

1. Clone the repository:
   ```bash
   git clone https://gitlab.com/rogs/caldav2google.git
   cd caldav2google
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Create `.env` file (copy from env.example):
   ```env
   CALDAV_URL=https://your-caldav-server.com
   CALDAV_USERNAME=your_username
   CALDAV_PASSWORD=your_password
   CALDAV_CALENDAR_NAME=your_calendar_name
   GOOGLE_CALENDAR_NAME=target_google_calendar_name
   ```

## Usage

1. Activate virtual environment:
   ```bash
   poetry shell
   ```

2. Run synchronization:
   ```bash
   PYTHONPATH=. python src/main.py
   ```

On first run:
- Browser opens for Google OAuth authentication
- Grant requested calendar permissions
- Token is saved as `token.pickle` for future use

## Testing

To run the test suite:

```bash
poetry run pytest
```

This will run all tests in the `tests/` directory.

To generate a test coverage report:

```bash
poetry run pytest --cov=src tests/
```

## Project Structure

```
src/
├── auth_google.py      # Google Calendar authentication & calendar search
├── caldav_client.py    # CalDAV server connections & event fetching
├── main.py             # Main synchronization orchestration
├── sync_logic.py       # Core synchronization & event comparison logic
├── logger.py           # Logging setup & configuration
pyproject.toml          # Poetry project & tool configuration
env.example             # Environment variables template
.env                    # Active environment variables
README.md               # Project documentation
credentials.json        # Google OAuth credentials
token.pickle            # Stored Google authentication token
calendar_sync.json      # Local synchronization state
tests/                  # Test suite
```

## Configuration Files

### credentials.json
Downloaded from Google Cloud Console (required)

### .env
```env
CALDAV_URL=https://caldav.example.com
CALDAV_USERNAME=user
CALDAV_PASSWORD=pass
CALDAV_CALENDAR_NAME=My Calendar
GOOGLE_CALENDAR_NAME=CalDAV Events
```

### calendar_sync.json
Automatically maintained JSON file tracking:
- Event UIDs
- Event summaries
- Start and end times
- Last modification timestamps
- Google Calendar event IDs

## Error Handling

The script provides robust error handling:
- Failed events are tracked in memory during sync
- Detailed error messages for both CalDAV and Google Calendar operations
- Rate limiting prevents Google Calendar API throttling
- Synchronization state preserved even on partial failures
- Automatic token refresh for expired Google credentials

## Troubleshooting

### Authentication Issues

#### Google Calendar
- Error: `Invalid client credentials`
  - Verify `credentials.json` is correctly downloaded and placed
  - Ensure OAuth consent screen is configured
  - Check that Calendar API is enabled in Google Cloud Console

- Error: `Token has been expired or revoked`
  - Delete `token.pickle`
  - Re-run script to trigger new authentication flow

#### CalDAV
- Error: `Could not connect to server`
  - Check URL format and accessibility
  - Verify network connectivity
  - Confirm server SSL certificate if using HTTPS
  - Validate username and password

### Synchronization Issues

- Error: `Calendar not found`
  - Verify calendar names in `.env` (case-insensitive matching supported)
  - Check calendar visibility/permissions
  - Ensure calendar exists on both servers

- Error: `Failed to add/update events`
  - Check event data formatting (especially date/time formats)
  - Verify calendar write permissions
  - Review API quotas and limits
  - Check for required event fields

## Development

### Pre-commit Hooks
```bash
poetry run pre-commit install
```

This sets up pre-commit hooks to enforce code quality and consistency.

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Submit pull request

Please:
- Follow existing code style (enforced by Ruff)
- Add tests for new features
- Update documentation
- Run pre-commit hooks
- Maintain type hints and docstrings

## License

GNU General Public License v3.0 or later

## Credits

Built with:
- [caldav](https://pypi.org/project/caldav/) - CalDAV client library
- [google-api-python-client](https://github.com/googleapis/google-api-python-client) - Google Calendar API
- [python-dotenv](https://pypi.org/project/python-dotenv/) - Environment management
- [Poetry](https://python-poetry.org/) - Dependency management
- [Ruff](https://github.com/astral-sh/ruff) - Python linter
- [pytest](https://docs.pytest.org/) - Testing framework
