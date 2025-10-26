'use client';

import { useState, useEffect } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card } from "./ui/card";
import { Badge } from "./ui/badge";
import { ScrollArea } from "./ui/scroll-area";
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
  calendar: Calendar,
  browser: Globe,
};

export function ConnectionsView() {
  const [connectors, setConnectors] = useState<Connector[]>([]);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [error, setError] = useState<string | null>(null);

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

  const handleDisconnect = async (connectorId: string) => {
    try {
      await api.connectorRevoke(connectorId);
      await loadConnectors();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to disconnect");
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
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="border-b border-border p-4 bg-card shadow-sm space-y-3">
        <div className="flex items-center justify-between">
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
          <Button
            variant="outline"
            size="sm"
            onClick={loadConnectors}
            disabled={loading}
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <RefreshCw className="h-4 w-4" />
            )}
          </Button>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search connectors..."
            className="pl-10 shadow-sm"
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>
      </div>

      {/* Content */}
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
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
            filteredConnectors.map((connector) => (
              <Card key={connector.id} className="p-4">
                <div className="flex items-start gap-4">
                  {/* Icon */}
                  <div className="p-3 bg-primary/10 rounded-lg flex-shrink-0">
                    {getIcon(connector.id)}
                  </div>

                  {/* Info */}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-start justify-between gap-4 mb-2">
                      <div>
                        <div className="flex items-center gap-2">
                          <h3 className="font-medium">{connector.name}</h3>
                          {connector.connected ? (
                            <CheckCircle2 className="h-4 w-4 text-green-500" />
                          ) : (
                            <XCircle className="h-4 w-4 text-muted-foreground" />
                          )}
                        </div>
                        <p className="text-sm text-muted-foreground">
                          {connector.description}
                        </p>
                      </div>
                      <Badge variant="outline" className="flex-shrink-0">
                        v{connector.version}
                      </Badge>
                    </div>

                    {/* Metadata */}
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

                    {/* Actions */}
                    <div className="flex gap-2">
                      {connector.connected && connector.authenticated ? (
                        <>
                          <Button
                            size="sm"
                            onClick={() => handleSync(connector.id)}
                            disabled={syncing === connector.id}
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
                            Disconnect
                          </Button>
                        </>
                      ) : (
                        <Button size="sm" disabled>
                          Not Connected
                        </Button>
                      )}
                    </div>
                  </div>
                </div>
              </Card>
            ))
          )}
        </div>
      </ScrollArea>
    </div>
  );
}
