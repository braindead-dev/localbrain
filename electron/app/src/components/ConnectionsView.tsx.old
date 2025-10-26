import { useState, useRef, useEffect } from "react";
import { Badge } from "./ui/badge";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { ScrollArea } from "./ui/scroll-area";

import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { Label } from "./ui/label";
import { toast } from "sonner";
import { api } from "../lib/api";
import {
  Search,
  Github,
  Chrome,
  Database,
  Cloud,
  Mail,
  MessageSquare,
  Calendar,
  FolderOpen,
  Code2,
  FileText,
  Slack,
  Trello,
  CheckCircle2,
  XCircle,
  Settings,
  Bot,
  Sparkles,
  Zap,
  Figma,
  Brain,
  Wrench,
  Briefcase,
  Radio,
  HardDrive,
  LayoutGrid,
} from "lucide-react";

interface Integration {
  id: string;
  name: string;
  description: string;
  icon: React.ReactNode;
  connected: boolean;
  category: string;
}

const initialIntegrations: Integration[] = [
  {
    id: "chatgpt",
    name: "ChatGPT",
    description: "Integrate OpenAI's ChatGPT for AI assistance",
    icon: <Bot className="h-6 w-6" />,
    connected: false,
    category: "ai",
  },
  {
    id: "claude",
    name: "Claude",
    description: "Connect to Anthropic's Claude AI assistant",
    icon: <Sparkles className="h-6 w-6" />,
    connected: false,
    category: "ai",
  },
  {
    id: "gemini",
    name: "Gemini",
    description: "Access Google's Gemini AI models",
    icon: <Sparkles className="h-6 w-6" />,
    connected: false,
    category: "ai",
  },
  {
    id: "deepseek",
    name: "Deepseek",
    description: "Connect to Deepseek AI models",
    icon: <Zap className="h-6 w-6" />,
    connected: false,
    category: "ai",
  },
  {
    id: "figma",
    name: "Figma",
    description: "Access and analyze Figma designs",
    icon: <Figma className="h-6 w-6" />,
    connected: false,
    category: "ai",
  },
  {
    id: "github",
    name: "GitHub",
    description: "Sync repositories, issues, and pull requests",
    icon: <Github className="h-6 w-6" />,
    connected: false,
    category: "development",
  },
  {
    id: "vscode",
    name: "VS Code",
    description: "Access workspace files and recent projects",
    icon: <Code2 className="h-6 w-6" />,
    connected: false,
    category: "development",
  },
  {
    id: "notion",
    name: "Notion",
    description: "Import notes and databases from Notion",
    icon: <FileText className="h-6 w-6" />,
    connected: false,
    category: "productivity",
  },
  {
    id: "slack",
    name: "Slack",
    description: "Search and reference Slack messages",
    icon: <MessageSquare className="h-6 w-6" />,
    connected: false,
    category: "communication",
  },
  {
    id: "discord",
    name: "Discord",
    description: "Sync and search your Discord DMs",
    icon: <MessageSquare className="h-6 w-6" />,
    connected: false,
    category: "communication",
  },
  {
    id: "gmail",
    name: "Gmail",
    description: "Index and search email content",
    icon: <Mail className="h-6 w-6" />,
    connected: false,
    category: "communication",
  },
  {
    id: "gcal",
    name: "Google Calendar",
    description: "Access calendar events and meeting notes",
    icon: <Calendar className="h-6 w-6" />,
    connected: false,
    category: "productivity",
  },
  {
    id: "gdrive",
    name: "Google Drive",
    description: "Index documents and files from Drive",
    icon: <FolderOpen className="h-6 w-6" />,
    connected: false,
    category: "storage",
  },
  {
    id: "dropbox",
    name: "Dropbox",
    description: "Access and search Dropbox files",
    icon: <Cloud className="h-6 w-6" />,
    connected: false,
    category: "storage",
  },
  {
    id: "postgres",
    name: "PostgreSQL",
    description: "Connect to PostgreSQL databases",
    icon: <Database className="h-6 w-6" />,
    connected: false,
    category: "development",
  },
  {
    id: "chrome",
    name: "Chrome History",
    description: "Search browsing history and bookmarks",
    icon: <Chrome className="h-6 w-6" />,
    connected: false,
    category: "productivity",
  },
  {
    id: "trello",
    name: "Trello",
    description: "Sync boards, cards, and task lists",
    icon: <Trello className="h-6 w-6" />,
    connected: false,
    category: "productivity",
  },
];

interface ConnectionsViewProps {
  highlightedConnection?: string | null;
  onConnectionViewed?: () => void;
  onIntegrationsChange?: (integrations: Array<{id: string, name: string, connected: boolean}>) => void;
}

export function ConnectionsView({ highlightedConnection, onConnectionViewed, onIntegrationsChange }: ConnectionsViewProps = {}) {
  const [searchQuery, setSearchQuery] = useState("");
  const [selectedCategory, setSelectedCategory] = useState("all");
  const [integrations, setIntegrations] = useState(initialIntegrations);
  const [connectDialogOpen, setConnectDialogOpen] = useState(false);
  const [configureDialogOpen, setConfigureDialogOpen] = useState(false);
  const [selectedIntegration, setSelectedIntegration] = useState<Integration | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [isConnecting, setIsConnecting] = useState(false);
  const [isSyncing, setIsSyncing] = useState(false);
  const highlightedRef = useRef<HTMLDivElement>(null);

  // Check Gmail and Discord status on mount
  useEffect(() => {
    checkGmailStatus();
    checkDiscordStatus();
  }, []);

  // Notify parent of integration changes
  useEffect(() => {
    if (onIntegrationsChange) {
      onIntegrationsChange(integrations.map(i => ({ id: i.id, name: i.name, connected: i.connected })));
    }
  }, [integrations, onIntegrationsChange]);

  const checkGmailStatus = async () => {
    try {
      const status = await api.gmailStatus();
      setIntegrations(prev => prev.map(int => 
        int.id === 'gmail' ? { ...int, connected: status.connected } : int
      ));
    } catch (error) {
      console.error('Error checking Gmail status:', error);
    }
  };

  const checkDiscordStatus = async () => {
    try {
      const status = await api.discordStatus();
      setIntegrations(prev => prev.map(int => 
        int.id === 'discord' ? { ...int, connected: status.connected } : int
      ));
    } catch (error) {
      console.error('Error checking Discord status:', error);
    }
  };

  const filteredIntegrations = integrations.filter((integration) => {
    const matchesSearch = integration.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      integration.description.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesCategory = selectedCategory === "all" || integration.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  const categories = [
    { id: "ai", label: "Agent", icon: <Bot className="h-4 w-4" /> },
    { id: "development", label: "Development", icon: <Wrench className="h-4 w-4" /> },
    { id: "productivity", label: "Productivity", icon: <Briefcase className="h-4 w-4" /> },
    { id: "communication", label: "Communication", icon: <Radio className="h-4 w-4" /> },
    { id: "storage", label: "Storage", icon: <HardDrive className="h-4 w-4" /> },
    { id: "all", label: "All", icon: <LayoutGrid className="h-4 w-4" /> },
  ];

  const handleConnect = async (integration: Integration) => {
    // Special handling for Gmail - use OAuth flow
    if (integration.id === 'gmail') {
      try {
        setIsConnecting(true);
        const result = await api.gmailAuthStart();
        // Open OAuth URL in new window
        window.open(result.auth_url, '_blank', 'width=600,height=700');
        
        toast.info('Complete Gmail authentication in the popup window');
        
        // Poll for status change
        const pollInterval = setInterval(async () => {
          const status = await api.gmailStatus();
          if (status.connected) {
            clearInterval(pollInterval);
            setIntegrations(prev => prev.map(int => 
              int.id === 'gmail' ? { ...int, connected: true } : int
            ));
            toast.success(`Successfully connected to Gmail as ${status.email}!`);
            setIsConnecting(false);
          }
        }, 2000);
        
        // Stop polling after 5 minutes
        setTimeout(() => {
          clearInterval(pollInterval);
          setIsConnecting(false);
        }, 300000);
        
      } catch (error: any) {
        console.error('Gmail auth error:', error);
        toast.error(error.message || 'Failed to start Gmail authentication');
        setIsConnecting(false);
      }
    }
    // Special handling for Discord - show token input
    else if (integration.id === 'discord') {
      setSelectedIntegration(integration);
      setApiKey("");
      setConnectDialogOpen(true);
    }
    else {
      // For other integrations, show API key dialog
      setSelectedIntegration(integration);
      setApiKey("");
      setConnectDialogOpen(true);
    }
  };

  const handleConfirmConnect = async () => {
    if (!selectedIntegration) return;

    // Special handling for Discord - save token via API
    if (selectedIntegration.id === 'discord') {
      try {
        setIsConnecting(true);
        await api.discordSaveToken(apiKey);
        
        // Check status to get username
        const status = await api.discordStatus();
        
        setIntegrations(integrations.map(int => 
          int.id === 'discord' 
            ? { ...int, connected: true }
            : int
        ));

        toast.success(`Successfully connected to Discord as ${status.username}!`);
        setConnectDialogOpen(false);
        setApiKey("");
      } catch (error: any) {
        console.error('Discord connection error:', error);
        toast.error(error.message || 'Failed to connect Discord');
      } finally {
        setIsConnecting(false);
      }
    } else {
      // Update the integration status for other integrations
      setIntegrations(integrations.map(int => 
        int.id === selectedIntegration.id 
          ? { ...int, connected: true }
          : int
      ));

      toast.success(`Successfully connected to ${selectedIntegration.name}!`);
      setConnectDialogOpen(false);
      setApiKey("");
    }
  };

  const handleDisconnect = async (integration: Integration) => {
    // Special handling for Gmail
    if (integration.id === 'gmail') {
      try {
        await api.gmailRevoke();
        setIntegrations(integrations.map(int => 
          int.id === integration.id 
            ? { ...int, connected: false }
            : int
        ));
        toast.success(`Disconnected from ${integration.name}`);
      } catch (error: any) {
        console.error('Gmail disconnect error:', error);
        toast.error(error.message || 'Failed to disconnect Gmail');
      }
    }
    // Special handling for Discord
    else if (integration.id === 'discord') {
      try {
        await api.discordRevoke();
        setIntegrations(integrations.map(int => 
          int.id === integration.id 
            ? { ...int, connected: false }
            : int
        ));
        toast.success(`Disconnected from ${integration.name}`);
      } catch (error: any) {
        console.error('Discord disconnect error:', error);
        toast.error(error.message || 'Failed to disconnect Discord');
      }
    }
    else {
      setIntegrations(integrations.map(int => 
        int.id === integration.id 
          ? { ...int, connected: false }
          : int
      ));
      toast.success(`Disconnected from ${integration.name}`);
    }
  };

  const handleConfigure = async (integration: Integration) => {
    // Special handling for Gmail - trigger sync
    if (integration.id === 'gmail') {
      try {
        setIsSyncing(true);
        toast.info('Syncing and ingesting emails from the last 10 minutes...');
        
        const result = await api.gmailSync(10, 10, true); // max 10 emails, last 10 minutes, ingest=true
        
        if (result.success) {
          toast.success(`Synced ${result.count} emails. Ingested: ${result.ingested_count || 0}, Failed: ${result.failed_count || 0}`);
        } else {
          toast.error(result.error || 'Sync failed');
        }
      } catch (error: any) {
        console.error('Gmail sync error:', error);
        toast.error(error.message || 'Failed to sync Gmail');
      } finally {
        setIsSyncing(false);
      }
    }
    // Special handling for Discord - trigger sync
    else if (integration.id === 'discord') {
      try {
        setIsSyncing(true);
        toast.info('Syncing and ingesting Discord DMs from the last 24 hours...');
        
        const result = await api.discordSync(100, 24, true); // max 100 messages, last 24 hours, ingest=true
        
        if (result.success) {
          const count = result.messages_fetched || result.count || 0;
          toast.success(`Synced ${count} messages. Ingested: ${result.ingested_count || 0}, Failed: ${result.failed_count || 0}`);
        } else {
          toast.error(result.error || 'Sync failed');
        }
      } catch (error: any) {
        console.error('Discord sync error:', error);
        toast.error(error.message || 'Failed to sync Discord');
      } finally {
        setIsSyncing(false);
      }
    }
    else {
      setSelectedIntegration(integration);
      setApiKey("");
      setConfigureDialogOpen(true);
    }
  };

  const handleConfirmConfigure = () => {
    if (!selectedIntegration) return;

    toast.success(`Updated configuration for ${selectedIntegration.name}`);
    setConfigureDialogOpen(false);
    setApiKey("");
  };

  // Scroll to and highlight the selected connection
  useEffect(() => {
    if (highlightedConnection && highlightedRef.current) {
      setTimeout(() => {
        highlightedRef.current?.scrollIntoView({ behavior: 'smooth', block: 'center' });
        // Clear the highlight after viewing
        setTimeout(() => {
          onConnectionViewed?.();
        }, 2000);
      }, 300);
    }
  }, [highlightedConnection, onConnectionViewed]);

  return (
    <div className="flex flex-col h-full overflow-hidden m-4 rounded-2xl bg-card shadow-2xl border border-border">
      <div className="border-b border-border p-4 shrink-0 bg-card shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
            <Zap className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2>Integrations</h2>
            <p className="text-sm text-muted-foreground">Connect external apps to enhance your context engine</p>
          </div>
        </div>
      </div>

      <div className="flex-1 min-h-0 overflow-hidden bg-card shadow-sm">
        <ScrollArea className="h-full w-full">
          <div className="p-6 space-y-6">
            <div className="flex items-center justify-between gap-4">
              <div className="inline-flex rounded-lg bg-muted/60 p-1 shadow-inner border border-border/50">
                {categories.map((category, index) => (
                  <Button
                    key={category.id}
                    onClick={() => setSelectedCategory(category.id)}
                    variant={selectedCategory === category.id ? "default" : "ghost"}
                    size="sm"
                    className={`
                      flex items-center gap-2 px-4 py-2 transition-all rounded-md
                      ${selectedCategory === category.id
                        ? 'shadow-lg'
                        : 'text-muted-foreground hover:text-foreground hover:bg-muted/80'
                      }
                    `}
                  >
                    {category.icon}
                    <span>{category.label}</span>
                  </Button>
                ))}
              </div>
              <div className="relative w-64">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
                <Input
                  placeholder="Search integrations..."
                  className="pl-10 shadow-sm"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                />
              </div>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {filteredIntegrations.map((integration) => (
                <Card
                  key={integration.id}
                  ref={highlightedConnection === integration.id ? highlightedRef : null}
                  className={`hover:border-primary/50 hover:shadow-lg transition-all duration-200 shadow-md flex flex-col ${
                    highlightedConnection === integration.id
                      ? 'ring-2 ring-primary shadow-xl scale-105'
                      : ''
                  }`}
                >
                  <CardHeader className="flex-1">
                    <div className="flex items-start justify-between">
                      <div className="flex items-center gap-3">
                        <div className="p-2 rounded-lg bg-primary/10 shadow-sm ring-1 ring-primary/20">
                          {integration.icon}
                        </div>
                        <div className="flex-1 min-w-0">
                          <CardTitle className="flex items-center gap-2 flex-wrap">
                            <span>{integration.name}</span>
                            {integration.connected && (
                              <Badge variant="default" className="text-xs shadow-sm">
                                <CheckCircle2 className="h-3 w-3 mr-1" />
                                Connected
                              </Badge>
                            )}
                          </CardTitle>
                        </div>
                      </div>
                    </div>
                    <CardDescription className="min-h-[2.5rem]">{integration.description}</CardDescription>
                  </CardHeader>
                  <CardContent className="pt-0">
                    <div className="flex gap-2">
                      {integration.connected ? (
                        <>
                          <Button
                            variant="outline"
                            size="sm"
                            className="flex-1 shadow-sm hover:shadow-md transition-shadow"
                            onClick={() => handleConfigure(integration)}
                            disabled={isSyncing && (integration.id === 'gmail' || integration.id === 'discord')}
                          >
                            <Settings className="h-4 w-4 mr-2" />
                            {(integration.id === 'gmail' || integration.id === 'discord') ? (isSyncing ? 'Syncing...' : 'Sync') : 'Configure'}
                          </Button>
                          <Button
                            variant="outline"
                            size="sm"
                            className="flex-1 shadow-sm hover:shadow-md transition-shadow"
                            onClick={() => handleDisconnect(integration)}
                          >
                            Disconnect
                          </Button>
                        </>
                      ) : (
                        <Button
                          size="sm"
                          className="flex-1 shadow-sm hover:shadow-md transition-shadow"
                          onClick={() => handleConnect(integration)}
                          disabled={isConnecting && (integration.id === 'gmail' || integration.id === 'discord')}
                        >
                          {isConnecting && (integration.id === 'gmail' || integration.id === 'discord') ? 'Connecting...' : 'Connect'}
                        </Button>
                      )}
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>

            {filteredIntegrations.length === 0 && (
              <div className="text-center py-12">
                <p className="text-muted-foreground">No integrations found</p>
              </div>
            )}
          </div>
        </ScrollArea>
      </div>

      <Dialog open={connectDialogOpen} onOpenChange={setConnectDialogOpen}>
        <DialogContent className="shadow-xl">
          <DialogHeader>
            <DialogTitle>Connect to {selectedIntegration?.name}</DialogTitle>
            <DialogDescription>
              {selectedIntegration?.id === 'discord' 
                ? 'Enter your Discord user token to sync your personal DMs'
                : `Enter your API key or credentials to connect to ${selectedIntegration?.name}`
              }
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="apiKey">
                {selectedIntegration?.id === 'discord' ? 'Discord User Token' : 'API Key / Access Token'}
              </Label>
              <Input
                id="apiKey"
                type="password"
                placeholder={selectedIntegration?.id === 'discord' ? 'Paste your Discord token...' : 'Enter your API key...'}
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="shadow-sm"
              />
              {selectedIntegration?.id === 'discord' ? (
                <div className="space-y-2">
                  <p className="text-xs text-muted-foreground font-medium">How to get your Discord token (choose easiest method):</p>
                  
                  <div className="bg-green-50 dark:bg-green-950 border border-green-200 dark:border-green-800 rounded p-3">
                    <p className="text-xs text-green-800 dark:text-green-200 font-bold mb-2">✅ EASIEST: Network Tab Method</p>
                    <ol className="text-xs text-green-700 dark:text-green-300 space-y-1.5 ml-4 list-decimal">
                      <li>Open discord.com in browser and login</li>
                      <li>Press <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">F12</kbd> → <strong>Network</strong> tab</li>
                      <li>Reload page (<kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">Ctrl+R</kbd>)</li>
                      <li>In filter, type: <code className="bg-white dark:bg-gray-800 px-1 rounded">library</code></li>
                      <li>Click the <strong>library</strong> request</li>
                      <li>Click <strong>Headers</strong> tab → scroll to <strong>Request Headers</strong></li>
                      <li>Find <code className="bg-white dark:bg-gray-800 px-1 rounded">authorization:</code> - copy the long string after it</li>
                    </ol>
                  </div>

                  <div className="bg-blue-50 dark:bg-blue-950 border border-blue-200 dark:border-blue-800 rounded p-3">
                    <p className="text-xs text-blue-800 dark:text-blue-200 font-bold mb-2">🔧 Alternative: Application/Storage Tab</p>
                    <ol className="text-xs text-blue-700 dark:text-blue-300 space-y-1.5 ml-4 list-decimal">
                      <li>Open discord.com and press <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">F12</kbd></li>
                      <li>Go to <strong>Application</strong> tab (Chrome) or <strong>Storage</strong> (Firefox)</li>
                      <li>Expand <strong>Session Storage</strong> → click <strong>https://discord.com</strong></li>
                      <li>Look for a key containing "token" - copy its value (remove quotes)</li>
                    </ol>
                  </div>

                  <div className="bg-purple-50 dark:bg-purple-950 border border-purple-200 dark:border-purple-800 rounded p-3">
                    <p className="text-xs text-purple-800 dark:text-purple-200 font-bold mb-2">🖥️ Desktop App Method</p>
                    <ol className="text-xs text-purple-700 dark:text-purple-300 space-y-1.5 ml-4 list-decimal">
                      <li>Open Discord Desktop App</li>
                      <li>Press <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">Ctrl+Shift+I</kbd> (Windows) or <kbd className="px-1 py-0.5 bg-gray-200 dark:bg-gray-700 rounded">Cmd+Option+I</kbd> (Mac)</li>
                      <li>Go to <strong>Console</strong> tab</li>
                      <li>Type: <code className="bg-white dark:bg-gray-800 px-1 rounded block mt-1">{`Object.values(window.webpackChunkdiscord_app.push([[],{},e=>{m=[];for(let c in e.c)m.push(e.c[c])}])).find(x=>x?.exports?.default?.getToken).exports.default.getToken()`}</code></li>
                    </ol>
                  </div>

                  <p className="text-xs text-red-600 dark:text-red-400 font-bold bg-red-50 dark:bg-red-950 border border-red-200 dark:border-red-800 rounded p-2">
                    ⚠️ WARNING: Self-bots violate Discord TOS. This is for authorized personal use only.
                  </p>
                  <p className="text-xs text-muted-foreground">Token stored locally only - never sent to external servers.</p>
                </div>
              ) : (
                <p className="text-xs text-muted-foreground">
                  Your API key will be stored locally and never sent to external servers.
                </p>
              )}
            </div>
          </div>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setConnectDialogOpen(false)}
              className="shadow-sm hover:shadow-md transition-shadow"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleConfirmConnect}
              className="shadow-sm hover:shadow-md transition-shadow"
              disabled={!apiKey.trim() || isConnecting}
            >
              {isConnecting ? 'Connecting...' : 'Connect'}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <Dialog open={configureDialogOpen} onOpenChange={setConfigureDialogOpen}>
        <DialogContent className="shadow-xl">
          <DialogHeader>
            <DialogTitle>Configure {selectedIntegration?.name}</DialogTitle>
            <DialogDescription>
              Update your API key or configuration settings for {selectedIntegration?.name}
            </DialogDescription>
          </DialogHeader>
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="configApiKey">API Key / Access Token</Label>
              <Input
                id="configApiKey"
                type="password"
                placeholder="Enter new API key..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
                className="shadow-sm"
              />
              <p className="text-xs text-muted-foreground">
                Leave blank to keep the existing API key. Your credentials are stored locally.
              </p>
            </div>
          </div>
          <DialogFooter>
            <Button 
              variant="outline" 
              onClick={() => setConfigureDialogOpen(false)}
              className="shadow-sm hover:shadow-md transition-shadow"
            >
              Cancel
            </Button>
            <Button 
              onClick={handleConfirmConfigure}
              className="shadow-sm hover:shadow-md transition-shadow"
            >
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}
