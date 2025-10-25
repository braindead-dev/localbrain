import { ScrollArea } from "./ui/scroll-area";
import { Switch } from "./ui/switch";
import { Label } from "./ui/label";
import { Separator } from "./ui/separator";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "./ui/alert-dialog";
import { useState, useEffect } from "react";
import { Keyboard, Mic, Camera, MapPin, FileText, Monitor, Settings as SettingsIcon, FolderOpen, Folder, Download, Upload, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface SettingsViewProps {
  darkMode: boolean;
  setDarkMode: (value: boolean) => void;
  showLineNumbers: boolean;
  setShowLineNumbers: (value: boolean) => void;
}

export function SettingsView({ darkMode, setDarkMode, showLineNumbers, setShowLineNumbers }: SettingsViewProps) {
  const [permissions, setPermissions] = useState({
    keystrokes: false,
    audio: false,
    camera: false,
    location: false,
    clipboard: true,
    screenCapture: false,
  });

  const [vaultPath, setVaultPath] = useState<string | null>(null);
  const [showPathDialog, setShowPathDialog] = useState(false);
  const [pathInput, setPathInput] = useState("");
  const [isSelecting, setIsSelecting] = useState(false);
  const [showClearCacheDialog, setShowClearCacheDialog] = useState(false);

  useEffect(() => {
    // Load vault path from localStorage
    const savedPath = localStorage.getItem("localBrainVaultPath");
    setVaultPath(savedPath);
  }, []);

  const togglePermission = (key: keyof typeof permissions) => {
    setPermissions(prev => ({ ...prev, [key]: !prev[key] }));
  };

  const handleChangeVault = () => {
    setShowPathDialog(true);
  };

  const handleBrowseFolder = async () => {
    setIsSelecting(true);

    try {
      if ('showDirectoryPicker' in window) {
        const dirHandle = await (window as any).showDirectoryPicker();
        const path = dirHandle.name;
        setPathInput(path);
      } else {
        alert("Your browser doesn't support folder selection. Please paste the folder path manually.");
      }
    } catch (error) {
      console.log("Folder selection cancelled or error:", error);
    } finally {
      setIsSelecting(false);
    }
  };

  const handleConfirmPath = () => {
    if (pathInput && pathInput.trim()) {
      const trimmedPath = pathInput.trim();
      localStorage.setItem("localBrainVaultPath", trimmedPath);
      setVaultPath(trimmedPath);
      setShowPathDialog(false);
      setPathInput("");
    }
  };

  const handleCancelPathDialog = () => {
    setShowPathDialog(false);
    setPathInput("");
  };

  const handleExportData = () => {
    // Create export data object
    const exportData = {
      vaultPath: localStorage.getItem("localBrainVaultPath"),
      darkMode: localStorage.getItem("localBrainDarkMode"),
      exportDate: new Date().toISOString(),
      version: "1.0.0"
    };

    // Convert to JSON and download
    const dataStr = JSON.stringify(exportData, null, 2);
    const dataBlob = new Blob([dataStr], { type: "application/json" });
    const url = URL.createObjectURL(dataBlob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `localbrain-export-${Date.now()}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);

    toast.success("Data exported successfully!");
  };

  const handleImportData = () => {
    const input = document.createElement("input");
    input.type = "file";
    input.accept = "application/json";
    input.onchange = (e: any) => {
      const file = e.target.files[0];
      if (file) {
        const reader = new FileReader();
        reader.onload = (event) => {
          try {
            const importData = JSON.parse(event.target?.result as string);

            // Restore data
            if (importData.vaultPath) {
              localStorage.setItem("localBrainVaultPath", importData.vaultPath);
              setVaultPath(importData.vaultPath);
            }
            if (importData.darkMode !== undefined) {
              localStorage.setItem("localBrainDarkMode", importData.darkMode);
            }

            toast.success("Data imported successfully! Please refresh the page.");
          } catch (error) {
            toast.error("Failed to import data. Invalid file format.");
          }
        };
        reader.readAsText(file);
      }
    };
    input.click();
  };

  const handleClearCache = () => {
    // Clear all localStorage data
    localStorage.clear();

    // Reset state
    setVaultPath(null);

    toast.success("All data cleared! Reloading...");

    // Reload the page after a short delay
    setTimeout(() => {
      window.location.reload();
    }, 1500);
  };

  return (
    <div className="h-full flex flex-col overflow-hidden m-4 rounded-2xl bg-card shadow-2xl border border-border">
      <div className="border-b border-border p-4 bg-card shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
            <SettingsIcon className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2>Preferences</h2>
            <p className="text-sm text-muted-foreground">Configure your context engine preferences</p>
          </div>
        </div>
      </div>
      <ScrollArea className="flex-1 overflow-auto">
        <div className="p-6 space-y-6 max-w-2xl mx-auto">

        {/* Vault Location Section */}
        <div className="space-y-4 p-4 bg-card rounded-lg shadow-md border border-border">
          <h3 className="text-center">Vault Location</h3>
          <div className="space-y-3">
            <div className="p-3 rounded-md bg-background/50 shadow-sm">
              <Label className="text-sm mb-2 block">Current vault location:</Label>
              <code className="block px-4 py-3 bg-muted rounded-md text-sm break-all">
                {vaultPath || "Not configured"}
              </code>
            </div>
            <div className="flex justify-center">
              <Button
                onClick={handleChangeVault}
                variant="outline"
                className="shadow-sm hover:shadow-md transition-shadow"
              >
                <FolderOpen className="h-4 w-4 mr-2" />
                Change Vault Location
              </Button>
            </div>
          </div>
        </div>

        <Separator className="shadow-sm" />

        <div className="space-y-4 p-4 bg-card rounded-lg shadow-md border border-border">
          <h3 className="text-center">Appearance</h3>
          <div className="flex items-center justify-between p-3 rounded-md bg-background/50 hover:bg-accent/30 transition-colors shadow-sm">
            <div className="space-y-0.5">
              <Label>Dark Mode</Label>
              <p className="text-sm text-muted-foreground">Use dark theme</p>
            </div>
            <Switch checked={darkMode} onCheckedChange={setDarkMode} />
          </div>
          <div className="flex items-center justify-between p-3 rounded-md bg-background/50 hover:bg-accent/30 transition-colors shadow-sm">
            <div className="space-y-0.5">
              <Label>Show Line Numbers</Label>
              <p className="text-sm text-muted-foreground">Display line numbers in editor</p>
            </div>
            <Switch
              checked={showLineNumbers}
              onCheckedChange={(checked) => {
                setShowLineNumbers(checked);
                localStorage.setItem('localBrainShowLineNumbers', String(checked));
              }}
            />
          </div>
        </div>

        <Separator className="shadow-sm" />

        <div className="space-y-4 p-4 bg-card rounded-lg shadow-md border border-border">
          <h3 className="text-center">Context Engine</h3>
          <div className="space-y-2 p-3 rounded-md bg-background/50 shadow-sm">
            <Label htmlFor="maxTokens">Max Context Tokens</Label>
            <Input
              id="maxTokens"
              type="number"
              defaultValue="2048"
              className="shadow-sm"
            />
          </div>
          <div className="flex items-center justify-between p-3 rounded-md bg-background/50 hover:bg-accent/30 transition-colors shadow-sm">
            <div className="space-y-0.5">
              <Label>Auto-save</Label>
              <p className="text-sm text-muted-foreground">Automatically save changes</p>
            </div>
            <Switch defaultChecked />
          </div>
          <div className="flex items-center justify-between p-3 rounded-md bg-background/50 hover:bg-accent/30 transition-colors shadow-sm">
            <div className="space-y-0.5">
              <Label>Enable Graph View</Label>
              <p className="text-sm text-muted-foreground">Show connections visualization</p>
            </div>
            <Switch defaultChecked />
          </div>
        </div>

        <Separator className="shadow-sm" />

        <div className="space-y-4 p-4 bg-card rounded-lg shadow-md border border-border">
          <div className="text-center">
            <h3>Permissions</h3>
            <p className="text-sm text-muted-foreground mt-1">
              Control what data the context engine can access
            </p>
          </div>
          
          <div className="space-y-3">
            <div className="flex items-center justify-between p-3 rounded-md bg-background/50 hover:bg-accent/30 transition-colors shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-primary/10 shadow-sm">
                  <Keyboard className="h-4 w-4 text-primary" />
                </div>
                <div className="space-y-0.5">
                  <Label>Keystroke Logging</Label>
                  <p className="text-sm text-muted-foreground">
                    Monitor keyboard input for context
                  </p>
                </div>
              </div>
              <Switch 
                checked={permissions.keystrokes} 
                onCheckedChange={() => togglePermission('keystrokes')} 
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-md bg-background/50 hover:bg-accent/30 transition-colors shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-primary/10 shadow-sm">
                  <Mic className="h-4 w-4 text-primary" />
                </div>
                <div className="space-y-0.5">
                  <Label>Audio Recording</Label>
                  <p className="text-sm text-muted-foreground">
                    Access microphone for voice context
                  </p>
                </div>
              </div>
              <Switch 
                checked={permissions.audio} 
                onCheckedChange={() => togglePermission('audio')} 
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-md bg-background/50 hover:bg-accent/30 transition-colors shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-primary/10 shadow-sm">
                  <Camera className="h-4 w-4 text-primary" />
                </div>
                <div className="space-y-0.5">
                  <Label>Camera Access</Label>
                  <p className="text-sm text-muted-foreground">
                    Use camera for visual context
                  </p>
                </div>
              </div>
              <Switch 
                checked={permissions.camera} 
                onCheckedChange={() => togglePermission('camera')} 
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-md bg-background/50 hover:bg-accent/30 transition-colors shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-primary/10 shadow-sm">
                  <Monitor className="h-4 w-4 text-primary" />
                </div>
                <div className="space-y-0.5">
                  <Label>Screen Capture</Label>
                  <p className="text-sm text-muted-foreground">
                    Capture screenshots for context
                  </p>
                </div>
              </div>
              <Switch 
                checked={permissions.screenCapture} 
                onCheckedChange={() => togglePermission('screenCapture')} 
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-md bg-background/50 hover:bg-accent/30 transition-colors shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-primary/10 shadow-sm">
                  <FileText className="h-4 w-4 text-primary" />
                </div>
                <div className="space-y-0.5">
                  <Label>Clipboard Access</Label>
                  <p className="text-sm text-muted-foreground">
                    Read clipboard content
                  </p>
                </div>
              </div>
              <Switch 
                checked={permissions.clipboard} 
                onCheckedChange={() => togglePermission('clipboard')} 
              />
            </div>

            <div className="flex items-center justify-between p-3 rounded-md bg-background/50 hover:bg-accent/30 transition-colors shadow-sm">
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-md bg-primary/10 shadow-sm">
                  <MapPin className="h-4 w-4 text-primary" />
                </div>
                <div className="space-y-0.5">
                  <Label>Location Services</Label>
                  <p className="text-sm text-muted-foreground">
                    Access device location
                  </p>
                </div>
              </div>
              <Switch 
                checked={permissions.location} 
                onCheckedChange={() => togglePermission('location')} 
              />
            </div>
          </div>
        </div>

        <Separator className="shadow-sm" />

        <div className="space-y-4 p-4 bg-card rounded-lg shadow-md border border-border">
          <h3 className="text-center">Data</h3>
          <div className="flex gap-2 flex-wrap justify-center">
            <Button
              variant="outline"
              className="shadow-sm hover:shadow-md transition-shadow"
              onClick={handleExportData}
            >
              <Download className="h-4 w-4 mr-2" />
              Export Data
            </Button>
            <Button
              variant="outline"
              className="shadow-sm hover:shadow-md transition-shadow"
              onClick={handleImportData}
            >
              <Upload className="h-4 w-4 mr-2" />
              Import Data
            </Button>
            <Button
              variant="destructive"
              className="shadow-sm hover:shadow-md transition-shadow"
              onClick={() => setShowClearCacheDialog(true)}
            >
              <Trash2 className="h-4 w-4 mr-2" />
              Clear Cache
            </Button>
          </div>
        </div>
      </div>
      </ScrollArea>

      {/* Path Selection Dialog */}
      <Dialog open={showPathDialog} onOpenChange={setShowPathDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Choose Vault Location</DialogTitle>
            <DialogDescription>
              Select a folder for your LocalBrain vault or paste the path directly.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="vault-path">Vault Path</Label>
              <div className="flex gap-2">
                <Input
                  id="vault-path"
                  placeholder="/path/to/your/vault or C:\Users\YourName\Documents\LocalBrain"
                  value={pathInput}
                  onChange={(e) => setPathInput(e.target.value)}
                  className="flex-1"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && pathInput.trim()) {
                      handleConfirmPath();
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleBrowseFolder}
                  disabled={isSelecting}
                  title="Browse for folder"
                >
                  <Folder className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                You can paste the full path or click the folder icon to browse.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={handleCancelPathDialog}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirmPath}
              disabled={!pathInput.trim()}
            >
              Confirm Location
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Clear Cache Confirmation Dialog */}
      <AlertDialog open={showClearCacheDialog} onOpenChange={setShowClearCacheDialog}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you absolutely sure?</AlertDialogTitle>
            <AlertDialogDescription className="space-y-2">
              <p>This action cannot be undone. This will permanently delete:</p>
              <ul className="list-disc list-inside space-y-1 text-sm">
                <li>Your vault location settings</li>
                <li>All application preferences</li>
                <li>Theme settings</li>
                <li>All cached data</li>
              </ul>
              <p className="font-semibold text-destructive mt-4">
                The application will reset to its initial state and reload.
              </p>
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              onClick={handleClearCache}
              className="bg-destructive text-destructive-foreground hover:bg-destructive/90"
            >
              Yes, Clear Everything
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  );
}
