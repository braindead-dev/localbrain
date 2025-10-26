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

export interface CalendarStatus {
  connected: boolean;
  email?: string;
  calendar_count?: number;
  error?: string;
}

export interface CalendarSyncResult {
  success: boolean;
  count: number;
  events: string[];
  ingested_count?: number;
  failed_count?: number;
  ingested_titles?: string[];
  failed_events?: Array<{ title: string; error: string }>;
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
  // Generic Connector APIs (New Plugin System)
  // ============================================================================

  /**
   * List all available connectors
   */
  async listConnectors(): Promise<{ success: boolean; connectors: Array<any> }> {
    const response = await fetch(`${this.baseUrl}/connectors`);
    if (!response.ok) throw new Error('Failed to list connectors');
    return response.json();
  }

  /**
   * Get connector status
   */
  async connectorStatus(connectorId: string): Promise<any> {
    const response = await fetch(`${this.baseUrl}/connectors/${connectorId}/status`);
    if (!response.ok) throw new Error(`Failed to get ${connectorId} status`);
    return response.json();
  }

  /**
   * Start OAuth flow for connector
   */
  async connectorAuthStart(connectorId: string): Promise<{ auth_url: string; success: boolean }> {
    const response = await fetch(`${this.baseUrl}/connectors/${connectorId}/auth/start`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || `Failed to start ${connectorId} auth`);
    }
    return response.json();
  }

  /**
   * Authenticate connector
   */
  async connectorAuth(connectorId: string, credentials: any): Promise<{ success: boolean; message?: string; error?: string }> {
    const response = await fetch(`${this.baseUrl}/connectors/${connectorId}/auth`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(credentials),
    });
    
    const data = await response.json();
    
    if (!response.ok) {
      throw new Error(data.error || `Failed to authenticate ${connectorId}`);
    }
    
    return data;
  }

  /**
   * Sync connector
   */
  async connectorSync(connectorId: string, autoIngest: boolean = true, limit?: number): Promise<any> {
    let url = `${this.baseUrl}/connectors/${connectorId}/sync?auto_ingest=${autoIngest}`;
    if (limit) url += `&limit=${limit}`;
    const response = await fetch(url, { method: 'POST' });
    if (!response.ok) throw new Error(`Failed to sync ${connectorId}`);
    return response.json();
  }

  /**
   * Revoke connector access
   */
  async connectorRevoke(connectorId: string): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${this.baseUrl}/connectors/${connectorId}/auth/revoke`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error(`Failed to revoke ${connectorId}`);
    return response.json();
  }

  /**
   * Sync all connectors
   */
  async syncAllConnectors(autoIngest: boolean = true): Promise<any> {
    const response = await fetch(`${this.baseUrl}/connectors/sync-all?auto_ingest=${autoIngest}`, {
      method: 'POST',
    });
    if (!response.ok) throw new Error('Failed to sync all connectors');
    return response.json();
  }

  // ============================================================================
  // Gmail Connector APIs (Legacy - use generic connector APIs above)
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
    const data = await response.json();
    // Extract status from nested structure
    return {
      connected: data.status?.connected || false,
      email: data.status?.metadata?.email,
      error: data.status?.last_error
    };
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
  // Google Calendar Connector APIs
  // ============================================================================

  /**
   * Start Google Calendar OAuth flow
   */
  async calendarAuthStart(): Promise<{ auth_url: string; success: boolean }> {
    const response = await fetch(`${this.baseUrl}/connectors/calendar/auth/start`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to start Calendar auth');
    }
    return response.json();
  }

  /**
   * Get Google Calendar connection status
   */
  async calendarStatus(): Promise<CalendarStatus> {
    const response = await fetch(`${this.baseUrl}/connectors/calendar/status`);
    if (!response.ok) {
      const error = await response.json();
      return { connected: false, error: error.error || 'Failed to get status' };
    }
    const data = await response.json();
    // Extract status from nested structure
    return {
      connected: data.status?.connected || false,
      email: data.status?.metadata?.email,
      error: data.status?.last_error
    };
  }

  /**
   * Revoke Google Calendar access
   */
  async calendarRevoke(): Promise<{ success: boolean; message: string }> {
    const response = await fetch(`${this.baseUrl}/connectors/calendar/auth/revoke`, {
      method: 'POST',
    });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to revoke Calendar');
    }
    return response.json();
  }

  /**
   * Sync Google Calendar and optionally ingest events
   */
  async calendarSync(maxResults: number = 100, days: number = 7, ingest: boolean = false): Promise<CalendarSyncResult> {
    const url = `${this.baseUrl}/connectors/calendar/sync?max_results=${maxResults}&days=${days}&ingest=${ingest}`;
    const response = await fetch(url, { method: 'POST' });
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to sync Calendar');
    }
    return response.json();
  }

  /**
   * Fetch upcoming calendar events (without syncing/ingesting)
   */
  async calendarUpcomingEvents(days: number = 14, maxResults: number = 50): Promise<CalendarSyncResult> {
    const url = `${this.baseUrl}/connectors/calendar/events/upcoming?days=${days}&max_results=${maxResults}`;
    const response = await fetch(url);
    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error || 'Failed to fetch events');
    }
    return response.json();
  }

}

// Export singleton instance
export const api = new ApiClient();

// Export class for custom instances
export default ApiClient;

