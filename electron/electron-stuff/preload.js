const { contextBridge, ipcRenderer } = require('electron');

// Expose Electron APIs to the renderer process
contextBridge.exposeInMainWorld('electron', {
  // Folder picker
  selectDirectory: () => ipcRenderer.invoke('select-directory'),
  
  // Event listeners
  onDirectorySelected: (callback) => {
    ipcRenderer.on('directory-selected', (event, path) => callback(path));
  },
});
