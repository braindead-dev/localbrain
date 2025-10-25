import { useState, useEffect } from "react";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";
import { FileText, Save, FolderOpen } from "lucide-react";

interface EditorViewProps {
  initialFilePath?: string;
  initialContent?: string;
  showLineNumbers?: boolean;
}

export function EditorView({ initialFilePath, initialContent = "", showLineNumbers = false }: EditorViewProps) {
  const [content, setContent] = useState(initialContent);
  const [filePath, setFilePath] = useState<string | null>(initialFilePath || null);
  const [isSaved, setIsSaved] = useState(true);

  // Update content and file path when props change
  useEffect(() => {
    if (initialFilePath !== filePath) {
      setFilePath(initialFilePath || null);
      setContent(initialContent);
      setIsSaved(true);
    }
  }, [initialFilePath, initialContent]);

  const handleContentChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setContent(e.target.value);
    setIsSaved(false);
  };

  const handleSave = () => {
    // TODO: Implement actual file saving via Electron IPC
    console.log("Saving file:", filePath, content);
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
        {filePath ? (
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
            <p className="text-muted-foreground max-w-md">
              Open the Vault sidebar and double-click on any editable file to start editing
            </p>
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
