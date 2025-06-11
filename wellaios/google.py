import os
from typing import Optional
from urllib.parse import urlencode
import requests
from starlette.requests import Request
from starlette.responses import PlainTextResponse, RedirectResponse

from wellaios.disk import get_user_google_credentials, save_user_google_tokens

# Load environment variables. These should be set securely in production.
SERVER_DOMAIN = os.environ.get("SERVER_DOMAIN")  # e.g., "http://your.app.com"
GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID")  # Your Google OAuth Client ID
GOOGLE_CLIENT_SECRET = os.environ.get(
    "GOOGLE_CLIENT_SECRET"
)  # Your Google OAuth Client Secret

# Construct the redirect URI for Google OAuth callback.
# This must exactly match one of the authorized redirect URIs in your Google Cloud project.
GOOGLE_REDIRECT_URI = f"{SERVER_DOMAIN}/auth/google/callback"

# Define the Google OAuth scopes required for your application.
GOOGLE_SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",  # Permission to view calendar events
    "https://www.googleapis.com/auth/calendar.events",  # Permission to create/modify calendar events
]

# A temporary, in-memory dictionary to store state-user ID pairs during the OAuth flow.
temp_google_oauth_states: dict[str, str] = {}


def refresh_google_access_token(userid: str, refresh_token: str) -> str | None:
    """
    Refreshes an expired Google access token using the stored refresh token.

    Args:
        userid: The unique identifier of the user whose token needs to be refreshed.
        refresh_token: The long-lived refresh token obtained during initial authorization.

    Returns:
        The new access token string if the refresh is successful, otherwise None.
    """
    token_url = "https://oauth2.googleapis.com/token"  # Google's token endpoint
    payload = {
        "client_id": GOOGLE_CLIENT_ID,
        "client_secret": GOOGLE_CLIENT_SECRET,
        "refresh_token": refresh_token,
        "grant_type": "refresh_token",  # Indicate that we are using a refresh token
    }

    try:
        # Make a POST request to the token endpoint to get a new access token.
        response = requests.post(token_url, data=payload)
        response.raise_for_status()  # Raise an HTTPError for 4xx/5xx responses
        new_token_data = response.json()

        # The refresh token is often not returned in a refresh response, so we add it back
        # to the new token data before saving, as it's still valid.
        new_token_data["refresh_token"] = refresh_token
        # Save the updated token data, including the new access token and its expiry.
        save_user_google_tokens(userid, new_token_data)
        return new_token_data["access_token"]
    except Exception as e:
        print(
            f"An unexpected error occurred during token refresh for user {userid}: {e}"
        )
        return None


def generate_google_auth_url(state: str) -> str:
    """
    Generates the Google OAuth authorization URL to redirect the user to.

    Args:
        state: A unique, unguessable string to protect against CSRF attacks.

    Returns:
        The full Google OAuth authorization URL.
    """
    params = {
        "client_id": GOOGLE_CLIENT_ID,
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "response_type": "code",  # We expect an authorization code in return
        "scope": " ".join(GOOGLE_SCOPES),  # Space-separated list of requested scopes
        "access_type": "offline",  # Request a refresh token for offline access
        "prompt": "consent",  # Force consent screen to ensure refresh token is always granted
        "state": state,
    }
    # Encode parameters and construct the full URL.
    return f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"


def exchange_code_for_tokens(code: str) -> dict:
    """
    Exchanges the authorization code received from Google for access and refresh tokens.

    Args:
        code: The authorization code received from Google in the callback.

    Returns:
        A dictionary containing the token response from Google (access_token, refresh_token, etc.).

    Raises:
        requests.exceptions.HTTPError: If the token exchange request fails.
    """
    response = requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",  # Indicate we are exchanging an authorization code
        },
    )

    response.raise_for_status()  # Raise an exception for bad status codes (e.g., invalid code)
    return response.json()  # Return the full token response


def start_google_auth(user_id: str):
    """
    Initiates the Google OAuth 2.0 authorization flow for a given user.

    Generates a unique 'state' parameter, stores it with the user ID,
    and returns a RedirectResponse to Google's authorization URL.

    Args:
        user_id: The unique identifier of the user to authorize.

    Returns:
        A Starlette RedirectResponse object that will redirect the user's browser to Google's consent screen.
    """
    # Generate a random state string for CSRF protection.
    state = os.urandom(16).hex()
    # Store the state and associate it with the user ID.
    temp_google_oauth_states[state] = user_id

    # Generate the full authorization URL.
    auth_url = generate_google_auth_url(state)
    return RedirectResponse(auth_url)


def handle_google_callback(request: Request):
    """
    Handles the callback from Google after a user completes the authorization flow.

    Extracts the authorization code and state from the URL query parameters.
    Validates the state, exchanges the code for tokens, and saves them.

    Args:
        request: The Starlette Request object containing query parameters.

    Returns:
        A Starlette PlainTextResponse indicating success or an error, or a RedirectResponse.
    """
    code = request.query_params.get("code")
    state = request.query_params.get("state")
    error = request.query_params.get(
        "error"
    )  # Check for errors from Google (e.g., user denied access)

    if error:
        print(f"Google OAuth error: {error}")
        return PlainTextResponse(f"Google OAuth Error: {error}", status_code=400)

    if not code or not state:
        return PlainTextResponse("Invalid OAuth callback parameters", status_code=400)

    # Validate the state parameter.
    # Retrieve and remove the state from our temporary storage.
    user_id = temp_google_oauth_states.pop(state, None)
    if user_id is None:
        print(f"Invalid or missing state parameter: {state}")
        # This could indicate a CSRF attack or an expired state.
        return PlainTextResponse("Invalid or expired state parameter", status_code=400)

    try:
        # Exchange the authorization code for access and refresh tokens.
        token_data = exchange_code_for_tokens(code)

        # Securely save the received token_data (especially the refresh_token)
        # linked to the user_id for future use.
        save_user_google_tokens(user_id, token_data)

        # Indicate success to the user. In a real application, this might redirect
        # to a user dashboard or an app-specific success page.
        return PlainTextResponse("You can close the tab.", status_code=200)
    except Exception as e:
        print(f"An unexpected error occurred during token exchange: {e}")
        return PlainTextResponse("An internal error occurred.", status_code=500)


def get_user_token(user_id: str) -> Optional[str]:
    """
    Retrieves a valid Google access token for a given user.

    It first checks if an existing access token is valid. If it's expired or
    nearing expiration, it attempts to refresh it using the stored refresh token.

    Args:
        user_id: The unique identifier of the user.

    Returns:
        A valid Google access token string, or None if authorization is needed
        or if token refresh fails.
    """
    # Attempt to get existing Google credentials (access token or refresh token status).
    result = get_user_google_credentials(user_id)
    if result is None:
        # If no credentials exist, the user needs to authorize.
        return None

    is_valid, token_or_refresh_token = result

    if not is_valid:
        # If the existing access token is not valid (e.g., expired),
        # try to refresh it using the refresh token provided in `token_or_refresh_token`.
        access_token = refresh_google_access_token(user_id, token_or_refresh_token)
        return access_token
    else:
        # If the existing access token is still valid, return it directly.
        return token_or_refresh_token
