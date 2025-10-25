# Gmail Connector Setup Guide

## Overview

The Gmail connector is now integrated into the MCP server. You can connect Gmail, fetch emails, and automatically ingest them into your LocalBrain vault.

## 📋 Prerequisites

### 1. Install Python Dependencies

```bash
cd electron/backend
pip install google-auth-oauthlib google-api-python-client html2text
```

### 2. Set Up Google Cloud Project

1. **Go to Google Cloud Console**: https://console.cloud.google.com

2. **Create a new project** (or use existing):
   - Name: "LocalBrain"
   - Click "Create"

3. **Enable Gmail API**:
   - Go to "APIs & Services" > "Library"
   - Search for "Gmail API"
   - Click "Enable"

4. **Create OAuth 2.0 Credentials**:
   - Go to "APIs & Services" > "Credentials"
   - Click "Create Credentials" > "OAuth client ID"
   - If prompted, configure OAuth consent screen:
     - User Type: External
     - App name: LocalBrain
     - User support email: your email
     - Developer contact: your email
     - Scopes: Just click Save (we'll set scopes in code)
   - Application type: **Desktop app**
   - Name: "LocalBrain Gmail Connector"
   - Click "Create"

5. **Download credentials**:
   - Click the download icon next to your OAuth 2.0 Client ID
   - Save the JSON file

6. **Move credentials file**:
   ```bash
   mkdir -p ~/.localbrain/credentials
   mv ~/Downloads/client_secret_*.json ~/.localbrain/credentials/gmail_client_secret.json
   ```

## 🚀 Usage

### Start the MCP Server

```bash
cd electron/backend
python -m src.core.mcp.server
```

The server will start on `http://localhost:8000` (or your configured port).

## 🔌 Available Endpoints

### 1. **Start OAuth Flow**
```http
POST http://localhost:8000/connectors/gmail/auth/start
```

**Response:**
```json
{
  "auth_url": "https://accounts.google.com/o/oauth2/auth?...",
  "success": true
}
```

Open the `auth_url` in a browser to authenticate.

---

### 2. **OAuth Callback** (Automatic)
```http
GET http://localhost:8000/connectors/gmail/auth/callback?code=...
```

Google redirects here after user authorizes. Returns a success page.

---

### 3. **Check Connection Status**
```http
GET http://localhost:8000/connectors/gmail/status
```

**Response (Connected):**
```json
{
  "connected": true,
  "email": "user@gmail.com",
  "lastSync": "2025-10-25T14:30:00",
  "emailCount": 42,
  "totalProcessed": 100,
  "connectedAt": "2025-10-24T10:00:00"
}
```

**Response (Not Connected):**
```json
{
  "connected": false
}
```

---

### 4. **Sync Emails**
```http
POST http://localhost:8000/connectors/gmail/sync?max_results=100
```

**What it does:**
1. Fetches new emails since last sync (or last 30 days if first sync)
2. Converts emails to plain text
3. Automatically ingests into your vault using AgenticIngestionPipeline

**Response:**
```json
{
  "success": true,
  "emails_fetched": 15,
  "emails_processed": 15,
  "ingested_count": 15
}
```

---

### 5. **Fetch Recent Emails (No Ingestion)**
```http
GET http://localhost:8000/connectors/gmail/emails/recent?days=7&max_results=50
```

**Parameters:**
- `days`: Number of days to look back (default: 7)
- `max_results`: Max emails to fetch (default: 50)

**Response:**
```json
{
  "success": true,
  "count": 10,
  "emails": [
    {
      "content": "Subject: Meeting Tomorrow\nFrom: john@example.com\n...",
      "metadata": {
        "platform": "Gmail",
        "timestamp": "2025-10-25T14:30:00",
        "url": "https://mail.google.com/mail/u/0/#inbox/abc123",
        "quote": "Meeting Tomorrow",
        "type": "email",
        "from": "john@example.com",
        "to": "me@gmail.com"
      }
    }
  ]
}
```

---

### 6. **Disconnect Gmail**
```http
POST http://localhost:8000/connectors/gmail/auth/revoke
```

**Response:**
```json
{
  "success": true,
  "message": "Gmail disconnected"
}
```

## 🎨 Frontend Integration Example

Here's how to integrate with your Next.js frontend:

```typescript
// app/settings/connectors/gmail/page.tsx

'use client';

import { useState, useEffect } from 'react';

export default function GmailConnector() {
  const [status, setStatus] = useState({ connected: false });
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    checkStatus();
  }, []);

  async function checkStatus() {
    const res = await fetch('http://localhost:8000/connectors/gmail/status');
    const data = await res.json();
    setStatus(data);
  }

  async function handleConnect() {
    setLoading(true);
    
    // Start OAuth flow
    const res = await fetch('http://localhost:8000/connectors/gmail/auth/start', {
      method: 'POST'
    });
    const { auth_url } = await res.json();
    
    // Open browser for user to sign in
    window.open(auth_url, '_blank');
    
    // Poll for connection
    const interval = setInterval(async () => {
      const status = await checkStatus();
      if (status.connected) {
        clearInterval(interval);
        setLoading(false);
        alert('Gmail connected!');
      }
    }, 2000);
    
    setTimeout(() => clearInterval(interval), 300000); // Stop after 5 min
  }

  async function handleSync() {
    setLoading(true);
    await fetch('http://localhost:8000/connectors/gmail/sync', {
      method: 'POST'
    });
    setLoading(false);
    await checkStatus();
  }

  return (
    <div>
      <h2>Gmail Connector</h2>
      
      {!status.connected ? (
        <button onClick={handleConnect} disabled={loading}>
          {loading ? 'Connecting...' : 'Connect Gmail'}
        </button>
      ) : (
        <div>
          <p>✓ Connected as {status.email}</p>
          <p>Last sync: {status.lastSync}</p>
          <p>Emails synced: {status.emailCount}</p>
          <button onClick={handleSync} disabled={loading}>
            {loading ? 'Syncing...' : 'Sync Now'}
          </button>
        </div>
      )}
    </div>
  );
}
```

## 📁 File Structure

After setup, your file structure will look like:

```
~/.localbrain/credentials/
├── gmail_client_secret.json    # From Google Cloud Console
├── gmail_token.json            # Auto-generated after OAuth
├── gmail_config.json           # Sync state and stats
└── flow_state.json             # Temporary OAuth state

electron/backend/src/connectors/gmail/
├── __init__.py
├── gmail_connector.py          # Main connector class
├── README.md                   # Documentation
└── SETUP.md                    # This file
```

## 🔒 Security & Privacy

- **Read-only access**: Uses `gmail.readonly` scope
- **Local storage**: Tokens stored locally in `~/.localbrain/credentials`
- **Excludes spam/trash**: Automatically filters out unwanted emails
- **Refresh tokens**: Automatically refreshes expired access tokens
- **Revocable**: Easy disconnect via `/auth/revoke` endpoint

## 🐛 Troubleshooting

### Error: "Client secrets file not found"
```bash
# Make sure you've downloaded and placed the file correctly
ls -la ~/.localbrain/credentials/gmail_client_secret.json
```

### Error: "Not authenticated"
```bash
# Check if token file exists
ls -la ~/.localbrain/credentials/gmail_token.json

# If not, run auth flow again
curl -X POST http://localhost:8000/connectors/gmail/auth/start
```

### Error: "Invalid credentials"
```bash
# Delete old tokens and reconnect
rm ~/.localbrain/credentials/gmail_token.json
rm ~/.localbrain/credentials/flow_state.json

# Then reconnect via frontend or:
curl -X POST http://localhost:8000/connectors/gmail/auth/start
```

### Error: "Access blocked: This app is not verified"

This happens in development. Click "Advanced" → "Go to LocalBrain (unsafe)" to proceed.

For production, you'd need to verify your app with Google.

## 📊 Email Format

Emails are converted to this plain text format before ingestion:

```
Subject: Meeting Tomorrow at 3pm
From: john@company.com
To: me@gmail.com
Date: Wed, 25 Oct 2025 14:30:00 +0000

Hi there,

Let's meet tomorrow at 3pm to discuss the project.

Thanks,
John
```

## 🔄 Automatic Ingestion

When you call `/connectors/gmail/sync`, emails are:

1. **Fetched** from Gmail API
2. **Converted** to plain text
3. **Ingested** into your vault using `AgenticIngestionPipeline`
4. **Organized** by the LLM into appropriate vault files
5. **Cited** with source metadata (Gmail URL, sender, date)

The LLM decides which vault files to update based on email content!

## 🎯 Next Steps

1. ✅ Install dependencies
2. ✅ Set up Google Cloud project
3. ✅ Download and place credentials
4. ✅ Start MCP server
5. ✅ Connect Gmail via frontend
6. ✅ Sync your emails!

---

Need help? Check the main README or open an issue.

