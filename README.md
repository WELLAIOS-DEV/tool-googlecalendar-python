# WELLAIOS Calendar Assistant Tool Server (Standalone)

This repository presents a standalone server demonstration for the **WELLAIOS Calendar Assistant** tool.
This tool leverages the **Google Calendar API** to enable AI agents to interact with user calendars, supporting both viewing and adding events.

## Getting Started

Follow these steps to set up and run your WELLAIOS Calendar Assistant server:

1. **Get Google Calendar API Credentials (Client ID & Client Secret)**

   To use the Google Calendar API, you'll need to create a project in the Google Cloud Console and obtain OAuth 2.0 Client ID and Client Secret credentials. These are necessary for authenticating your application with Google and allowing users to grant access to their calendars.

   Here's how to get them:

   1. **Go to Google Cloud Console**:
      Navigate to the [Google Cloud Console](https://console.cloud.google.com/) and sign in with your Google account.

   2. **Create or Select a Project**:
      From the project dropdown at the top, choose an existing project or create a new one.

   3. **Enable the Google Calendar API**:

      - In the Cloud Console, go to APIs & Services > Library.
      - Search for "Google Calendar API" and select it.
      - Click the "Enable" button.

   4. **Create OAuth Consent Screen**:

      - Go to APIs & Services > OAuth consent screen.
      - Configure your consent screen (e.g., set the app name, user support email).
      - Add authorized scopes: You'll need `https://www.googleapis.com/auth/calendar.readonly` and `https://www.googleapis.com/auth/calendar.events`.

   5. **Create OAuth Client ID & Client Secret**:
      - Navigate to APIs & Services > Credentials.
      - Click "Create Credentials" and select "OAuth client ID".
      - Choose "Web application" as the Application type.
      - Add an Authorized Redirect URI: This is crucial!
        This is the URL Google will redirect to after a user authorizes your app.
        For example, `http://localhost:30000/auth/google/callback`.
      - Click "Create". Your Client ID and Client Secret will be displayed. Make sure to copy them.

2. **Install Python and Required Packages**

   Make sure you have Python installed on your system (Python 3.12+ is recommended).
   Then, navigate to your project directory in the terminal and install the necessary Python packages using `pip`:

   ```
   pip install -r requirements.txt
   ```

3. **Configure the Server**

   Create a file named `.env` in the root directory of your project (the same directory as `main.py`). Add the following content, replacing the placeholder values with your actual tokens and API key:

   ```
   AUTH_TOKEN=your_wellaios_auth_token_here
   SERVER_DOMAIN=http://localhost:30000
   GOOGLE_CLIENT_ID=your_google_client_id_here # e.g., xxxxxxxxxxxx.apps.googleusercontent.com
   GOOGLE_CLIENT_SECRET=your_google_client_secret_here # e.g., GOCSPX-yyyyyyyyyyyyyyyyyy
   ```

   - `AUTH_TOKEN`:
     This is the bearer token used for authenticating clients with your tool server (e.g., from WELLAIOS).
   - `SERVER_DOMAIN`:
     This environment variable defines the base URL for your server, critical for Google OAuth callbacks. For local testing, the default is `http://localhost:30000`.
   - `GOOGLE_CLIENT_ID`:
     Your Client ID obtained from the Google Cloud Console.
   - `GOOGLE_CLIENT_SECRET`:
     Your Client Secret obtained from the Google Cloud Console.

4. **Test Your Tool Server**

   You can test your running tool server

   - **MCP Inspector**:
     For basic testing and inspecting the tool's functionality, you can use the [MCP inspector](https://github.com/modelcontextprotocol/inspector).

     **Note**: The MCP Inspector currently does not support multi-user scenarios. Therefore, you won't be able to test the multi-user specific features using this tool alone.

   - **WELLAIOS Engine**:
     The best way to thoroughly test the multi-user capabilities and the full integration is by connecting your tool server to the WELLAIOS engine itself.
     Refer to the WELLAIOS documentation for instructions on how to connect external tool servers.

## Guide to connect to MCP Inspector

### Transport Type

Select `Streamble HTTP`

### URL

Enter the MCP path under your server's location.
For example, if your server is running locally on port 30000, the URL would be:

`http://localhost:30000/mcp`

### Authentication

Use `Bearer Token` as the authentication method.
Then, use the exact token you've set in your `.env` file.

## Example Flow of Using the Tool on MCP Inspector (Single User)

This example demonstrates the typical authorization flow when using the `Calendar Assistant` with the MCP Inspector:

1. **Attempt to call** `view_calendar`

   - In MCP Inspector, try calling the view_calendar tool.
   - You'll notice the result contains `[AUTH] [your_generated_token]`.
     This is the signal from your tool server (and how WELLAIOS would interpret it) that user authorization is required.

2. **Initiate User Authorization**

   - Since MCP Inspector doesn't automatically handle the OAuth flow, you need to manually access the `/auth` path of your tool server in a web browser.

   - Construct the URL using your server's domain, the `user_id`, and the `token` you received in the `view_calendar` call result.

   - For example, if your server is on `http://localhost:30000` and the `view_calendar` call returned `[AUTH] mysecrettoken123`, the link would be: `http://localhost:30000/auth?userid=single_user&token=mysecrettoken123`

   - **Important**: Make sure `userid` is set to `single_user` as that's the fallback ID for MCP Inspector.

   - Opening this link will redirect you to the Google authorization page.
     Follow the prompts to grant your application access to your Google Calendar.

   - After successful authorization, you'll see a page from your server stating, "You can close the tab."
     You can then close this browser tab and return to MCP Inspector.

3. **Call** `view_calendar` **Again**:

   - Now, try calling view_calendar in MCP Inspector once more.
   - This time, your server should have the necessary Google tokens, and you will see the upcoming events from your Google Calendar displayed in the response.
