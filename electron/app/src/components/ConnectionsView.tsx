'use client';

import { useState, useEffect, useRef } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { 
  Plug, 
  Search, 
  CheckCircle2, 
  XCircle, 
  Loader2,
  Mail,
  MessageSquare,
  Calendar,
  Globe,
  RefreshCw
} from "lucide-react";
import { api } from "../lib/api";
import { toast } from "sonner";

interface Connector {
  id: string;
  name: string;
  description: string;
  version: string;
  auth_type: string;
  requires_config: boolean;
  capabilities: string[];
  connected?: boolean;
  authenticated?: boolean;
  last_sync?: string;
}

const iconMap: Record<string, any> = {
  gmail: Mail,
  discord: MessageSquare,
  imessage: MessageSquare,
  calendar: Calendar,
  browser: Globe,
  browser_history: Globe,
};

export function ConnectionsView() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showConnectDialog, setShowConnectDialog] = useState(false);
  const [showFileDialog, setShowFileDialog] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(null);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Load connectors on mount
  useEffect(() => {
    loadConnectors();
  }, []);

  const loadConnectors = async () => {
    setLoading(true);
    setError(null);
    
    try {
      const response = await api.listConnectors();
      if (response.success) {
        // Get status for each connector
        const connectorsWithStatus = await Promise.all(
          response.connectors.map(async (conn: any) => {
            try {
              const status = await api.connectorStatus(conn.id);
              return {
                ...conn,
                connected: status.status?.connected || false,
                authenticated: status.status?.authenticated || false,
                last_sync: status.status?.last_sync,
              };
            } catch {
              return { ...conn, connected: false, authenticated: false };
            }
          })
        );
        // Add a dummy iMessage connector for demonstration
        const dummyIMessageConnector: Connector = {
          id: "imessage",
          name: "iMessage",
          description: "Connect to iMessage to sync your conversations.",
          version: "1.0.0",
          auth_type: "file",
          requires_config: true,
          capabilities: ["chat"],
          connected: false,
          authenticated: false,
        };

        const dummyBrowserHistoryConnector: Connector = {
          id: "browser_history",
          name: "Browser History",
          description: "Connect to browser history to sync your browsing.",
          version: "1.0.0",
          auth_type: "file",
          requires_config: true,
          capabilities: ["history"],
          connected: false,
          authenticated: false,
        };

        setConnectors([...connectorsWithStatus, dummyIMessageConnector, dummyBrowserHistoryConnector]);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load connectors");
    } finally {
      setLoading(false);
    }
  };

  const handleSync = async (connectorId: string) => {
    setSyncing(connectorId);
    try {
      await api.connectorSync(connectorId, true);
      // Reload to get updated status
      await loadConnectors();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Sync failed");
    } finally {
      setSyncing(null);
    }
  };

  const handleConnect = async (connectorIdOrConnector: string | Connector) => {
    try {
      // Handle both string ID and Connector object for backward compatibility
      const connector = typeof connectorIdOrConnector === 'string' 
        ? connectors.find(c => c.id === connectorIdOrConnector)
        : connectorIdOrConnector;
      
      if (!connector) {
        setError("Connector not found");
        return;
      }

      if (connector.id === 'imessage' || connector.id === 'browser_history') {
        setSelectedConnector(connector);
        setShowFileDialog(true);
      } else if (connector.auth_type === 'oauth') {
        console.log(`🔵 Starting OAuth flow for ${connector.id}...`);
        const authResult = await api.connectorAuthStart(connector.id);
        if (authResult.success && authResult.auth_url) {
          console.log(`🔵 Opening OAuth window for ${connector.id}:`, authResult.auth_url);
          // Open OAuth URL in new window
          window.open(authResult.auth_url, '_blank', 'width=600,height=700,scrollbars=yes,resizable=yes');
          // Reload connectors and auto-sync after OAuth completes
          console.log(`🔵 Setting up auto-sync timer for ${connector.id} (3 seconds)...`);
          setTimeout(async () => {
            console.log(`🔵 Timer fired! Reloading connectors for ${connector.id}...`);
            await loadConnectors();
            // Auto-sync the newly connected connector
            try {
              console.log(`🔵 Checking connection status for ${connector.id}...`);
              const status = await api.connectorStatus(connector.id);
              console.log(`🔵 Status for ${connector.id}:`, status);
              if (status.status?.connected) {
                console.log(`✅ ${connector.id} is connected! Starting auto-sync...`);
                await handleSync(connector.id);
                console.log(`✅ Auto-sync triggered for ${connector.id}`);
              } else {
                console.log(`⚠️ ${connector.id} not connected yet. Status:`, status);
              }
            } catch (err) {
              console.error(`❌ Auto-sync failed for ${connector.id}:`, err);
            }
          }, 3000); // Wait 3 seconds for OAuth to complete
        }
      } else {
        // For other connectors, show dialog
        setSelectedConnector(connector);
        setShowConnectDialog(true);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to start connection");
    }
  };

  const handleDisconnect = async (connectorId: string) => {
    try {
      await api.connectorRevoke(connectorId);
      await loadConnectors();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect");
    }
  };

  const handleFileSelect = async () => {
    if (!selectedFile) {
      toast.error("Please select a file first.");
      return;
    }

    const toastId = toast.loading("Ingesting browser history...");
    setShowFileDialog(false); // Close the dialog immediately

    try {
      const fileContent = await selectedFile.text();
      const items = JSON.parse(fileContent);

      const result = await api.browserIngest(items);

      if (result.success) {
        toast.success(`Successfully ingested ${result.items_ingested} items.`, { id: toastId });
      } else {
        toast.error(`Ingestion failed. Errors: ${result.errors.join(', ')}`, { id: toastId });
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : "An unknown error occurred.", { id: toastId });
    } finally {
      setSelectedFile(null);
    }
  };

  const handleConfirmConnect = async () => {
    if (!selectedConnector) return;

    try {
      // Check if this is an OAuth connector (Gmail, Calendar, etc.)
      if (selectedConnector.auth_type === 'oauth') {
        // Start OAuth flow
        const authResult = await api.connectorAuthStart(selectedConnector.id);
        if (authResult.success && authResult.auth_url) {
          // Open OAuth URL in browser
          window.open(authResult.auth_url, '_blank', 'width=600,height=700');
          toast.success('OAuth window opened! Complete authorization in the browser.');
          setShowConnectDialog(false);
          
          // Poll for connection status
          setTimeout(async () => {
            await loadConnectors();
          }, 3000);
        }
      } 
    } catch (err) {
      console.error("Connection error:", err);
      toast.error(err instanceof Error ? err.message : "Connection failed");
    }
  };

  const filteredConnectors = connectors.filter(conn =>
    conn.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    conn.description.toLowerCase().includes(searchQuery.toLowerCase())
  );

  const getIcon = (connectorId: string) => {
    const Icon = iconMap[connectorId] || Plug;
    return <Icon className="h-5 w-5" />;
  };
  return (
    <div className={`h-full flex flex-col bg-background m-4 rounded-2xl overflow-hidden border border-border shadow-2xl ${showFileDialog ? 'blur-sm' : ''}`}>
      {/* Header */}
      <div className="border-b border-border px-6 py-5 bg-card shadow-sm space-y-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
            <Plug className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2>Connectors</h2>
            <p className="text-sm text-muted-foreground">
              Manage data source integrations
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2 pl-14">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search connectors..."
              className="pl-10 shadow-sm"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
            />
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={loadConnectors}
            disabled={loading}
            className="ml-2"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
          </Button>
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="px-6 py-8 space-y-4">
          {error && (
            <div className="p-4 border border-destructive bg-destructive/10 rounded-lg text-destructive">
              {error}
            </div>
          )}

          {loading && !connectors.length ? (
            <div className="flex items-center justify-center p-12">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
            </div>
          ) : filteredConnectors.length === 0 ? (
            <div className="p-12 text-center text-muted-foreground">
              <Plug className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg">No connectors found</p>
              <p className="text-sm">
                {searchQuery ? "Try a different search" : "No connectors available"}
              </p>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredConnectors.map((connector) => (
                <Card key={connector.id} className="p-4 flex flex-col">
                  <div className="flex items-start gap-4">
                    {/* Icon */}
                    <div className="p-3 bg-primary/10 rounded-lg flex-shrink-0">
                      {getIcon(connector.id)}
                    </div>

                    {/* Info */}
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1">
                        <h3 className="font-medium">{connector.name}</h3>
                        {connector.connected ? (
                          <CheckCircle2 className="h-4 w-4 text-green-500" />
                        ) : (
                          <XCircle className="h-4 w-4 text-muted-foreground" />
                        )}
                      </div>
                      <Badge variant="outline" className="text-xs mb-2">
                          v{connector.version}
                      </Badge>
                      <p className="text-sm text-muted-foreground mb-3">
                        {connector.description}
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex flex-wrap gap-2 mb-3">
                    <Badge variant="secondary" className="text-xs">
                      {connector.auth_type}
                    </Badge>
                    {connector.capabilities.map((cap) => (
                      <Badge key={cap} variant="outline" className="text-xs">
                        {cap}
                      </Badge>
                    ))}
                  </div>

                  {/* Last Sync */}
                  {connector.last_sync && (
                    <p className="text-xs text-muted-foreground mb-3">
                      Last synced: {new Date(connector.last_sync).toLocaleString()}
                    </p>
                  )}

                  {/* Spacer to push actions to the bottom */}
                  <div className="flex-grow" />

                  {/* Actions */}
                  <div className="flex gap-2 mt-auto">
                    {connector.connected && connector.authenticated ? (
                      <>
                        <Button
                          size="sm"
                          onClick={() => handleSync(connector.id)}
                          disabled={syncing === connector.id}
                          className="w-full"
                        >
                          {syncing === connector.id ? (
                            <>
                              <Loader2 className="h-3 w-3 mr-2 animate-spin" />
                              Syncing...
                            </>
                          ) : (
                            "Sync Now"
                          )}
                        </Button>
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => handleDisconnect(connector.id)}
                        >
                          <XCircle className="h-4 w-4" />
                        </Button>
                      </>
                    ) : (
                      <Button 
                        size="sm"
                        onClick={() => handleConnect(connector)}
                        className="w-full"
                      >
                        Connect
                      </Button>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* File Dialog */}
      <Dialog open={showFileDialog} onOpenChange={setShowFileDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Select File</DialogTitle>
            <DialogDescription>
              Please select the JSON file for {selectedConnector?.name}.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <Input
              ref={fileInputRef}
              type="file"
              accept=".json"
              className="hidden"
              onChange={(e) => setSelectedFile(e.target.files ? e.target.files[0] : null)}
            />
            <Button variant="outline" onClick={() => fileInputRef.current?.click()}>
              Choose File
            </Button>
            {selectedFile && <p className="text-sm text-muted-foreground">Selected file: {selectedFile.name}</p>}
          </div>
          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowFileDialog(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleFileSelect} disabled={!selectedFile}>
              Select
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Connect Dialog */}
      <Dialog open={showConnectDialog} onOpenChange={setShowConnectDialog}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Connect to {selectedConnector?.name}</DialogTitle>
            <DialogDescription>
              {selectedConnector?.auth_type === 'oauth' ? (
                <>
                  Click Connect to authorize {selectedConnector?.name} access via OAuth
                </>
              ) : (
                <>Configure connection settings for {selectedConnector?.name}</>
              )}
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            {selectedConnector?.auth_type === 'oauth' && (
              <div className="space-y-2">
                <p className="text-sm text-muted-foreground">
                  You will be redirected to {selectedConnector?.name} to authorize access.
                  After authorization, you'll be redirected back to LocalBrain.
                </p>
              </div>
            )}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setShowConnectDialog(false)}
            >
              Cancel
            </Button>
            <Button onClick={handleConfirmConnect}>
              Connect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
