const { contextBridge, ipcRenderer } = require('electron');

// Expose Electron APIs to the renderer process
contextBridge.exposeInMainWorld('electron', {
  // Folder picker
  selectDirectory: () => ipcRenderer.invoke('select-directory'),

  // Open URL in system browser
  openExternal: (url) => ipcRenderer.invoke('open-external', url),

  // Event listeners
  onDirectorySelected: (callback) => {
    ipcRenderer.on('directory-selected', (event, path) => callback(path));
  },
});
