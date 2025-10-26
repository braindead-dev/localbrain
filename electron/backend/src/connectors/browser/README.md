# Browser History Connector

Ingests browsing history from Chromium-based browsers into your LocalBrain vault.

## Supported Browsers

- **Google Chrome**
- **Microsoft Edge**
- **Brave Browser**
- Any Chromium-based browser

## Setup

### Auto-Detection (Easiest)

The connector will automatically detect your default Chrome installation:

```bash
POST /connectors/browser/auth
{}
```

### Manual Browser Selection

Specify which browser to use:

```bash
POST /connectors/browser/auth
{
  "browser": "chrome"  # or "edge", "brave"
}
```

### Custom Path

If your browser history is in a non-standard location:

```bash
POST /connectors/browser/auth
{
  "history_path": "/path/to/History",
  "browser_name": "Custom Browser"
}
```

## Default Paths

**macOS**:
- Chrome: `~/Library/Application Support/Google/Chrome/Default/History`
- Edge: `~/Library/Application Support/Microsoft Edge/Default/History`
- Brave: `~/Library/Application Support/BraveSoftware/Brave-Browser/Default/History`

**Linux**:
- Chrome: `~/.config/google-chrome/Default/History`
- Edge: `~/.config/microsoft-edge/Default/History`

**Windows**:
- Chrome: `%LOCALAPPDATA%\Google\Chrome\User Data\Default\History`
- Edge: `%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\History`

## Sync

Sync recent browsing history:

```bash
POST /connectors/browser/sync?hours=24&limit=100&auto_ingest=true
```

**Parameters**:
- `hours` (default: 24): Look back this many hours
- `limit` (default: 100): Maximum URLs to sync
- `auto_ingest` (default: true): Automatically ingest into vault

## What Gets Ingested

Each visited URL is saved as a markdown file with:

```markdown
# Page Title

**URL**: https://example.com/page
**Last Visited**: 2025-10-25T17:30:00
**Visit Count**: 5
```

**Metadata**:
- Source: `browser`
- Browser name
- URL and domain
- Visit count and timestamp
- Tags: `browser`, `web`, domain name

**File naming**: `browser_example.com_2025-10-25.md`

## Status

Check connector status:

```bash
GET /connectors/browser/status
```

Returns:
- Connection status
- Browser name
- History file path
- Total URLs in database
- Last sync time

## Use Cases

- **Research tracking**: Keep record of websites you visited while researching
- **Learning history**: Track educational content you've consumed
- **Work context**: Remember tools/docs you referenced
- **Search**: Find that page you visited last week but can't remember the URL

## Privacy Note

Browser history is stored locally in your vault. The connector only reads from your local browser database and never sends data externally.

## Tips

1. **Close browser before syncing**: Chrome locks the History file while running. The connector creates a temporary copy, but you might need to close Chrome for best results.

2. **Regular syncs**: Set up auto-sync to continuously capture your browsing:
   ```bash
   # The daemon auto-syncs every 10 minutes by default
   ```

3. **Filter by time**: Use the `hours` parameter to focus on recent activity:
   ```bash
   # Last hour only
   POST /connectors/browser/sync?hours=1
   ```

4. **Domain-based search**: Search by domain to find all pages from a site:
   ```bash
   POST /protocol/search
   {"query": "github.com documentation"}
   ```
