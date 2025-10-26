# LocalBrain Electron App

Desktop application for LocalBrain - combines Next.js frontend with Python backend.

---

## Structure

```
electron/
├── app/              # Next.js frontend (Port 3000)
├── backend/          # FastAPI backend (Port 8765)
└── package.json      # Electron configuration
```

---

## Development

### Start Backend

```bash
cd backend
python src/daemon.py
```

### Start Frontend

```bash
cd app
npm install
npm run dev
```

### Desktop App

```bash
npm run dev:electron
```

---

## Building

### Package Desktop App

```bash
npm run build
npm run package
```

Outputs to `dist/`.

---

## Documentation

See [main docs](../docs/) for detailed information:
- [Quick Start](../docs/QUICKSTART.md)
- [Architecture](../docs/ARCHITECTURE.md)
- [API Reference](../docs/API.md)
