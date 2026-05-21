export {};

declare global {
  interface Window {
    /**
     * Electron bridge exposed by preload.js via contextBridge.
     * Note: the API name is "electron" (not "electronAPI") as set in preload.js.
     */
    electron: {
      selectDirectory: () => Promise<string | null>;
      onDirectorySelected: (callback: (path: string) => void) => void;
    };
  }
}
