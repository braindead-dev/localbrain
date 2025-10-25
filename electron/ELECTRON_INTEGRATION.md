# Electron + Backend Integration

The Electron app now manages the Python background daemon automatically!

---

## How It Works

### On App Start
1. Electron launches
2. Python daemon starts automatically
3. Tray icon appears in menu bar (●/○ shows status)
4. Window opens

### On Window Close
1. Window closes
2. **Daemon keeps running** ✅
3. Tray icon remains visible
4. App still active in background

### On Quit (from tray)
1. User clicks "Quit LocalBrain" in tray menu
2. Daemon stops gracefully
3. Electron quits completely

---

## Menu Tray

<img src="https://placehold.co/300x200/EEE/31343C/?text=LocalBrain+●" alt="Tray Menu"/>

**Tray Menu:**
```
LocalBrain               ●
├─ ● Backend Running     (status indicator)
├─ ─────────────────
├─ Show Window
├─ Hide Window
├─ ─────────────────
├─ Stop Backend
├─ ─────────────────
└─ Quit LocalBrain       ⚠️ This stops everything
```

**Status Indicators:**
- `●` = Backend running (green dot)
- `○` = Backend stopped (gray circle)

**Click behavior:**
- Click tray icon → Toggle window visibility
- Right-click / Left-click hold → Show menu

---

## Protocol Handling

The app automatically handles `localbrain://` URLs!

**How it works:**
```
1. System opens: localbrain://ingest?text=...
2. Electron receives URL
3. Forwards to Python daemon
4. Daemon processes ingestion
5. Electron gets result
6. Shows notification (optional)
```

**Example:**
```bash
open "localbrain://ingest?text=Test%20from%20URL&platform=Test"
```

Electron automatically:
- Parses the URL
- Forwards to daemon at `http://localhost:8765`
- Handles the response
- Sends result to renderer (if window open)

---

## Setup

### 1. Install Dependencies

```bash
cd electron
npm install
```

This installs `axios` for HTTP requests to the daemon.

### 2. Backend Setup

Make sure Python backend is set up:
```bash
cd backend
conda activate localbrain
pip install -r requirements.txt
```

### 3. Run in Development

```bash
npm run dev
```

This will:
- Start Next.js dev server (port 3000)
- Launch Electron
- Auto-start Python daemon
- Show tray icon

---

## Architecture

```
┌─────────────────────────────────────┐
│     Electron Main Process           │
│  (electron-stuff/main.js)           │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Spawns Python Daemon          │ │
│  │ spawn('python3', ['daemon.py'])│ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Creates Tray Icon             │ │
│  │ - Show/Hide window            │ │
│  │ - Start/Stop daemon           │ │
│  │ - Quit app                    │ │
│  └───────────────────────────────┘ │
│                                     │
│  ┌───────────────────────────────┐ │
│  │ Protocol Handler              │ │
│  │ localbrain:// → daemon        │ │
│  └───────────────────────────────┘ │
└─────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────┐
│  Python Daemon (background)         │
│  FastAPI on :8765                   │
│                                     │
│  - /protocol/ingest                 │
│  - /protocol/parse                  │
│  - /health                          │
└─────────────────────────────────────┘
                │
                ↓
┌─────────────────────────────────────┐
│  Your Vault                         │
│  Markdown + JSON files              │
└─────────────────────────────────────┘
```

---

## Key Features

### ✅ Automatic Daemon Management
- Electron spawns Python process on start
- Monitors health every 5 seconds
- Graceful shutdown on quit

### ✅ Always-On Background Service
- Window can close, daemon keeps running
- Perfect for system-wide ingestion
- No need to keep window open

### ✅ Native Protocol Integration
- `localbrain://` registered with OS
- Electron forwards to daemon
- Works from any app

### ✅ Tray Integration
- Status indicator (running/stopped)
- Quick access controls
- Show/hide window

---

## Code Overview

### Main Process (`electron-stuff/main.js`)

**Daemon Management:**
```javascript
function startDaemon() {
  const daemonScript = path.join(__dirname, '../backend/src/daemon.py');
  daemonProcess = spawn('python3', [daemonScript], { ... });
  // Monitor stdout/stderr, handle crashes
}

function stopDaemon() {
  daemonProcess.kill('SIGTERM');
}
```

**Tray Creation:**
```javascript
function createTray() {
  tray = new Tray(iconPath);
  tray.setToolTip('LocalBrain');
  updateTrayMenu(isRunning);
  
  // Health check every 5 seconds
  setInterval(checkDaemonHealth, 5000);
}
```

**Protocol Handling:**
```javascript
app.on('open-url', async (event, url) => {
  // Parse: localbrain://ingest?text=...
  const { command, parameters } = await axios.get(
    `${DAEMON_URL}/protocol/parse?url=${url}`
  );
  
  // Forward to daemon
  if (command === 'ingest') {
    await axios.post(`${DAEMON_URL}/protocol/ingest`, parameters);
  }
});
```

**Lifecycle:**
```javascript
app.whenReady().then(() => {
  startDaemon();    // 1. Start Python
  createTray();     // 2. Show tray icon
  createWindow();   // 3. Open window
});

// Don't quit when window closes
app.on('window-all-closed', () => {
  // Just log, don't quit
  console.log('Window closed, daemon still running');
});

// Only quit from tray menu
app.on('before-quit', () => {
  stopDaemon();  // Clean shutdown
});
```

---

## Configuration

### Change Daemon Port

Edit `electron-stuff/main.js`:
```javascript
const DAEMON_PORT = 8765;  // Your preferred port
```

Also update `backend/src/daemon.py`:
```python
PORT = 8765  // Match Electron
```

### Python Command

By default uses `python3`. To use conda environment:

```javascript
const pythonCmd = '/path/to/conda/envs/localbrain/bin/python';
```

Or set up environment activation in spawn options:
```javascript
daemonProcess = spawn('python3', [daemonScript], {
  cwd: backendDir,
  env: {
    ...process.env,
    CONDA_DEFAULT_ENV: 'localbrain'
  }
});
```

---

## Building for Production

### macOS

```bash
npm run build
```

This creates:
- `dist/LocalBrain-1.0.0.dmg` - Installer
- `dist/LocalBrain-1.0.0-mac.zip` - Portable app

**Important:** The Python daemon must be bundled!

Add to `package.json`:
```json
"build": {
  "files": [
    "electron-stuff/main.js",
    "app/out/**/*",
    "backend/**/*"  // ← Include Python backend
  ],
  "extraResources": [
    {
      "from": "backend",
      "to": "backend",
      "filter": ["**/*", "!**/__pycache__", "!**/node_modules"]
    }
  ]
}
```

Then update daemon path in production:
```javascript
const backendDir = app.isPackaged
  ? path.join(process.resourcesPath, 'backend')
  : path.join(__dirname, '../backend');
```

---

## Troubleshooting

### Daemon not starting

**Check logs:**
```bash
# Electron logs
npm run dev  # Look at terminal output

# Daemon logs
tail -f /tmp/localbrain-daemon.log
```

**Common issues:**
- Python not in PATH → Use full path to python
- Missing dependencies → Run `pip install -r requirements.txt`
- Port already in use → Change DAEMON_PORT

### Tray icon not showing

**macOS:** Make sure you have an icon file at `electron-stuff/assets/icon.png`

**Create placeholder:**
```bash
cd electron-stuff/assets
# Use any 16x16 or 32x32 PNG
```

### Protocol not working

**Register manually:**
```bash
# From your terminal
open "localbrain://ingest?text=test&platform=manual"
```

**Check if Electron is set as handler:**
```bash
# macOS
open -a LocalBrain "localbrain://ingest?text=test"
```

### Window won't close (keeps quitting app)

Check `window-all-closed` handler:
```javascript
app.on('window-all-closed', () => {
  // DON'T call app.quit() here!
  console.log('Window closed, daemon still running');
});
```

---

## Development Workflow

### Running

```bash
# Terminal 1: Watch backend changes (optional)
cd backend && conda activate localbrain

# Terminal 2: Run Electron
cd electron && npm run dev
```

### Testing

1. **Check tray icon** - Should appear in menu bar
2. **Check daemon** - `curl http://localhost:8765/health`
3. **Test ingestion** - `open "localbrain://ingest?text=Test"`
4. **Close window** - Daemon should keep running
5. **Quit from tray** - Everything stops

---

## Next Steps

- [ ] Add desktop notifications for ingestion results
- [ ] Show recent ingestions in tray menu
- [ ] Add progress indicator during ingestion
- [ ] Bundle Python with PyInstaller for production
- [ ] Add auto-updater for both Electron and Python
- [ ] Windows/Linux support

---

## Summary

✅ **Fully integrated** - Electron manages Python daemon  
✅ **Always-on** - Daemon persists when window closes  
✅ **Native tray** - macOS menu bar integration  
✅ **Protocol support** - `localbrain://` URLs work  
✅ **Clean lifecycle** - Graceful start/stop  

Just run `npm run dev` and everything works together! 🚀
