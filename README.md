# CalDAV2GoogleCalendar

This project synchronizes events from a CalDAV calendar to a specific Google Calendar.

## Features
- Connects to a CalDAV server to fetch calendar events.
- Compares fetched events with locally stored events to identify new, updated, and deleted events.
- Synchronizes changes to a specified Google Calendar:
  - Adds new events.
  - Updates modified events.
  - Deletes removed events.

## Prerequisites

### 1. Python Environment
Ensure you have Python 3.7 or higher installed. It is recommended to use a virtual environment.

### 2. CalDAV Server
A CalDAV server should be set up and accessible. Ensure you have the following:
- CalDAV server URL
- Username
- Password

### 3. Google Calendar API Credentials

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

1. Clone this repository:
   ```bash
   git clone https://github.com/your-username/caldav2googlecalendar.git
   cd caldav2googlecalendar
   ```

2. Install dependencies using Poetry:
   ```bash
   poetry install
   ```

3. Activate the virtual environment:
   ```bash
   poetry shell
   ```

## Configuration

1. Update the `CALDAV_URL`, `USERNAME`, and `PASSWORD` variables in the script to match your CalDAV server credentials.
2. Ensure the `LOCAL_SYNC_FILE` points to the file where locally synced events will be stored.

## Usage

1. Run the script:
   ```bash
   python sync_caldav_to_google.py
   ```

2. On the first run, a browser window will open for Google authentication. Grant the necessary permissions to access your Google Calendar.
3. The script will:
   - Fetch events from the CalDAV calendar.
   - Compare with the locally stored events.
   - Add, update, or delete events in the specified Google Calendar.

## Project Structure

```
caldav2googlecalendar/
├── sync_caldav_to_google.py  # Main script
├── pyproject.toml            # Project metadata and dependencies
├── README.md                 # Project documentation
├── credentials.json          # Google API credentials (not included in the repository)
├── calendar_sync.json        # Locally synced events
└── .venv/                    # Virtual environment (not included in the repository)
```

## Logging

- The script provides detailed logs during execution:
  - Number of new, updated, and deleted events.
  - Any errors encountered during synchronization.

## Troubleshooting

### Common Issues

#### 1. `HttpError 400` when adding events
- Ensure the event data is correctly formatted (ISO 8601 format for `start` and `end` dates).
- Check if required fields (`summary`, `start`, `end`) are missing.

#### 2. Authentication Issues
- Ensure the `credentials.json` file is in the correct location.
- Delete the `token.pickle` file and re-authenticate by running the script again.

#### 3. CalDAV Connection Issues
- Verify the `CALDAV_URL`, `USERNAME`, and `PASSWORD` values.
- Test connectivity to the CalDAV server using another CalDAV client (e.g., Thunderbird).

## Contributions

Contributions are welcome! Please fork the repository, make your changes, and submit a pull request.

## License

This project is licensed under the GNU General Public License v3.0 or later. See the LICENSE file for more details.

## Acknowledgments

- [Radicale](https://radicale.org/) for providing a lightweight CalDAV server.
- [Google Calendar API](https://developers.google.com/calendar) for seamless calendar integration.


