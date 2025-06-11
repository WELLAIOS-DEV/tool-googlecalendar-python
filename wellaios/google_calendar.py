from datetime import datetime, timezone
import requests

# Base URL for the Google Calendar API
GOOGLE_CALENDAR_API_BASE_URL = "https://www.googleapis.com/calendar/v3"


def get_auth_headers(access_token: str) -> dict:
    """
    Generates standard HTTP headers for Google Calendar API requests.

    Args:
        access_token: The OAuth 2.0 access token for authenticating with Google APIs.

    Returns:
        A dictionary containing the Authorization and Content-Type headers.
    """
    return {
        "Authorization": f"Bearer {access_token}",  # OAuth 2.0 Bearer token for authentication
        "Content-Type": "application/json",  # Specifies that the request body is JSON
    }


def get_user_timezone(access_token: str) -> str | None:
    """
    Retrieves the authenticated user's primary Google Calendar timezone setting.

    Args:
        access_token: The OAuth 2.0 access token of the user.

    Returns:
        A string representing the user's timezone (e.g., "America/Los_Angeles")
        or None if an error occurs or the timezone cannot be retrieved.
    """
    # Get the standard authentication headers
    headers = get_auth_headers(access_token)
    # Construct the API URL for retrieving the user's timezone setting
    url = f"{GOOGLE_CALENDAR_API_BASE_URL}/users/me/settings/timezone"
    try:
        # Send a GET request to the Google Calendar API
        response = requests.get(url, headers=headers)
        # Raise an HTTPError for bad responses (4xx or 5xx status codes)
        response.raise_for_status()
        # Parse the JSON response
        timezone_data = response.json()
        # Extract the 'value' field which contains the timezone string
        return timezone_data.get("value")
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred while getting timezone: {e}")
        return None


def list_calendar_events(
    access_token: str, calendar_id: str = "primary", max_results: int = 10
) -> list:
    """
    Lists upcoming events from a specified Google Calendar.

    Events are retrieved starting from the current UTC time.

    Args:
        access_token: The OAuth 2.0 access token of the user.
        calendar_id: The ID of the calendar to list events from. Defaults to "primary"
                     for the user's default calendar.
        max_results: The maximum number of events to return. Defaults to 10.

    Returns:
        A list of event dictionaries from the Google Calendar API, or an empty list
        if no events are found or an error occurs.
    """
    # Get the standard authentication headers
    headers = get_auth_headers(access_token)
    # Get the current UTC time and format it as required by the API (RFC3339)
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    # Construct the API URL for listing events from the specified calendar
    url = f"{GOOGLE_CALENDAR_API_BASE_URL}/calendars/{calendar_id}/events"

    # Define query parameters for the request
    params = {
        "timeMin": now,  # Only retrieve events starting from now
        "maxResults": max_results,  # Limit the number of results
    }

    try:
        # Send a GET request to the Google Calendar API with headers and parameters
        response = requests.get(url, headers=headers, params=params)
        # Raise an HTTPError for bad responses (4xx or 5xx status codes)
        response.raise_for_status()
        # Parse the JSON response
        events_data = response.json()
        # Extract the 'items' list, which contains the actual event data. Default to empty list.
        events = events_data.get("items", [])

        if not events:
            # Inform if no upcoming events are found
            print("No upcoming events found.")
            return []
        else:
            # Print the number of events found (for debugging/logging)
            print(f"Found {len(events)} events:")
            # Basic iteration for internal logging/debugging, but the full event list is returned
            for event in events:
                # Extract either dateTime (for specific time) or date (for all-day events)
                start = event["start"].get("dateTime", event["start"].get("date"))
                # print(f"  {event['summary']} ({start})") # Example: print event summary and start time
            return events

    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred while listing events: {e}")
        return []


def add_calendar_event(
    access_token: str,
    event_summary: str,
    start_time_str: str,
    end_time_str: str,
    calendar_id: str = "primary",
    description: str = "",
) -> dict | None:
    """
    Adds a new event to a specified Google Calendar.

    Args:
        access_token: The OAuth 2.0 access token of the user.
        event_summary: The title or summary of the event.
        start_time_str: The start time of the event in "YYYY-MM-DDTHH:MM:SS" format.
        end_time_str: The end time of the event in "YYYY-MM-DDTHH:MM:SS" format.
        calendar_id: The ID of the calendar to add the event to. Defaults to "primary".
        description: An optional detailed description for the event.

    Returns:
        A dictionary representing the newly created event if successful, or None if an error occurs.
    """
    # Get the standard authentication headers
    headers = get_auth_headers(access_token)
    # Get the user's timezone to ensure event times are interpreted correctly by Google Calendar.
    tz = get_user_timezone(access_token)
    if tz is None:
        print("Could not retrieve user timezone, cannot add event.")
        return None

    # Construct the event body as a dictionary, following Google Calendar API specifications.
    event_body = {
        "summary": event_summary,
        "description": description,
        "start": {"dateTime": start_time_str, "timeZone": tz},
        "end": {"dateTime": end_time_str, "timeZone": tz},
    }

    # Construct the API URL for inserting events into the specified calendar
    url = f"{GOOGLE_CALENDAR_API_BASE_URL}/calendars/{calendar_id}/events"

    try:
        # Send a POST request to the Google Calendar API with the event body as JSON
        response = requests.post(url, headers=headers, json=event_body)
        # Raise an HTTPError for bad responses (4xx or 5xx status codes)
        response.raise_for_status()
        # Parse the JSON response, which contains the details of the created event
        created_event = response.json()
        return created_event
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred while adding event: {e}")
        return None
