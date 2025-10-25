import { useState, useEffect } from "react";
import { ScrollArea } from "./ui/scroll-area";
import { FileText, Save, FolderOpen } from "lucide-react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";

interface TextEditorViewProps {
  selectedFile: { id: string; name: string; content: string } | null;
  onOpenVault: () => void;
}

export function TextEditorView({ selectedFile, onOpenVault }: TextEditorViewProps) {
  const [content, setContent] = useState("");
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);

  useEffect(() => {
    if (selectedFile) {
      setContent(selectedFile.content);
      setHasUnsavedChanges(false);
    }
  }, [selectedFile]);

  const handleContentChange = (value: string) => {
    setContent(value);
    setHasUnsavedChanges(true);
  };

  const handleSave = () => {
    // TODO: Implement actual file saving logic
    console.log("Saving file:", selectedFile?.name, content);
    setHasUnsavedChanges(false);
  };

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border p-4 bg-card shadow-sm">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
              <FileText className="h-5 w-5 text-primary" />
            </div>
            <div>
              <h2>{selectedFile ? selectedFile.name : "Text Editor"}</h2>
              <p className="text-sm text-muted-foreground">
                {selectedFile ? "Edit your document" : "Open a file from the vault to start editing"}
              </p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {!selectedFile && (
              <Button
                onClick={onOpenVault}
                variant="outline"
                size="sm"
                className="shadow-sm"
              >
                <FolderOpen className="h-4 w-4 mr-2" />
                Open Vault
              </Button>
            )}
            {selectedFile && (
              <Button
                onClick={handleSave}
                disabled={!hasUnsavedChanges}
                size="sm"
                className="shadow-sm"
              >
                <Save className="h-4 w-4 mr-2" />
                {hasUnsavedChanges ? "Save" : "Saved"}
              </Button>
            )}
          </div>
        </div>
      </div>
      <div className="flex-1 overflow-hidden p-4">
        {selectedFile ? (
          <Textarea
            value={content}
            onChange={(e) => handleContentChange(e.target.value)}
            className="w-full h-full resize-none font-mono text-sm p-4 shadow-sm"
            placeholder="Start typing..."
          />
        ) : (
          <div className="flex items-center justify-center h-full">
            <div className="text-center space-y-4">
              <div className="p-4 bg-muted/50 rounded-full inline-block">
                <FileText className="h-12 w-12 text-muted-foreground" />
              </div>
              <div>
                <h3 className="text-lg font-medium mb-2">No file selected</h3>
                <p className="text-muted-foreground mb-4">
                  Double-click a file in the vault to open it
                </p>
                <Button
                  onClick={onOpenVault}
                  variant="outline"
                  className="shadow-sm"
                >
                  <FolderOpen className="h-4 w-4 mr-2" />
                  Open Vault
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
