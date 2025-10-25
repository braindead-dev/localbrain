'use client';

import { useState, useEffect } from 'react';

export default function Home() {
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  useEffect(() => {
    // Listen for directory selection events
    if (window.electronAPI) {
      window.electronAPI.onDirectorySelected((path: string) => {
        setSelectedPath(path);
        setIsLoading(false);
      });

      return () => {
        window.electronAPI.removeDirectoryListener();
      };
    }
  }, []);

  const handleSelectDirectory = async () => {
    if (window.electronAPI) {
      setIsLoading(true);
      try {
        await window.electronAPI.selectDirectory();
      } catch (error) {
        console.error('Failed to select directory:', error);
        setIsLoading(false);
      }
    }
  };

  return (
    <div className="min-h-screen w-full bg-gradient-to-br from-slate-50 to-slate-100 dark:from-slate-900 dark:to-slate-800 flex items-center justify-center p-8">
      <div className="max-w-md w-full space-y-8">
        <div className="text-center">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-slate-100 mb-2">
            LocalBrain
          </h1>
          <p className="text-slate-600 dark:text-slate-400">
            Your personal knowledge workspace
          </p>
        </div>

        <div className="bg-white dark:bg-slate-800 rounded-xl shadow-lg p-8 space-y-6">
          <div className="text-center space-y-4">
            <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mx-auto">
              <svg
                className="w-8 h-8 text-blue-600 dark:text-blue-400"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2H5a2 2 0 00-2-2z"
                />
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M8 5a2 2 0 012-2h4a2 2 0 012 2v2H8V5z"
                />
              </svg>
            </div>

            <div>
              <h2 className="text-xl font-semibold text-slate-900 dark:text-slate-100 mb-2">
                Choose Your Vault Directory
              </h2>
              <p className="text-slate-600 dark:text-slate-400 text-sm">
                Select the folder that contains your markdown files, notes, and subdirectories
              </p>
            </div>
          </div>

          <button
            onClick={handleSelectDirectory}
            disabled={isLoading}
            className="w-full bg-blue-600 hover:bg-blue-700 disabled:bg-blue-400 text-white font-medium py-3 px-4 rounded-lg transition-colors duration-200 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <svg className="animate-spin h-5 w-5" fill="none" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
                  />
                </svg>
                Opening directory picker...
              </>
            ) : (
              'Choose Directory'
            )}
          </button>

          {selectedPath && (
            <div className="mt-4 p-4 bg-green-50 dark:bg-green-900/20 border border-green-200 dark:border-green-800 rounded-lg">
              <div className="flex items-center gap-2">
                <svg
                  className="w-5 h-5 text-green-600 dark:text-green-400"
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path
                    strokeLinecap="round"
                    strokeLinejoin="round"
                    strokeWidth={2}
                    d="M5 13l4 4L19 7"
                  />
                </svg>
                <span className="text-sm text-green-800 dark:text-green-200 font-medium">
                  Vault selected:
                </span>
              </div>
              <p className="text-sm text-green-700 dark:text-green-300 mt-1 font-mono break-all">
                {selectedPath}
              </p>
            </div>
          )}
        </div>

        <div className="text-center">
          <p className="text-xs text-slate-500 dark:text-slate-500">
            Your vault directory will be used to store and organize your markdown files
          </p>
        </div>
      </div>
    </div>
  );
}
