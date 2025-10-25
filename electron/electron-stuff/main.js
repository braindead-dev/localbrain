const { app, BrowserWindow, Menu, Tray, ipcMain, dialog } = require('electron');
const path = require('path');
const fs = require('fs');
const { spawn } = require('child_process');
const axios = require('axios');
const isDev = process.env.NODE_ENV === 'development';

// Set the app name for macOS dock
app.setName('LocalBrain');

// Register protocol handler for localbrain://
if (process.defaultApp) {
  if (process.argv.length >= 2) {
    app.setAsDefaultProtocolClient('localbrain', process.execPath, [path.resolve(process.argv[1])]);
  }
} else {
  app.setAsDefaultProtocolClient('localbrain');
}

let mainWindow;
let tray = null;
let daemonProcess = null;
const DAEMON_PORT = 8765;
const DAEMON_URL = `http://127.0.0.1:${DAEMON_PORT}`;

function createWindow() {
  // Create the browser window
  mainWindow = new BrowserWindow({
    width: 1400,
    height: 900,
    minWidth: 800,
    minHeight: 600,
    webPreferences: {
      nodeIntegration: false,
      contextIsolation: true,
      enableRemoteModule: false,
    },
    icon: isDev
      ? path.join(__dirname, 'assets/icon.png')  // PNG for development
      : path.join(__dirname, 'assets/icon.icns'), // ICNS for production
    titleBarStyle: 'default',
    show: false, // Don't show until ready-to-show
  });

  // Maximize the window on startup for better fullscreen experience
  mainWindow.maximize();

  // Load the Next.js exported files
  const startUrl = isDev
    ? 'http://localhost:3000'
    : `file://${path.join(__dirname, '../app/out/index.html')}`;

  mainWindow.loadURL(startUrl);

  // Show window when ready to prevent visual flash
  mainWindow.once('ready-to-show', () => {
    mainWindow.show();
  });

  // Emitted when the window is closed
  mainWindow.on('closed', () => {
    mainWindow = null;
  });

  // Set up menu (optional)
  const template = [
    {
      label: 'File',
      submenu: [
        {
          label: 'Quit',
          accelerator: process.platform === 'darwin' ? 'Cmd+Q' : 'Ctrl+Q',
          click: () => {
            app.quit();
          },
        },
      ],
    },
    {
      label: 'Edit',
      submenu: [
        { role: 'undo' },
        { role: 'redo' },
        { type: 'separator' },
        { role: 'cut' },
        { role: 'copy' },
        { role: 'paste' },
      ],
    },
    {
      label: 'View',
      submenu: [
        { role: 'reload' },
        { role: 'forceReload' },
        { role: 'toggleDevTools' },
        { type: 'separator' },
        { role: 'resetZoom' },
        { role: 'zoomIn' },
        { role: 'zoomOut' },
        { type: 'separator' },
        { role: 'togglefullscreen' },
      ],
    },
    {
      role: 'window',
      submenu: [{ role: 'minimize' }, { role: 'close' }],
    },
  ];

  if (process.platform === 'darwin') {
    template.unshift({
      label: app.getName(),
      submenu: [
        { role: 'about' },
        { type: 'separator' },
        { role: 'services' },
        { type: 'separator' },
        { role: 'hide' },
        { role: 'hideOthers' },
        { role: 'unhide' },
        { type: 'separator' },
        { role: 'quit' },
      ],
    });

    // Window menu
    template[4].submenu = [
      { role: 'close' },
      { role: 'minimize' },
      { role: 'zoom' },
      { type: 'separator' },
      { role: 'front' },
    ];
  }

  const menu = Menu.buildFromTemplate(template);
  Menu.setApplicationMenu(menu);
}

// Python Daemon Management
async function startDaemon() {
  if (daemonProcess) {
    console.log('Daemon already running');
    return;
  }

  // Check if port is already in use
  const isPortInUse = await checkDaemonHealth();
  if (isPortInUse) {
    console.log('✅ Daemon already running on port 8765');
    updateTrayStatus(true);
    return;
  }

  const backendDir = path.join(__dirname, '../backend');
  const daemonScript = path.join(backendDir, 'src', 'daemon.py');
  
  console.log('Starting Python daemon...');
  console.log('Backend dir:', backendDir);
  console.log('Daemon script:', daemonScript);

  // Use conda environment's python
  // Check for conda environment first
  const homeDir = require('os').homedir();
  const condaPaths = [
    path.join(homeDir, 'miniconda3', 'envs', 'localbrain', 'bin', 'python'),
    path.join(homeDir, 'anaconda3', 'envs', 'localbrain', 'bin', 'python'),
    path.join(homeDir, 'miniforge3', 'envs', 'localbrain', 'bin', 'python'),
  ];
  
  let pythonCmd = 'python3'; // Fallback
  
  // Find conda python
  for (const condaPath of condaPaths) {
    if (fs.existsSync(condaPath)) {
      pythonCmd = condaPath;
      console.log('Using conda python:', pythonCmd);
      break;
    }
  }
  
  if (pythonCmd === 'python3') {
    console.log('⚠️  Could not find conda environment, using system python3');
    console.log('   Make sure to run: conda create -n localbrain python=3.10');
  }
  
  daemonProcess = spawn(pythonCmd, [daemonScript], {
    cwd: backendDir,
    env: { ...process.env },
    stdio: ['ignore', 'pipe', 'pipe']
  });

  daemonProcess.stdout.on('data', (data) => {
    console.log(`[Daemon] ${data.toString().trim()}`);
  });

  daemonProcess.stderr.on('data', (data) => {
    console.error(`[Daemon Error] ${data.toString().trim()}`);
  });

  daemonProcess.on('close', (code) => {
    console.log(`Daemon process exited with code ${code}`);
    if (code === 1) {
      console.log('❌ Daemon failed to start (likely port 8765 already in use)');
    }
    daemonProcess = null;
    updateTrayStatus(false);
  });

  // Wait a bit for daemon to start
  setTimeout(() => checkDaemonHealth(), 2000);
}

function stopDaemon() {
  if (daemonProcess) {
    console.log('Stopping Python daemon...');
    daemonProcess.kill('SIGTERM');
    daemonProcess = null;
  }
}

async function checkDaemonHealth() {
  try {
    const response = await axios.get(`${DAEMON_URL}/health`, { timeout: 2000 });
    const isHealthy = response.status === 200;
    updateTrayStatus(isHealthy);
    return isHealthy;
  } catch (error) {
    updateTrayStatus(false);
    return false;
  }
}

// Tray Management
function createTray() {
  // Create a simple 16x16 template icon for macOS menu bar
  // Template icons are monochrome and adapt to light/dark mode
  const { nativeImage } = require('electron');
  
  // Create a simple 16x16 icon (you can replace with actual icon file)
  // For now, use a simple text-based icon
  const icon = nativeImage.createEmpty();
  
  // Try to load icon file, fall back to empty if not found
  const iconPath = path.join(__dirname, 'assets/tray-icon.png');
  try {
    const loadedIcon = nativeImage.createFromPath(iconPath);
    if (!loadedIcon.isEmpty()) {
      tray = new Tray(loadedIcon.resize({ width: 16, height: 16 }));
    } else {
      // Use a simple emoji as fallback
      tray = new Tray(nativeImage.createFromDataURL('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAdgAAAHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAGBSURBVDiNpdM/S8NAGMfx7+XSGpQWxUGQFgcHQRB8AZ1c3HwRLroIvoROgpu4uLo4ODk4+AZcxMVFBEGhIIKDVRRE/5T+ye1yGdI0TRMHH3K55+7z3D33JJIkCSEEhmEwGo0wTRPTNBmPx+i6/j/BZDLBNE1UVcU0TXRdRwgBIQSmaSKEQAjBaDRCCMFoNELTNDRNwzRNdF1nMBgghGAwGKBpGpqmoaoqmqYxHA4RQjAcDlFVFVVVGY/HCCEYj8cMh0NUVWUymaCqKpPJBF3X0XWd/n+g6zr9fh9N0+j3+/R6PXq9Hr1ej263S7fbpdfr0el06Ha7dDodOp0O7Xabbrd9u027Xafdbttutsnt22223bfb22y323Q6HTqdDu12m1arRavVotVq0Wq1aLVatFotms0mzWaTZrNJs9mk0WjQaDRoNBo0Gg3q9Tr1ep16vU69XqderxvtdprU6/U09Xrd+P3lM75p8x0='));
    }
  } catch (error) {
    console.log('Could not load tray icon, using fallback');
    tray = new Tray(nativeImage.createFromDataURL('data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABHNCSVQICAgIfAhkiAAAAAlwSFlzAAAAdgAAAHYBTnsmCAAAABl0RVh0U29mdHdhcmUAd3d3Lmlua3NjYXBlLm9yZ5vuPBoAAAGBSURBVDiNpdM/S8NAGMfx7+XSGpQWxUGQFgcHQRB8AZ1c3HwRLroIvoROgpu4uLo4ODk4+AZcxMVFBEGhIIKDVRRE/5T+ye1yGdI0TRMHH3K55+7z3D33JJIkCSEEhmEwGo0wTRPTNBmPx+i6/j/BZDLBNE1UVcU0TXRdRwgBIQSmaSKEQAjBaDRCCMFoNELTNDRNwzRNdF1nMBgghGAwGKBpGpqmoaoqmqYxHA4RQjAcDlFVFVVVGY/HCCEYj8cMh0NUVWUymaCqKpPJBF3X0XWd/n+g6zr9fh9N0+j3+/R6PXq9Hr1ej263S7fbpdfr0el06Ha7dDodOp0O7Xabbrd9u027Xafdbttutsnt22223bfb22y323Q6HTqdDu12m1arRavVotVq0Wq1aLVatFotms0mzWaTZrNJs9mk0WjQaDRoNBo0Gg3q9Tr1ep16vU69XqderxvtdprU6/U09Xrd+P3lM75p8x0='));
  }
  
  tray.setToolTip('LocalBrain');
  tray.setTitle(''); // Don't show text by default
  
  updateTrayMenu(false); // Start with "checking" status
  
  // Prevent tray from being destroyed
  tray.on('destroyed', () => {
    console.log('Tray was destroyed!');
  });
  
  // No click handler - tray and window are independent
  // Use the context menu "Show Window" / "Hide Window" options instead
  
  // Start health check interval
  setInterval(checkDaemonHealth, 5000);
}

function updateTrayMenu(daemonRunning) {
  const contextMenu = Menu.buildFromTemplate([
    {
      label: daemonRunning ? '● Backend Running' : '○ Backend Stopped',
      enabled: false
    },
    { type: 'separator' },
    {
      label: 'Show Window',
      click: () => {
        if (mainWindow) {
          mainWindow.show();
        } else {
          createWindow();
        }
      }
    },
    {
      label: 'Hide Window',
      click: () => {
        if (mainWindow) {
          mainWindow.hide();
        }
      }
    },
    { type: 'separator' },
    {
      label: daemonRunning ? 'Stop Backend' : 'Start Backend',
      click: () => {
        if (daemonRunning) {
          stopDaemon();
        } else {
          startDaemon();
        }
      }
    },
    { type: 'separator' },
    {
      label: 'Quit LocalBrain',
      click: () => {
        app.quit();
      }
    }
  ]);
  
  tray.setContextMenu(contextMenu);
}

function updateTrayStatus(isRunning) {
  if (!tray) {
    console.log('⚠️  Tray not initialized yet, skipping status update');
    return;
  }
  updateTrayMenu(isRunning);
  // Use emoji for better visibility
  tray.setTitle(isRunning ? '🟢' : '⚫');
}

// IPC handlers
ipcMain.handle('select-directory', async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    properties: ['openDirectory'],
    title: 'Choose Your Vault Directory',
    message: 'Select the directory that contains your markdown files and folders',
  });

  if (!result.canceled && result.filePaths.length > 0) {
    const selectedPath = result.filePaths[0];
    mainWindow.webContents.send('directory-selected', selectedPath);
    return selectedPath;
  }

  return null;
});

// App lifecycle
app.whenReady().then(async () => {
  // Create tray first (daemon startup needs it for status updates)
  createTray();

  // Start backend daemon on app launch
  await startDaemon();

  // Create window
  createWindow();
});

// Don't quit when windows close - keep daemon running
app.on('window-all-closed', () => {
  // On macOS, apps typically stay running even after all windows close
  // On Windows/Linux, we also want to keep running for the background daemon
  // Do NOT call app.quit() here - let the tray menu handle quitting
  console.log('All windows closed, but keeping app and daemon running');
});

app.on('activate', () => {
  if (BrowserWindow.getAllWindows().length === 0) {
    createWindow();
  }
});

// Handle protocol URLs (localbrain://...)
app.on('open-url', async (event, url) => {
  event.preventDefault();
  console.log('Received protocol URL:', url);
  
  try {
    // Forward to daemon
    const response = await axios.get(`${DAEMON_URL}/protocol/parse`, {
      params: { url },
      timeout: 5000
    });
    
    const { command, parameters } = response.data;
    console.log('Parsed command:', command);
    console.log('Parameters:', parameters);
    
    // Handle different commands
    if (command === 'ingest') {
      const ingestResponse = await axios.post(`${DAEMON_URL}/protocol/ingest`, parameters, {
        timeout: 60000 // Ingestion can take time
      });
      
      console.log('Ingestion result:', ingestResponse.data);
      
      // Show notification
      if (mainWindow) {
        mainWindow.webContents.send('protocol-command', {
          command,
          success: true,
          result: ingestResponse.data
        });
      }
    } else if (command === 'search') {
      // Natural language search
      console.log('Search query:', parameters.q || parameters.query);
      
      const searchResponse = await axios.post(`${DAEMON_URL}/protocol/search`, parameters, {
        timeout: 30000 // Search can take time with LLM calls
      });
      
      console.log('Search result:', searchResponse.data);
      
      // Show notification
      if (mainWindow) {
        mainWindow.webContents.send('protocol-command', {
          command,
          success: true,
          result: searchResponse.data
        });
      }
    }
  } catch (error) {
    console.error('Error handling protocol URL:', error);
    if (mainWindow) {
      mainWindow.webContents.send('protocol-command', {
        command: 'unknown',
        success: false,
        error: error.message
      });
    }
  }
});

// Handle protocol URLs on Windows/Linux (passed as command line argument)
const gotTheLock = app.requestSingleInstanceLock();

if (!gotTheLock) {
  app.quit();
} else {
  app.on('second-instance', (event, commandLine, workingDirectory) => {
    // Someone tried to run a second instance, focus our window instead
    if (mainWindow) {
      if (mainWindow.isMinimized()) mainWindow.restore();
      mainWindow.focus();
    }
    
    // Check for protocol URL in command line
    const url = commandLine.find(arg => arg.startsWith('localbrain://'));
    if (url) {
      app.emit('open-url', null, url);
    }
  });
}

// Clean shutdown when quitting
app.on('before-quit', (event) => {
  console.log('App quitting - stopping daemon...');
  stopDaemon();
});

// Also handle SIGINT/SIGTERM
process.on('SIGINT', () => {
  console.log('Received SIGINT');
  stopDaemon();
  app.quit();
});

process.on('SIGTERM', () => {
  console.log('Received SIGTERM');
  stopDaemon();
  app.quit();
});
