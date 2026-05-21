import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ConnectionsView } from '../components/ConnectionsView';

// Mock API
vi.mock('../lib/api', () => ({
  api: {
    listConnectors: vi.fn(),
    connectorStatus: vi.fn(),
    connectorSync: vi.fn(),
    connectorRevoke: vi.fn(),
    connectorAuthStart: vi.fn(),
  },
}));

// Mock sonner
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
    loading: vi.fn(),
  },
  Toaster: () => null,
}));

import { api } from '../lib/api';

const mockApi = api as unknown as {
  listConnectors: ReturnType<typeof vi.fn>;
  connectorStatus: ReturnType<typeof vi.fn>;
  connectorSync: ReturnType<typeof vi.fn>;
  connectorRevoke: ReturnType<typeof vi.fn>;
  connectorAuthStart: ReturnType<typeof vi.fn>;
};

const gmailConnector = {
  id: 'gmail',
  name: 'Gmail',
  description: 'Sync Gmail emails',
  version: '1.0.0',
  auth_type: 'oauth',
  requires_config: true,
  capabilities: ['read'],
};

const notionConnector = {
  id: 'notion',
  name: 'Notion',
  description: 'Sync Notion pages',
  version: '1.0.0',
  auth_type: 'oauth',
  requires_config: true,
  capabilities: ['read'],
};

const connectedStatus = { status: { connected: true, authenticated: true, last_sync: null } };
const disconnectedStatus = { status: { connected: false, authenticated: false, last_sync: null } };

beforeEach(() => {
  vi.clearAllMocks();
  mockApi.listConnectors.mockResolvedValue({ success: true, connectors: [gmailConnector, notionConnector] });
  mockApi.connectorStatus.mockResolvedValue(disconnectedStatus);
});

describe('ConnectionsView', () => {
  it('shows loading spinner on mount', () => {
    // Don't resolve listConnectors yet
    mockApi.listConnectors.mockReturnValue(new Promise(() => {}));

    render(<ConnectionsView />);
    expect(document.querySelector('.animate-spin')).toBeInTheDocument();
  });

  it('renders connector cards after load', async () => {
    render(<ConnectionsView />);

    await waitFor(() => {
      expect(screen.getByText('Gmail')).toBeInTheDocument();
      expect(screen.getByText('Notion')).toBeInTheDocument();
    });
  });

  it('renders the dummy Browser History connector', async () => {
    render(<ConnectionsView />);
    await waitFor(() => {
      expect(screen.getByText('Browser History')).toBeInTheDocument();
    });
  });

  it('shows Connect button for disconnected connectors', async () => {
    render(<ConnectionsView />);

    await waitFor(() => {
      const connectButtons = screen.getAllByRole('button', { name: /connect/i });
      expect(connectButtons.length).toBeGreaterThan(0);
    });
  });

  it('shows Sync Now button for connected connectors', async () => {
    mockApi.connectorStatus.mockResolvedValue(connectedStatus);

    render(<ConnectionsView />);

    await waitFor(() => {
      expect(screen.getAllByRole('button', { name: /sync now/i }).length).toBeGreaterThan(0);
    });
  });

  it('filters connectors by search query', async () => {
    render(<ConnectionsView />);

    await waitFor(() => screen.getByText('Gmail'));

    await userEvent.type(screen.getByPlaceholderText(/Search connectors/i), 'gmail');

    expect(screen.getByText('Gmail')).toBeInTheDocument();
    expect(screen.queryByText('Notion')).not.toBeInTheDocument();
  });

  it('shows no connectors found when search has no match', async () => {
    render(<ConnectionsView />);
    await waitFor(() => screen.getByText('Gmail'));

    await userEvent.type(screen.getByPlaceholderText(/Search connectors/i), 'zzznomatch');

    expect(screen.getByText(/No connectors found/i)).toBeInTheDocument();
  });

  it('calls connectorSync when Sync Now is clicked', async () => {
    mockApi.connectorStatus.mockResolvedValue(connectedStatus);
    mockApi.connectorSync.mockResolvedValue({ success: true, items_fetched: 5, items_ingested: 5 });

    render(<ConnectionsView />);
    await waitFor(() => screen.getAllByRole('button', { name: /sync now/i }));

    await userEvent.click(screen.getAllByRole('button', { name: /sync now/i })[0]);

    await waitFor(() => {
      expect(mockApi.connectorSync).toHaveBeenCalled();
    });
  });

  it('calls connectorRevoke when disconnect button is clicked', async () => {
    mockApi.connectorStatus.mockResolvedValue(connectedStatus);
    mockApi.connectorRevoke.mockResolvedValue({ success: true, message: 'Disconnected' });

    render(<ConnectionsView />);
    await waitFor(() => screen.getAllByRole('button', { name: /sync now/i }));

    // Find the first "Sync Now" button, then find the disconnect button in the same flex container
    const syncBtn = screen.getAllByRole('button', { name: /sync now/i })[0];
    const disconnectBtn = syncBtn.closest('.flex.gap-2')?.querySelector('button:last-child') as HTMLElement;
    expect(disconnectBtn).toBeTruthy();
    await userEvent.click(disconnectBtn!);

    await waitFor(() => {
      expect(mockApi.connectorRevoke).toHaveBeenCalled();
    });
  });

  it('opens OAuth flow when Connect is clicked for oauth connector', async () => {
    const openSpy = vi.spyOn(window, 'open').mockReturnValue(null as any);
    mockApi.connectorAuthStart.mockResolvedValue({ success: true, auth_url: 'https://oauth.example.com' });

    render(<ConnectionsView />);
    await waitFor(() => screen.getAllByRole('button', { name: /connect/i }));

    // Click connect on Gmail (first oauth connector)
    await userEvent.click(screen.getAllByRole('button', { name: /^connect$/i })[0]);

    await waitFor(() => {
      expect(mockApi.connectorAuthStart).toHaveBeenCalledWith('gmail');
      expect(openSpy).toHaveBeenCalledWith('https://oauth.example.com', '_blank', expect.any(String));
    });

    openSpy.mockRestore();
  });

  it('shows error when listConnectors fails', async () => {
    mockApi.listConnectors.mockRejectedValue(new Error('Network error'));

    render(<ConnectionsView />);

    await waitFor(() => {
      expect(screen.getByText(/Network error/i)).toBeInTheDocument();
    });
  });

  it('reload button re-fetches connectors', async () => {
    render(<ConnectionsView />);
    await waitFor(() => screen.getByText('Gmail'));

    expect(mockApi.listConnectors).toHaveBeenCalledTimes(1);

    await userEvent.click(screen.getByRole('button', { name: '' })); // RefreshCw button (no text)

    await waitFor(() => {
      expect(mockApi.listConnectors).toHaveBeenCalledTimes(2);
    });
  });
});
