# CalDAV2GoogleCalendar

<p align="center">
  <img src="https://gitlab.com/uploads/-/system/project/avatar/64798757/logo.jpg" alt="caldav2google"/>
</p>

A Python utility to synchronize events from a CalDAV calendar to Google Calendar, maintaining a local state to track changes.

## Features
- One-way synchronization from CalDAV to Google Calendar
- Intelligent change detection:
  - Adds new events
  - Updates modified events
  - Removes deleted events
- Local state management to track synchronized events
- Detailed logging of synchronization activities
- Rate limiting to prevent API throttling
- Error handling with failed events tracking

## Prerequisites

### 1. Python Environment
- Python 3.10 or higher
- Poetry for dependency management

### 2. CalDAV Server Details
You'll need:
- CalDAV server URL
- Username
- Password
- Calendar name to synchronize

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

3. Create `.env` file:
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
   python src/main.py
   ```

On first run:
- Browser opens for Google OAuth authentication
- Grant requested calendar permissions
- Token is saved locally for future use

## Project Structure

```
src/
├── auth_google.py        # Google Calendar authentication
├── caldav_client.py      # CalDAV server interactions
├── main.py               # Main synchronization script
├── sync_logic.py         # Core synchronization logic
pyproject.toml            # Project configuration
env.example               # Environment variables example file
.env                      # Environment variables 
README.md                 # README instructions
credentials.json          # Google OAuth credentials
token.pickle              # Stored Google token
calendar_sync.json        # Local sync state
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
Automatically maintained by the script to track synchronization state.

## Error Handling

The script provides robust error handling:
- Failed events are tracked and reported
- Rate limiting prevents API throttling
- Detailed error messages for troubleshooting
- Synchronization state preserved on failure

## Troubleshooting

### Authentication Issues

#### Google Calendar
- Error: `Invalid client credentials`
  - Verify `credentials.json` is correctly downloaded and placed
  - Ensure OAuth consent screen is configured

- Error: `Token has been expired or revoked`
  - Delete `token.pickle`
  - Re-run script to authenticate

#### CalDAV
- Error: `Could not connect to server`
  - Check URL format and accessibility
  - Verify network connectivity
  - Confirm server SSL certificate if using HTTPS

### Synchronization Issues

- Error: `Calendar not found`
  - Verify calendar names in `.env`
  - Check calendar visibility/permissions

- Error: `Failed to add/update events`
  - Check event data formatting
  - Verify calendar write permissions
  - Review API quotas and limits

## Development

### Pre-commit Hooks
```bash
poetry run pre-commit install
```

## Contributing

1. Fork the repository
2. Create feature branch
3. Commit changes
4. Push to branch
5. Submit pull request

Please:
- Follow existing code style
- Add tests for new features
- Update documentation
- Run pre-commit hooks

## License

GNU General Public License v3.0 or later

## Credits

Built with:
- [caldav](https://pypi.org/project/caldav/) - CalDAV client library
- [google-api-python-client](https://github.com/googleapis/google-api-python-client) - Google Calendar API
- [python-dotenv](https://pypi.org/project/python-dotenv/) - Environment management
- [Poetry](https://python-poetry.org/) - Dependency management
