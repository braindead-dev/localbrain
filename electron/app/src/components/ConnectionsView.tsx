'use client';

import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
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

// Connectors to hide — stubs/unimplemented or merged into another entry
const HIDDEN_CONNECTORS = new Set(['browser_history', 'drive', 'linkedin', 'outlook_calendar']);

// Pinned connectors shown first, in order
const PINNED_ORDER = ['gmail', 'calendar'];

// Display name overrides (e.g. outlook_mail → "Outlook")
const DISPLAY_NAME_OVERRIDES: Record<string, string> = {
  outlook_mail: 'Outlook',
};

// After connecting these connectors, also silently connect their companion
const COMPANION_CONNECTORS: Record<string, string> = {
  outlook_mail: 'outlook_calendar',
};

// Button label for each connector's sign-in action
const SIGN_IN_LABELS: Record<string, string> = {
  gmail: 'Sign in with Google',
  calendar: 'Sign in with Google',
  github: 'Sign in with GitHub',
  notion: 'Sign in with Notion',
  reddit: 'Sign in with Reddit',
  twitter: 'Connect X',
  outlook_mail: 'Sign in with Microsoft',
};

export function ConnectionsView() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [showFileDialog, setShowFileDialog] = useState(false);
  const [selectedConnector, setSelectedConnector] = useState<Connector | null>(null);

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
        // Filter out stub/unimplemented connectors and get status for each
        const connectorsWithStatus = await Promise.all(
          response.connectors
            .filter((conn: any) => !HIDDEN_CONNECTORS.has(conn.id))
            .map(async (conn: any) => {
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

        setConnectors(connectorsWithStatus);
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
      const connector = typeof connectorIdOrConnector === 'string'
        ? connectors.find(c => c.id === connectorIdOrConnector)
        : connectorIdOrConnector;

      if (!connector) {
        toast.error("Connector not found");
        return;
      }

      if (connector.id === 'imessage') {
        setSelectedConnector(connector);
        setShowFileDialog(true);
        return;
      }

      if (connector.auth_type === 'oauth') {
        const toastId = toast.loading(`Opening sign-in window...`);

        const authResult = await api.connectorAuthStart(connector.id);

        if (authResult.success && authResult.auth_url) {
          toast.dismiss(toastId);

          // Open in the user's real system browser so passkeys, saved passwords,
          // and existing sessions all work. Electron popups block WebAuthn/passkeys.
          (window as any).electron?.openExternal(authResult.auth_url);

          // Poll every 2s for up to 60s for the user to complete sign-in
          let attempts = 0;
          const maxAttempts = 30;
          const pollInterval = setInterval(async () => {
            attempts++;
            try {
              const status = await api.connectorStatus(connector.id);
              if (status.status?.connected) {
                clearInterval(pollInterval);
                const displayName = DISPLAY_NAME_OVERRIDES[connector.id] ?? connector.name;
                toast.success(`${displayName} connected!`);
                await loadConnectors();
                await handleSync(connector.id);

                // Auto-connect companion connector (e.g. outlook_calendar alongside outlook_mail)
                const companion = COMPANION_CONNECTORS[connector.id];
                if (companion) {
                  try {
                    const companionResult = await api.connectorAuthStart(companion);
                    if (companionResult.success && companionResult.auth_url) {
                      (window as any).electron?.openExternal(companionResult.auth_url);
                      setTimeout(async () => {
                        await handleSync(companion);
                        await loadConnectors();
                      }, 5000);
                    }
                  } catch (err) {
                    console.error(`Companion connect failed for ${companion}:`, err);
                  }
                }
              } else if (attempts >= maxAttempts) {
                clearInterval(pollInterval);
              }
            } catch {
              if (attempts >= maxAttempts) clearInterval(pollInterval);
            }
          }, 2000);
        } else {
          toast.error(`Failed to open sign-in for ${connector.name}`, { id: toastId });
        }
      }
    } catch (err) {
      const errorMessage = err instanceof Error ? err.message : "Failed to start connection";
      setError(errorMessage);
      toast.error(errorMessage);
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

  const filteredConnectors = connectors
    .filter(conn =>
      conn.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      conn.description.toLowerCase().includes(searchQuery.toLowerCase())
    )
    .sort((a, b) => {
      const ai = PINNED_ORDER.indexOf(a.id);
      const bi = PINNED_ORDER.indexOf(b.id);
      if (ai !== -1 && bi !== -1) return ai - bi;
      if (ai !== -1) return -1;
      if (bi !== -1) return 1;
      return 0;
    });

  const getIcon = (connectorId: string) => {
    const Icon = iconMap[connectorId] || Plug;
    return <Icon className="h-5 w-5" />;
  };
  return (
    <div className={`h-full flex flex-col bg-background m-4 rounded-2xl border border-border shadow-2xl ${showFileDialog ? 'blur-sm' : ''}`}>
      {/* Header */}
      <div className="border-b border-border px-6 py-5 bg-card shadow-sm space-y-3 flex-shrink-0">
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
      <div className="flex-1 overflow-auto">
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
                        <h3 className="font-medium">{DISPLAY_NAME_OVERRIDES[connector.id] ?? connector.name}</h3>
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
                        {SIGN_IN_LABELS[connector.id] ?? 'Connect'}
                      </Button>
                    )}
                  </div>
                </Card>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* iMessage Access Dialog */}
      <Dialog open={showFileDialog} onOpenChange={setShowFileDialog}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>Connect iMessage</DialogTitle>
            <DialogDescription>
              iMessage reads directly from your Mac's local Messages database — no account login required.
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-2">
            <div className="rounded-lg border border-border bg-muted/30 p-4 space-y-2">
              <p className="text-sm font-medium">Full Disk Access required</p>
              <p className="text-sm text-muted-foreground">
                macOS restricts access to <code className="text-xs bg-muted px-1 py-0.5 rounded">~/Library/Messages/chat.db</code>.
                Grant LocalBrain Full Disk Access in System Settings to allow it to read your messages.
              </p>
            </div>
            <ol className="text-sm text-muted-foreground space-y-1 list-decimal list-inside">
              <li>Open System Settings → Privacy &amp; Security → Full Disk Access</li>
              <li>Click the <strong>+</strong> button and add <strong>LocalBrain</strong> (or Electron in dev)</li>
              <li>Restart LocalBrain, then click Connect below</li>
            </ol>
            <button
              className="text-xs text-primary hover:underline underline-offset-2"
              onClick={() => (window as any).electron?.openExternal('x-apple.systempreferences:com.apple.preference.security?Privacy_AllFiles')}
            >
              Open Full Disk Access settings →
            </button>
          </div>
          <DialogFooter>
            <Button variant="outline" onClick={() => setShowFileDialog(false)}>Cancel</Button>
            <Button onClick={async () => {
              setShowFileDialog(false);
              if (selectedConnector) await handleSync(selectedConnector.id);
            }}>
              Connect
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

    </div>
  );
}
