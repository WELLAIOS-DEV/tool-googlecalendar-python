import json
import os
import time
from typing import Optional

# Define the folder where user token data will be stored.
FOLDER = "tokens"


def save_user_google_tokens(user_id: str, token_data: dict):
    """
    Saves a user's Google token data to a JSON file.

    This function creates a dedicated folder ('tokens') if it doesn't already exist.
    It then saves the provided `token_data` dictionary into a JSON file named
    after the `user_id`. Before saving, it calculates and adds an 'expires_at'
    timestamp based on 'expires_in' (if present) or sets it to 0 if 'expires_in'
    is missing, indicating the token might not expire or its expiration is unknown.

    Args:
        user_id: A unique identifier for the user.
        token_data: A dictionary containing the Google token information
                    (e.g., access_token, refresh_token, expires_in).
    """
    # Create the directory if it doesn't exist to store token files.
    os.makedirs(FOLDER, exist_ok=True)
    # Construct the full file path for the user's token data.
    filepath = os.path.join(FOLDER, f"{user_id}.json")

    # Calculate the 'expires_at' timestamp.
    # 'expires_at' stores the Unix timestamp when the token will expire.
    if "expires_in" in token_data:
        # If 'expires_in' (seconds until expiration) is provided, calculate the exact expiry time.
        token_data["expires_at"] = int(time.time()) + token_data["expires_in"]
    else:
        # If 'expires_in' is not available, set 'expires_at' to 0 as a warning flag.
        # This implies the token might not expire, or its expiration is not known from the data.
        token_data["expires_at"] = 0
        print(
            f"Warning: No 'expires_in' info for user {user_id}. 'expires_at' set to 0."
        )

    # Write the token data (including 'expires_at') to the JSON file.
    with open(filepath, "w") as f:
        json.dump(token_data, f, indent=4)


def get_user_google_credentials(user_id: str) -> Optional[tuple[bool, str]]:
    """
    Retrieves a user's Google credentials (access token or refresh token) and
    checks for expiration.

    This function attempts to load the token data for a given user from a JSON file.
    It then checks if the access token has expired (with a 60-second buffer).
    If the access token is still valid, it returns `(True, access_token)`.
    If the access token has expired or is about to expire, it returns
    `(False, refresh_token)` to indicate that a refresh is needed.

    Args:
        user_id: A unique identifier for the user.

    Returns:
        - `(True, access_token_string)` if the access token is valid and not expired.
        - `(False, refresh_token_string)` if the access token is expired or
          nearing expiration, indicating a refresh is required.
        - `None` if the token file does not exist or an error occurs during loading.
    """
    # Construct the full file path for the user's token data.
    filepath = os.path.join(FOLDER, f"{user_id}.json")
    # Get the current Unix timestamp.
    current_time = int(time.time())

    try:
        # Attempt to open and load the JSON token data.
        with open(filepath, "r") as f:
            token_data = json.load(f)
    except FileNotFoundError:
        # If the file doesn't exist, no credentials are found.
        return None
    except Exception as e:
        # Catch any other potential exceptions during file operations.
        print(f"An unexpected error occurred for user {user_id}: {e}")
        return None

    # Extract relevant token information.
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")
    expires_at = token_data.get("expires_at")

    # Basic validation: ensure we have essential tokens and an expiration time.
    if not access_token or expires_at is None:
        # This case might happen if the file is corrupted or not properly saved.
        print(f"Missing essential token data for user {user_id}")
        return None

    # Check if the current time is greater than or equal to the token's expiration time
    # minus a 60-second buffer. This buffer helps proactively refresh before actual expiration.
    if current_time >= expires_at - 60:
        # If expired or near expiration, return False and the refresh token.
        # This signals the caller to use the refresh token to get a new access token.
        return False, refresh_token
    else:
        # If still valid, return True and the access token.
        return True, access_token
