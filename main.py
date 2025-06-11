from dotenv import load_dotenv

# Load environment variables from a .env file.
load_dotenv()

import json

from fastmcp import FastMCP, Context
from starlette.middleware import Middleware
from starlette.responses import PlainTextResponse
from starlette.requests import Request

from wellaios.authenticate import (
    AuthenticationMiddleware,
    gen_user_auth_token,
    match_user_auth_token,
)
from wellaios.google_calendar import add_calendar_event, list_calendar_events
from wellaios.google import get_user_token, handle_google_callback, start_google_auth

import uvicorn

# Initialize the FastMCP application.
mcp = FastMCP("wellaios-demo")

# This special token prefix indicates to the WELLAIOS engine that user authorization
# is required or being initiated.
REQUEST_AUTH_TOKEN = "[AUTH]"


@mcp.tool()
async def view_calendar(ctx: Context) -> str:
    """
    View the Google Calendar events of the authenticated user.

    This tool requires no parameters.
    """
    request = ctx.get_http_request()
    # Extract the user ID from the X-User-ID header provided by WELLAIOS.
    # Defaults to "unknown" if not present.
    user_id = request.headers.get("X-User-ID")

    # If no user ID is found (e.g., when requests aren't coming from WELLAIOS's multi-user context,
    # like from a generic MCP Inspector), we fall back to a default user ID.
    # This ensures basic functionality and compatibility for single-user testing scenarios.
    # SHOULD BE REMOVED for production
    if user_id is None:
        user_id = "single_user"

    # Attempt to retrieve a valid Google access token for the user.
    # This function handles token refresh if necessary.
    token = get_user_token(user_id)

    if token is None:
        # If no valid token is found (meaning the user isn't authenticated or refresh failed),
        # return the special authorization token along with a unique token for this user
        # to initiate the OAuth flow from WELLAIOS.
        return f"{REQUEST_AUTH_TOKEN} {gen_user_auth_token(user_id)}"

    # If a valid token is available, list the user's calendar events and return them as a JSON string.
    return json.dumps(list_calendar_events(token))


@mcp.tool()
async def add_event_to_calendar(
    details: str, start_time: str, end_time: str, ctx: Context
) -> str:
    """
    Adds an event to the authenticated user's Google Calendar.

    Args:
        details: A description or summary of the event (e.g., "Team meeting").
        start_time: The start time of the event in "YYYY-MM-DDTHH:MM:SS" format
                    (e.g., "2025-05-26T07:00:00").
        end_time: The end time of the event in "YYYY-MM-DDTHH:MM:SS" format
                  (e.g., "2025-05-26T08:00:00").
    """
    request = ctx.get_http_request()
    # Extract the user ID from the X-User-ID header.
    user_id = request.headers.get("X-User-ID")

    # If no user ID is found (e.g., when requests aren't coming from WELLAIOS's multi-user context,
    # like from a generic MCP Inspector), we fall back to a default user ID.
    # This ensures basic functionality and compatibility for single-user testing scenarios.
    # SHOULD BE REMOVED for production
    if user_id is None:
        user_id = "single_user"

    # Attempt to retrieve a valid Google access token for the user.
    token = get_user_token(user_id)

    if token is None:
        # If no valid token is found, return the authorization request.
        return f"{REQUEST_AUTH_TOKEN}\n{gen_user_auth_token(user_id)}"

    # If a valid token is available, add the event to the calendar and return the result as JSON.
    return json.dumps(add_calendar_event(token, details, start_time, end_time))


# A custom HTTP route specifically designed for handling user authorization flows.
# This endpoint is accessed directly by the user's browser, typically initiated by WELLAIOS.
@mcp.custom_route("/auth", methods=["GET"])
async def auth(request: Request):
    """
    Handles user authorization initiation for Google services.

    This endpoint is invoked by WELLAIOS
    when a tool needs Google Calendar access. It validates the user and token
    provided by WELLAIOS, then redirects the user to Google's OAuth consent screen.
    """
    # Retrieve the 'userid' and 'token' from the request's query parameters.
    # These parameters are passed by WELLAIOS to identify the user and validate the request.
    user_id = request.query_params.get("userid")
    token = request.query_params.get("token")

    # Validate the user ID and the provided token using the `match_user_auth_token` utility.
    # This ensures that only legitimate authorization requests are processed.
    if user_id is None or token is None or not match_user_auth_token(user_id, token):
        # If validation fails, return an Unauthorized response.
        return PlainTextResponse("Unauthorized", status_code=401)

    # If the user and token are valid, initiate the Google OAuth flow by
    # redirecting the user's browser to Google's authentication URL.
    return start_google_auth(user_id)


# Another custom HTTP route for handling the callback from Google's OAuth server.
# After the user grants consent, Google redirects back to this URL.
@mcp.custom_route("/auth/google/callback", methods=["GET"])
async def auth_google_callback(request: Request):
    """
    Handles the callback from Google's OAuth server after user authorization.

    This endpoint receives the authorization code from Google, exchanges it
    for access and refresh tokens, and saves them for the user.
    """
    # Delegate the actual handling of the Google OAuth callback to a dedicated function.
    return handle_google_callback(request)


if __name__ == "__main__":
    # Define a list of custom middleware to be applied to the HTTP application.
    custom_middleware = [Middleware(AuthenticationMiddleware)]

    # Create the FastMCP HTTP application instance.
    http_app = mcp.http_app(middleware=custom_middleware)

    # Run the Uvicorn server.
    uvicorn.run(http_app, host="0.0.0.0", port=30000)
