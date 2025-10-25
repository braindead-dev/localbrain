export {};

declare global {
  interface Window {
    electronAPI: {
      selectDirectory: () => Promise<string | null>;
      onDirectorySelected: (callback: (path: string) => void) => void;
      removeDirectoryListener: () => void;
    };
  }
}
