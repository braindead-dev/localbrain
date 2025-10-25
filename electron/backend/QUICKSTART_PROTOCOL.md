# Quick Start: Background Service & Protocol

Get LocalBrain running as a background service with `localbrain://` protocol in 5 minutes.

---

## 1. Install Dependencies

```bash
conda activate localbrain
cd electron/backend
pip install fastapi uvicorn rumps requests
```

## 2. Register Protocol

```bash
./scripts/setup_protocol.sh
```

This registers `localbrain://` with macOS.

## 3. Start Background Service

```bash
python src/tray.py
```

You'll see **LocalBrain** in your menu bar with status: ✅ Running

## 4. Test It!

```bash
# Test via URL protocol
open "localbrain://ingest?text=Hello%20from%20protocol!&platform=Test"

# Test via API
curl -X POST http://localhost:8765/protocol/ingest \
  -H "Content-Type: application/json" \
  -d '{"text": "Hello from API!", "platform": "curl"}'
```

## 5. Check Results

```bash
# View logs
tail -f /tmp/localbrain-daemon.log

# Check your vault
ls ~/Documents/GitHub/localbrain/my-vault/
```

---

## Daily Usage

The tray app stays in your menu bar. Use it to:
- ✅ See service status
- ▶️ Start/Stop daemon
- 🚪 Quit LocalBrain

**From anywhere in macOS:**
```bash
open "localbrain://ingest?text=Your%20content&platform=YourApp"
```

---

## Integration Examples

### Alfred Workflow

Create a workflow that runs:
```bash
open "localbrain://ingest?text={query}&platform=Alfred"
```

### Raycast Script

```bash
#!/bin/bash
encoded=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$1'))")
open "localbrain://ingest?text=$encoded&platform=Raycast"
```

### From any app

```python
import urllib.parse, subprocess

text = "My note"
url = f"localbrain://ingest?text={urllib.parse.quote(text)}&platform=MyApp"
subprocess.run(["open", url])
```

---

## Metadata Fields

When calling `localbrain://ingest`:

**Required:**
- `text` - Content to ingest

**Optional:**
- `platform` - Source platform (e.g., "Gmail", "Discord", "Manual")
- `timestamp` - ISO 8601 format (e.g., "2024-10-25T15:00:00Z")
- `url` - Source URL

**Auto-generated:**
- `quote` - LLM picks the best excerpt during ingestion

---

## Troubleshooting

**Service not starting?**
```bash
# Check if port 8765 is available
lsof -i :8765

# View logs
tail -f /tmp/localbrain-daemon.log
```

**Protocol not working?**
```bash
# Re-register
./scripts/setup_protocol.sh

# Test manually
python src/protocol_handler.py "localbrain://ingest?text=test&platform=manual"
```

---

That's it! Your LocalBrain is now running in the background and ready to ingest from anywhere. 🚀
