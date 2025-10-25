/**
 * LocalBrain API Client
 * 
 * Connects to the daemon backend service (localhost:8765)
 */

const API_BASE_URL = 'http://localhost:8765';

export interface SearchContext {
  file: string;
  text: string;  // Backend returns 'text', not 'content'
  content?: string;  // Keep for backwards compatibility
  citations?: any[];
  line_start?: number;
  line_end?: number;
}

export interface SearchResult {
  success: boolean;
  query: string;
  contexts: SearchContext[];
  total_results: number;
  error?: string;
}

export interface FileInfo {
  path: string;
  content: string;
  citations: Record<string, any>;
  size: number;
  last_modified: number;
}

export interface DirectoryItem {
  name: string;
  type: 'file' | 'directory';
  size?: number;
  item_count?: number;
  last_modified: number;
}

export interface DirectoryListing {
  path: string;
  items: DirectoryItem[];
  total: number;
}

export interface Config {
  vault_path: string;
  port: number;
  auto_start: boolean;
}

export interface GmailStatus {
  connected: boolean;
  email?: string;
  error?: string;
}

export interface GmailSyncResult {
  success: boolean;
  count: number;
  emails: string[];
  ingested_count?: number;
  failed_count?: number;
  ingested_subjects?: string[];
  failed_emails?: Array<{ subject: string; error: string }>;
  error?: string;
}

export interface DiscordStatus {
  connected: boolean;
  username?: string;
  user_id?: string;
  lastSync?: string;
  messageCount?: number;
  totalProcessed?: number;
  error?: string;
}

export interface DiscordSyncResult {
  success: boolean;
  messages_fetched?: number;
  count?: number;
  messages: string[];
  ingested_count?: number;
  failed_count?: number;
  ingested_messages?: string[];
  failed_messages?: Array<{ content: string; error: string }>;
  time_window?: string;
  error?: string;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE_URL) {
    this.baseUrl = baseUrl;
  }

  /**
   * Check if daemon is healthy
   */
  async health(): Promise<{ status: string; service: string }> {
    const response = await fetch(`${this.baseUrl}/health`);
    if (!response.ok) throw new Error('Health check failed');
    return response.json();
  }

  /**
   * Get current config
   */
  async getConfig(): Promise<Config> {
    const response = await fetch(`${this.baseUrl}/config`);
    if (!response.ok) throw new Error('Failed to get config');
    return response.json();
  }

  /**
   * Update config
   */
  async updateConfig(updates: Partial<Config>): Promise<{ success: boolean; config: Config; restart_required: boolean; message: string }> {
    const response = await fetch(`${this.baseUrl}/config`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(updates),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to update config');
    }
    return response.json();
  }

  /**
   * Search the vault with natural language query
   */
  async search(query: string): Promise<SearchResult> {
    const response = await fetch(`${this.baseUrl}/protocol/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ q: query }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Search failed');
    }
    return response.json();
  }

  /**
   * Ingest content into vault
   */
  async ingest(text: string, platform?: string, timestamp?: string, url?: string): Promise<{ success: boolean; files_created?: string[]; files_modified?: string[]; message: string }> {
    const response = await fetch(`${this.baseUrl}/protocol/ingest`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text,
        platform: platform || 'Manual',
        timestamp: timestamp || new Date().toISOString(),
        url,
      }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Ingestion failed');
    }
    return response.json();
  }

  /**
   * Get file content from vault
   */
  async getFile(filepath: string): Promise<FileInfo> {
    const response = await fetch(`${this.baseUrl}/file/${encodeURIComponent(filepath)}`);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to get file');
    }
    return response.json();
  }

  /**
   * List directory contents
   */
  async listDirectory(path: string = ''): Promise<DirectoryListing> {
    const url = path ? `${this.baseUrl}/list/${encodeURIComponent(path)}` : `${this.baseUrl}/list`;
    const response = await fetch(url);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to list directory');
    }
    return response.json();
  }

  // ============================================================================
  // Gmail Connector APIs
  // ============================================================================

  /**
   * Start Gmail OAuth flow
   */
  async gmailAuthStart(): Promise<{ auth_url: string; success: boolean }> {
    const response = await fetch(`${this.baseUrl}/connectors/gmail/auth/start`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to start Gmail auth');
    }
    return response.json();
  }

  /**
   * Get Gmail connection status
   */
  async gmailStatus(): Promise<GmailStatus> {
    const response = await fetch(`${this.baseUrl}/connectors/gmail/status`);
    if (!response.ok) {
      const error = await response.json();
      return { connected: false, error: error.error };
    }
    return response.json();
  }

  /**
   * Revoke Gmail access
   */
  async gmailRevoke(): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${this.baseUrl}/connectors/gmail/auth/revoke`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to revoke Gmail');
    }
    return response.json();
  }

  /**
   * Sync Gmail and optionally ingest emails
   */
  async gmailSync(maxResults: number = 100, minutes: number = 10, ingest: boolean = false): Promise<GmailSyncResult> {
    const url = `${this.baseUrl}/connectors/gmail/sync?max_results=${maxResults}&minutes=${minutes}&ingest=${ingest}`;
    const response = await fetch(url, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to sync Gmail');
    }
    return response.json();
  }

  /**
   * Fetch recent emails (without syncing/ingesting)
   */
  async gmailRecentEmails(days: number = 7, maxResults: number = 50): Promise<GmailSyncResult> {
    const url = `${this.baseUrl}/connectors/gmail/emails/recent?days=${days}&max_results=${maxResults}`;
    const response = await fetch(url);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch emails');
    }
    return response.json();
  }

  // ============================================================================
  // Discord Connector APIs
  // ============================================================================

  /**
   * Save Discord user token
   */
  async discordSaveToken(token: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${this.baseUrl}/connectors/discord/auth/save-token`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ token }),
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to save Discord token');
    }
    return response.json();
  }

  /**
   * Get Discord connection status
   */
  async discordStatus(): Promise<DiscordStatus> {
    const response = await fetch(`${this.baseUrl}/connectors/discord/status`);
    if (!response.ok) {
      const error = await response.json();
      return { connected: false, error: error.error };
    }
    return response.json();
  }

  /**
   * Revoke Discord access
   */
  async discordRevoke(): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${this.baseUrl}/connectors/discord/auth/revoke`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to revoke Discord');
    }
    return response.json();
  }

  /**
   * Sync Discord DMs and optionally ingest
   */
  async discordSync(maxMessages: number = 100, hours: number = 24, ingest: boolean = false): Promise<DiscordSyncResult> {
    const url = `${this.baseUrl}/connectors/discord/sync?max_messages=${maxMessages}&hours=${hours}&ingest=${ingest}`;
    const response = await fetch(url, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to sync Discord');
    }
    return response.json();
  }

  /**
   * Fetch recent DMs (without syncing/ingesting)
   */
  async discordRecentDMs(hours?: number, days?: number, maxMessages: number = 50): Promise<DiscordSyncResult> {
    let url = `${this.baseUrl}/connectors/discord/dms/recent?max_messages=${maxMessages}`;
    if (hours !== undefined) {
      url += `&hours=${hours}`;
    } else if (days !== undefined) {
      url += `&days=${days}`;
    }
    const response = await fetch(url);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch DMs');
    }
    return response.json();
  }
}

// Export singleton instance
export const api = new ApiClient();

// Export class for custom instances
export default ApiClient;

