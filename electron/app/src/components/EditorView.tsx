import { useState, useEffect } from "react";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";
import { FileText, Save, FolderOpen, Loader2, AlertCircle } from "lucide-react";
import { api } from "../lib/api";
import { toast } from "sonner";

interface EditorViewProps {
  initialFilePath?: string;
  initialContent?: string;
  showLineNumbers?: boolean;
}

export function EditorView({ initialFilePath, initialContent = "", showLineNumbers = false }: EditorViewProps) {
  const [content, setContent] = useState(initialContent);
  const [filePath, setFilePath] = useState<string | null>(initialFilePath || null);
  const [isSaved, setIsSaved] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [citations, setCitations] = useState<Record<string, any>>({});

  // Load file when initialFilePath changes
  useEffect(() => {
    if (initialFilePath) {
      // Always load if we have an initialFilePath, even if it's the "same" file
      // This fixes the issue where clicking a file after highlighting it from chat
      // would show blank content
      loadFile(initialFilePath);
    }
  }, [initialFilePath]);

  const loadFile = async (path: string) => {
    try {
      setIsLoading(true);
      setError(null);
      setFilePath(path);
      
      const fileInfo = await api.getFile(path);
      setContent(fileInfo.content);
      setCitations(fileInfo.citations);
      setIsSaved(true);
    } catch (error: any) {
      console.error('Error loading file:', error);
      setError(error.message || 'Failed to load file');
      toast.error(error.message || 'Failed to load file');
    } finally {
      setIsLoading(false);
    }
  };

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    setIsSaved(false);
  };

  const handleSave = () => {
    // Note: File saving would require a backend API endpoint
    // For now, we'll just mark as saved
    toast.info("File saving not yet implemented. Edits are view-only.");
    console.log("Would save file:", filePath, content);
    setIsSaved(true);
  };

  return (
    <div className="flex flex-col h-full relative m-4 rounded-2xl overflow-hidden bg-card shadow-2xl border border-border">
      {/* Header */}
      <div className="border-b border-border p-4 bg-card shadow-sm space-y-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2>Text Editor</h2>
              <p className="text-sm text-muted-foreground">
                {filePath ? filePath : "No file open"}
              </p>
            </div>
          </div>
          {!isSaved && (
            <span className="text-xs text-amber-500 font-medium">Unsaved changes</span>
          )}
        </div>
      </div>

      {/* Editor Area */}
      <div className="flex-1 overflow-hidden">
        {isLoading ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-2">
              <Loader2 className="h-8 w-8 animate-spin text-primary" />
              <p className="text-sm text-muted-foreground">Loading file...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center h-full">
            <div className="flex flex-col items-center gap-2 text-center">
              <AlertCircle className="h-8 w-8 text-destructive" />
              <p className="text-sm text-muted-foreground">{error}</p>
              <p className="text-xs text-muted-foreground">Make sure the daemon is running</p>
            </div>
          </div>
        ) : filePath ? (
          showLineNumbers ? (
            <div className="flex h-full">
              {/* Line Numbers */}
              <div className="bg-muted/30 px-4 py-6 border-r border-border select-none">
                <div className="font-mono text-sm leading-relaxed text-muted-foreground text-right">
                  {content.split('\n').map((_, index) => (
                    <div key={index} className="h-6">
                      {index + 1}
                    </div>
                  ))}
                </div>
              </div>
              {/* Text Area */}
              <textarea
                value={content}
                onChange={handleContentChange}
                className="flex-1 p-6 bg-background text-foreground resize-none focus:outline-none font-mono text-sm leading-relaxed"
                placeholder="Start typing..."
                spellCheck={false}
              />
            </div>
          ) : (
            <textarea
              value={content}
              onChange={handleContentChange}
              className="w-full h-full p-6 bg-background text-foreground resize-none focus:outline-none font-mono text-sm leading-relaxed"
              placeholder="Start typing..."
              spellCheck={false}
            />
          )
        ) : (
          <div className="flex flex-col items-center justify-center h-full text-center p-8">
            <div className="p-4 bg-muted/30 rounded-full mb-4">
              <FolderOpen className="h-12 w-12 text-muted-foreground" />
            </div>
            <h3 className="text-lg font-medium mb-2">No file open</h3>
            <p className="text-muted-foreground max-w-md mb-4">
              Open the Vault sidebar and double-click on any file to view its content
            </p>
            {Object.keys(citations).length > 0 && (
              <div className="mt-4 p-4 bg-muted/30 rounded-lg max-w-md">
                <h4 className="text-sm font-medium mb-2">Citations</h4>
                <div className="text-xs text-muted-foreground space-y-1">
                  {citations.platform && <p><strong>Source:</strong> {citations.platform}</p>}
                  {citations.timestamp && <p><strong>Date:</strong> {new Date(citations.timestamp).toLocaleString()}</p>}
                  {citations.url && <p><strong>URL:</strong> <a href={citations.url} className="text-primary hover:underline" target="_blank" rel="noopener noreferrer">{citations.url}</a></p>}
                  {citations.quote && <p><strong>Quote:</strong> {citations.quote}</p>}
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Floating Save Button */}
      {filePath && (
        <Button
          onClick={handleSave}
          disabled={isSaved}
          size="lg"
          className="fixed bottom-6 right-6 shadow-2xl hover:shadow-xl transition-all z-40 rounded-xl"
        >
          <Save className="h-5 w-5 mr-2" />
          Save
        </Button>
      )}
    </div>
  );
}
