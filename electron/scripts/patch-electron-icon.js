#!/usr/bin/env node
// Patches the local Electron binary to use the LocalBrain icon and bundle name.
// Runs automatically via postinstall so it survives npm install.

const { execSync } = require('child_process');
const path = require('path');
const fs = require('fs');

const electronApp = path.join(__dirname, '..', 'node_modules', 'electron', 'dist', 'Electron.app');
const plist = path.join(electronApp, 'Contents', 'Info.plist');
const iconSrc = path.join(__dirname, '..', 'electron-stuff', 'assets', 'icon.icns');
const iconDest = path.join(electronApp, 'Contents', 'Resources', 'electron.icns');

if (!fs.existsSync(electronApp)) {
  console.log('Electron.app not found, skipping icon patch.');
  process.exit(0);
}

try {
  const pb = (cmd) => execSync(`/usr/libexec/PlistBuddy -c "${cmd}" "${plist}"`, { stdio: 'pipe' });
  pb('Set :CFBundleDisplayName LocalBrain');
  pb('Set :CFBundleName LocalBrain');
  pb('Set :CFBundleIdentifier com.localbrain.app');

  fs.copyFileSync(iconSrc, iconDest);
  execSync(`touch "${electronApp}"`);

  console.log('✅ Electron icon patched successfully.');
} catch (err) {
  console.warn('⚠️  Icon patch failed (non-fatal):', err.message);
}
