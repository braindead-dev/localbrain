# Connector OAuth App Setup Guide

This guide explains how to register OAuth apps for each LocalBrain connector. Once registered, add the credentials to `electron/backend/src/bundled_credentials.json` and they'll be loaded automatically at startup.

---

## Google (Gmail + Google Calendar)

Both connectors share the same credentials.

1. Go to [Google Cloud Console](https://console.cloud.google.com)
2. Create a new project (or use an existing one)
3. **Enable APIs:**
   - APIs & Services > Library > search "Gmail API" > Enable
   - APIs & Services > Library > search "Google Calendar API" > Enable
4. **Configure OAuth consent screen:**
   - APIs & Services > OAuth consent screen
   - User Type: External
   - Fill in app name, support email, developer email
   - Scopes: Add `gmail.readonly`, `gmail.labels`, `calendar.readonly`, `calendar.events.readonly`
   - Test users: Add any Google accounts that will sign in during development
5. **Create credentials:**
   - APIs & Services > Credentials > Create Credentials > OAuth client ID
   - Application type: **Desktop app**
   - Name: LocalBrain
   - Click Create
6. Copy the **Client ID** and **Client Secret**

**Redirect URIs** (automatically allowed for Desktop app type):
- `http://localhost:8765/connectors/gmail/auth/callback`
- `http://localhost:8765/connectors/calendar/auth/callback`

**bundled_credentials.json:**
```json
{
  "GMAIL_CLIENT_ID": "xxxx.apps.googleusercontent.com",
  "GMAIL_CLIENT_SECRET": "GOCSPX-xxxx"
}
```

**Note:** While in "Testing" mode, only emails added as Test Users can sign in. Submit for verification when ready to ship.

---

## GitHub

1. Go to [GitHub Developer Settings](https://github.com/settings/developers)
2. Click **OAuth Apps** > **New OAuth App**
3. Fill in:
   - Application name: LocalBrain
   - Homepage URL: `http://localhost:8765`
   - Authorization callback URL: `http://localhost:8765/connectors/github/auth/callback`
4. Click **Register application**
5. Copy the **Client ID** from the app page
6. Click **Generate a new client secret** > copy the secret immediately

**bundled_credentials.json:**
```json
{
  "GITHUB_CLIENT_ID": "Ov23li...",
  "GITHUB_CLIENT_SECRET": "..."
}
```

---

## Notion

1. Go to [Notion Integrations](https://www.notion.so/my-integrations)
2. Click **New integration** (or **Create new integration**)
3. Fill in:
   - Name: LocalBrain
   - Associated workspace: Choose your workspace
   - Type: **Public** (required for OAuth)
4. Under **Capabilities**, enable: Read content, Read user information
5. Under **OAuth Domain & URIs**:
   - Redirect URI: `http://localhost:8765/connectors/notion/auth/callback`
6. Copy the **OAuth client ID** and **OAuth client secret**

**bundled_credentials.json:**
```json
{
  "NOTION_CLIENT_ID": "...",
  "NOTION_CLIENT_SECRET": "secret_..."
}
```

---

## Reddit

1. Go to [Reddit App Preferences](https://www.reddit.com/prefs/apps)
2. Click **create another app...** at the bottom
3. Fill in:
   - Name: LocalBrain
   - App type: **web app**
   - Redirect URI: `http://localhost:8765/connectors/reddit/auth/callback`
4. Click **create app**
5. The **client ID** is the string under the app name (under "web app")
6. The **client secret** is labeled "secret"

**bundled_credentials.json:**
```json
{
  "REDDIT_CLIENT_ID": "...",
  "REDDIT_CLIENT_SECRET": "..."
}
```

---

## Microsoft Outlook (Mail + Calendar)

Both Outlook Mail and Outlook Calendar share the same credentials.

1. Go to [Azure Portal - App Registrations](https://portal.azure.com/#view/Microsoft_AAD_RegisteredApps/ApplicationsListBlade)
2. Click **New registration**
3. Fill in:
   - Name: LocalBrain
   - Supported account types: **Accounts in any organizational directory and personal Microsoft accounts**
   - Redirect URI: Platform = **Public client/native (mobile & desktop)**, URI = `http://localhost:8765/connectors/outlook_mail/auth/callback`
4. Click **Register**
5. Copy the **Application (client) ID** from the overview page
6. Left sidebar > **Certificates & secrets** > **New client secret**:
   - Description: LocalBrain
   - Expiry: choose (24 months max)
   - Click **Add** > copy the **Value** immediately (shown only once)
7. Left sidebar > **API permissions** > **Add a permission** > **Microsoft Graph** > **Delegated permissions**:
   - Add: `Mail.Read`, `Calendars.Read`, `User.Read`
   - Click **Add permissions**

**bundled_credentials.json:**
```json
{
  "OUTLOOK_CLIENT_ID": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
  "OUTLOOK_CLIENT_SECRET": "..."
}
```

---

## Twitter / X

Twitter uses OAuth 2.0 PKCE — only a Client ID is needed (no secret).

**Important:** Twitter API requires a paid developer plan. The Basic tier ($100/month) is needed for `tweet.read` + `offline.access` scopes (user timeline access).

1. Go to [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard)
2. Sign up for a developer account if you don't have one (requires Basic plan)
3. Create a new **Project** and **App**
4. In the app settings, go to **User authentication settings** > **Set up**
5. Configure:
   - App permissions: **Read**
   - Type of App: **Native App** (public client)
   - Callback URI: `http://localhost:8765/connectors/twitter/auth/callback`
   - Website URL: `http://localhost:8765`
6. Copy the **Client ID** from the Keys and Tokens tab

**bundled_credentials.json:**
```json
{
  "TWITTER_CLIENT_ID": "..."
}
```

**Note:** Twitter PKCE flow does not require a client secret for public/native clients.

---

## iMessage

No OAuth registration needed. iMessage reads directly from the local macOS Messages database (`~/Library/Messages/chat.db`). The app requires **Full Disk Access** permission in System Settings > Privacy & Security.

---

## Full bundled_credentials.json Template

```json
{
  "GMAIL_CLIENT_ID": "",
  "GMAIL_CLIENT_SECRET": "",
  "GITHUB_CLIENT_ID": "",
  "GITHUB_CLIENT_SECRET": "",
  "NOTION_CLIENT_ID": "",
  "NOTION_CLIENT_SECRET": "",
  "REDDIT_CLIENT_ID": "",
  "REDDIT_CLIENT_SECRET": "",
  "OUTLOOK_CLIENT_ID": "",
  "OUTLOOK_CLIENT_SECRET": "",
  "TWITTER_CLIENT_ID": ""
}
```

Place this file at `electron/backend/src/bundled_credentials.json`. It is gitignored and loaded automatically by the daemon at startup.
