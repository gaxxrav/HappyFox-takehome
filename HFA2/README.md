# Email Processing Application

A standalone Python application that integrates with the Gmail API, stores emails in a PostgreSQL database, and processes them based on rules defined in a JSON file.

## Project Overview

This application provides automated email processing capabilities:

- **Gmail API Integration**: Authenticates with Gmail using OAuth 2.0 and fetches 100 most recent emails
- **Database Storage**: Stores emails in PostgreSQL with duplicate handling
- **Rule-Based Processing**: Applies configurable rules to emails for automatic organization
- **Actions**: Mark as read/unread, move to folders, and update database status

## Features

- Fetch up to 100 recent emails from Gmail Inbox (configurable)
- Store emails in PostgreSQL database with conflict resolution
- Process emails based on JSON-defined rules
- Support for multiple conditions and predicates (ALL/ANY)
- Actions: mark as read/unread, move to folders
- Comprehensive error handling and logging
- Unit tests with mocked dependencies

## Prerequisites

- Python 3.8 or higher
- PostgreSQL database
- Gmail API credentials

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd HFA2
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL database**
   ```bash
   # Create database
   createdb email_processor
   
   # Or using psql
   psql -U postgres
   CREATE DATABASE email_processor;
   ```

4. **Configure Gmail API**
   - Go to [Google Cloud Console](https://console.cloud.google.com/)
   - Create a new project or select existing one
   - Enable the Gmail API
   - Create OAuth 2.0 credentials
   - Download the credentials file as `credentials.json`
   - Place `credentials.json` in the project root

## Configuration

### Database Configuration

The application uses these default database settings:
- Host: `localhost`
- Port: `5432`
- User: Current system user (or `postgres` if not available)
- Password: (empty)
- Database: `email_processor`

You can modify these in the `EmailDatabase` constructor or use the `run_with_configuration` function.

### Email Fetch Limit

The default email fetch limit is 100. You can modify this in `src/config.py`:

```python
EMAIL_FETCH_LIMIT = 100  # Change this value as needed
```

### Rules Configuration

Rules are defined in `rules.json`. Each rule has:

- **rule_name**: Descriptive name for the rule
- **predicate**: `ALL` (all conditions must match) or `ANY` (at least one condition must match)
- **conditions**: List of conditions to evaluate
- **actions**: List of actions to execute when conditions match

#### Supported Conditions

- **field**: `from`, `subject`, `received_date`
- **operator**: `contains` (for text fields), `less_than_days` (for dates)
- **value**: The value to match against

#### Supported Actions

- `mark_as_read`: Mark email as read
- `mark_as_unread`: Mark email as unread
- `move`: Move email to specified mailbox/folder

#### Example Rules

The project includes several pre-configured rules:

```json
{
    "rule_name": "Critical Security Alerts",
    "predicate": "ANY",
    "conditions": [
        {"field": "subject", "operator": "contains", "value": "Security Alert"},
        {"field": "from", "operator": "contains", "value": "security@"}
    ],
    "actions": [
        {"action": "mark_as_unread"},
        {"action": "move", "mailbox": "Security Alerts"}
    ]
}
```

## Usage

### Basic Usage

Run the application with default settings:

```bash
python -m src.main
```

### Custom Configuration

Use the `run_with_configuration` function for custom settings:

```python
from src.main import run_with_configuration

exit_code = run_with_configuration(
    gmail_credentials_file='path/to/credentials.json',
    rules_file='path/to/rules.json',
    database_host='localhost',
    database_port=5432,
    database_user='postgres',
    database_password='your_password',
    database_name='email_processor',
    email_fetch_limit=50
)
```

## Testing

Run the unit tests:

```bash
pytest tests/
```

Run tests with verbose output:

```bash
pytest -v tests/
```

## Project Structure

```
HFA2/
├── src/
│   ├── __init__.py
│   ├── config.py          # Configuration and rule loading
│   ├── gmail_api.py       # Gmail API authentication and operations
│   ├── database.py        # PostgreSQL connection and email storage
│   ├── rule_engine.py     # Rule parsing and evaluation
│   └── main.py            # Main application orchestration
├── tests/
│   ├── __init__.py
│   └── test_rule_engine.py # Unit tests for rule engine
├── rules.json             # Email processing rules
├── credentials.json       # Gmail API OAuth credentials (user-provided)
├── token.json             # OAuth token (auto-generated)
├── errors.log             # Error log file (auto-generated)
├── README.md              # This file
└── requirements.txt       # Python dependencies
```

## Database Schema

The application creates an `emails` table with the following schema:

```sql
CREATE TABLE emails (
    id VARCHAR(255) PRIMARY KEY,
    thread_id VARCHAR(255),
    from_email TEXT,
    subject TEXT,
    received_date TIMESTAMP,
    mailbox TEXT,
    is_read BOOLEAN,
    snippet TEXT
);
```

## Error Handling

The application includes comprehensive error handling:

- **Gmail API errors**: Logged and operations skipped gracefully
- **Database errors**: Logged with individual email handling
- **Rule parsing errors**: Invalid rules are skipped with warnings
- **Authentication failures**: Clear error messages and exit codes

All errors are logged to both console and `errors.log` file.

## Logging

The application uses structured logging with:

- **Console output**: INFO level and above
- **File logging**: ERROR level to `errors.log`
- **Timestamps**: All log entries include timestamps
- **Module identification**: Logs identify the source module

## Security Considerations

- OAuth tokens are stored locally in `token.json`
- Database credentials should be secured appropriately
- Gmail API credentials should be kept confidential
- Consider using environment variables for sensitive configuration

## Troubleshooting

### Common Issues

1. **Gmail API Authentication Failed**
   - Ensure `credentials.json` is in the project root
   - Check that Gmail API is enabled in Google Cloud Console
   - Verify OAuth consent screen is configured

2. **Database Connection Failed**
   - Verify PostgreSQL is running
   - Check database credentials
   - Ensure database exists

3. **No Emails Processed**
   - Check if rules.json is valid JSON
   - Verify rule conditions match your emails
   - Check logs for rule validation warnings

4. **Permission Errors**
   - Ensure write permissions for token.json and errors.log
   - Check database user permissions

### Debug Mode

For detailed debugging, you can modify the logging level in `src/main.py`:

```python
root_logger.setLevel(logging.DEBUG)
```

## How to Run

1. **Set up the required files:**
   - Download `credentials.json` from Google Cloud Console
   - Place it in the project root directory

2. **Run the application:**
   ```bash
   python -m src.main
   ```
   
   The first run will:
   - Generate `token.json` after OAuth authentication
   - Create the database table if it doesn't exist
   - Process emails according to the rules in `rules.json`

3. **Monitor the output:**
   - Check console output for processing status
   - Review `errors.log` for any issues
   - Verify emails are being processed in Gmail

## Dependencies

The application requires the following Python packages (see `requirements.txt`):

- `google-auth-oauthlib>=1.0.0` - Gmail OAuth authentication
- `google-api-python-client>=2.88.0` - Gmail API client
- `psycopg2-binary>=2.9.7` - PostgreSQL database adapter
- `python-dateutil>=2.8.2` - Date parsing utilities
- `pytest>=7.4.0` - Testing framework
