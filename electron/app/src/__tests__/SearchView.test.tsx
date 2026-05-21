import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { SearchView } from '../components/SearchView';

// Mock the API module
vi.mock('../lib/api', () => ({
  api: {
    search: vi.fn(),
  },
}));

import { api } from '../lib/api';

const mockApi = api as unknown as { search: ReturnType<typeof vi.fn> };

const sampleContexts = [
  { file: 'notes/interview.md', text: 'Meta offered $200k base salary', citations: [] },
  { file: 'notes/jobs.md', text: 'Google offer was $180k', citations: [] },
];

beforeEach(() => {
  vi.clearAllMocks();
});

describe('SearchView', () => {
  it('renders search input and button', () => {
    render(<SearchView />);
    expect(screen.getByPlaceholderText(/Search for anything/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /search/i })).toBeInTheDocument();
  });

  it('shows empty state before any search', () => {
    render(<SearchView />);
    expect(screen.getByText(/Start searching your vault/i)).toBeInTheDocument();
  });

  it('disables button when query is empty', () => {
    render(<SearchView />);
    expect(screen.getByRole('button', { name: /search/i })).toBeDisabled();
  });

  it('enables button when query has text', async () => {
    render(<SearchView />);
    await userEvent.type(screen.getByPlaceholderText(/Search for anything/i), 'interview');
    expect(screen.getByRole('button', { name: /search/i })).not.toBeDisabled();
  });

  it('calls api.search with the query on button click', async () => {
    mockApi.search.mockResolvedValue({ success: true, contexts: sampleContexts });

    render(<SearchView />);
    await userEvent.type(screen.getByPlaceholderText(/Search for anything/i), 'Meta offer');
    await userEvent.click(screen.getByRole('button', { name: /search/i }));

    expect(mockApi.search).toHaveBeenCalledWith('Meta offer');
  });

  it('calls api.search when Enter key is pressed', async () => {
    mockApi.search.mockResolvedValue({ success: true, contexts: sampleContexts });

    render(<SearchView />);
    const input = screen.getByPlaceholderText(/Search for anything/i);
    await userEvent.type(input, 'Google offer{Enter}');

    expect(mockApi.search).toHaveBeenCalledWith('Google offer');
  });

  it('renders search results after successful search', async () => {
    mockApi.search.mockResolvedValue({ success: true, contexts: sampleContexts });

    render(<SearchView />);
    await userEvent.type(screen.getByPlaceholderText(/Search for anything/i), 'offer');
    await userEvent.click(screen.getByRole('button', { name: /search/i }));

    await waitFor(() => {
      expect(screen.getByText('notes/interview.md')).toBeInTheDocument();
      expect(screen.getByText(/Meta offered \$200k base salary/)).toBeInTheDocument();
      expect(screen.getByText('notes/jobs.md')).toBeInTheDocument();
    });
  });

  it('shows no results state when search returns empty', async () => {
    mockApi.search.mockResolvedValue({ success: true, contexts: [] });

    render(<SearchView />);
    await userEvent.type(screen.getByPlaceholderText(/Search for anything/i), 'xyz');
    await userEvent.click(screen.getByRole('button', { name: /search/i }));

    await waitFor(() => {
      expect(screen.getByText(/No results found/i)).toBeInTheDocument();
    });
  });

  it('shows error when api.search fails', async () => {
    mockApi.search.mockRejectedValue(new Error('Daemon not running'));

    render(<SearchView />);
    await userEvent.type(screen.getByPlaceholderText(/Search for anything/i), 'test');
    await userEvent.click(screen.getByRole('button', { name: /search/i }));

    await waitFor(() => {
      expect(screen.getByText(/Daemon not running/i)).toBeInTheDocument();
    });
  });

  it('shows error when api returns success: false', async () => {
    mockApi.search.mockResolvedValue({ success: false, contexts: [] });

    render(<SearchView />);
    await userEvent.type(screen.getByPlaceholderText(/Search for anything/i), 'test');
    await userEvent.click(screen.getByRole('button', { name: /search/i }));

    await waitFor(() => {
      expect(screen.getByText(/Search failed/i)).toBeInTheDocument();
    });
  });

  it('shows loading state during search', async () => {
    let resolveSearch: (v: any) => void;
    mockApi.search.mockReturnValue(new Promise((r) => (resolveSearch = r)));

    render(<SearchView />);
    await userEvent.type(screen.getByPlaceholderText(/Search for anything/i), 'test');
    await userEvent.click(screen.getByRole('button', { name: /search/i }));

    expect(screen.getByText(/Searching\.\.\./i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /searching/i })).toBeDisabled();

    resolveSearch!({ success: true, contexts: [] });
    await waitFor(() => expect(screen.queryByText(/Searching\.\.\./i)).not.toBeInTheDocument());
  });
});
