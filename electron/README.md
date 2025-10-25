# LocalBrain Desktop App

A desktop application that wraps the LocalBrain Next.js frontend in Electron.

## Project Structure

```
electron/
├── app/                    # Next.js frontend
│   ├── src/               # Next.js source code
│   ├── public/            # Static assets
│   ├── package.json       # Next.js dependencies
│   └── next.config.ts     # Next.js configuration
├── backend/               # Backend code (ignored for now)
├── electron-stuff/        # Electron-specific files
│   ├── main.js            # Electron main process
│   ├── assets/            # App icons and images
│   ├── node_modules/      # Electron dependencies
│   └── dist/              # Build output
└── package.json           # Main project configuration
```

## Development

### Prerequisites

- Node.js 16+
- npm or yarn
- For macOS builds: Xcode command line tools (`xcode-select --install`)

### Setup

1. Install dependencies:
```bash
npm install
```

2. This will also install Next.js dependencies in the `app/` directory.

### Development Mode

Run both Next.js dev server and Electron simultaneously:

```bash
npm run dev
```

This will:
- Start Next.js dev server on http://localhost:3000
- Launch Electron app that loads the dev server
- **Window starts maximized** for better desktop experience
- **Dock shows "LocalBrain"** instead of "Electron"
- Enable hot reloading for both frontend and Electron

### Building for Production

1. Build the Next.js app for static export:
```bash
npm run build:next
```

2. Build and package the Electron app:
```bash
npm run build
```

This creates distributable packages in the `dist/` directory:
- `LocalBrain-1.0.0.dmg` - macOS installer
- `LocalBrain-1.0.0.zip` - macOS portable app

## Customization

### App Icons

Replace the following files in the `electron-stuff/assets/` directory with your own icons:

- `icon.png` - Base icon (PNG format)
- `icon.icns` - macOS icon (ICNS format) - Required for production builds

For development, the PNG icon is used. For production builds, you'll need an ICNS file.

To create an ICNS file from PNG:
```bash
# Using iconutil (macOS built-in)
mkdir icon.iconset
# Create multiple sizes: 16x16, 32x32, 64x64, 128x128, 256x256, 512x512, 1024x1024
iconutil -c icns icon.iconset
mv icon.icns electron-stuff/assets/
```

### App Configuration

Edit the root `package.json` to customize:

- `name` - App name
- `build.appId` - Unique app identifier (format: com.company.app)
- `build.productName` - Display name in menus/finder
- `build.mac.category` - App Store category

### Code Signing (for Distribution)

For distributing outside the Mac App Store, you'll need to codesign:

1. Get a Developer ID Application certificate from Apple
2. Update the build configuration in `package.json`:
```json
{
  "build": {
    "mac": {
      "identity": "Developer ID Application: Your Name (TEAMID)"
    }
  }
}
```

3. For App Store distribution, use:
```json
{
  "build": {
    "mac": {
      "identity": "3rd Party Mac Developer Application: Your Name (TEAMID)"
    }
  }
}
```

## Mac Developer Account

**Do you need a Mac Developer account?**

- **For development/testing**: No, you can run unsigned apps
- **For distributing to others**: Yes, you need to codesign the app
- **For Mac App Store**: Yes, you need a paid developer account ($99/year)

Without codesigning, users will get security warnings when running the app.

## Troubleshooting

### Common Issues

1. **Build fails with permission errors**: Run `sudo npm run build` or fix permissions
2. **Icon not showing**: Ensure `electron-stuff/assets/icon.icns` exists for production builds
3. **App won't start**: Check that Next.js export completed successfully in `app/out/`
4. **White screen**: Check browser console for Next.js errors

### Rebuilding

If you make changes to the Next.js app:

1. Rebuild Next.js: `npm run build:next`
2. Restart Electron dev: `npm run dev:electron`

## Window Behavior

- **Development**: Window starts maximized and shows "LocalBrain" in dock
- **Production**: Window starts maximized, content fills entire window space
- **Window Controls**: Full macOS window controls (minimize, maximize, close) are available
- **Responsive**: Content adapts to window resizing

## Next.js Configuration

The Next.js app is configured for static export in `app/next.config.ts`:

- `output: 'export'` - Enables static HTML export
- `trailingSlash: true` - Ensures compatibility with file:// protocol
- `images: { unoptimized: true }` - Disables Next.js image optimization for static export

## Backend Integration

To integrate with the backend later:

1. The Electron main process can make HTTP requests to your backend
2. Or run the backend as a separate process and communicate via WebSocket/HTTP
3. Update the Next.js app to proxy API requests through Electron if needed

See `electron-stuff/main.js` for examples of how to add backend communication.