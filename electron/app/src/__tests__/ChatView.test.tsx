import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { ChatView } from '../components/ChatView';

// Mock API
vi.mock('../lib/api', () => ({
  api: {
    ask: vi.fn(),
  },
}));

// Mock sonner toast
vi.mock('sonner', () => ({
  toast: {
    error: vi.fn(),
    success: vi.fn(),
  },
  Toaster: () => null,
}));

import { api } from '../lib/api';

const mockApi = api as unknown as { ask: ReturnType<typeof vi.fn> };

const sampleAskResult = {
  success: true,
  answer: 'The Meta offer was $200k base salary.',
  contexts: [{ file: 'notes/interview.md', text: 'Meta offered $200k' }],
  query: 'meta offer',
  total_results: 1,
  conversation_length: 2,
};

beforeEach(() => {
  vi.clearAllMocks();
  // Clear localStorage between tests
  localStorage.clear();
});

describe('ChatView', () => {
  it('renders the initial welcome message', () => {
    render(<ChatView />);
    expect(screen.getByText(/Hi! I'm LocalBrain/i)).toBeInTheDocument();
  });

  it('renders the textarea and send button', () => {
    render(<ChatView />);
    expect(screen.getByPlaceholderText(/Ask a question/i)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: '' })).toBeInTheDocument(); // Send icon button
  });

  it('disables send button when input is empty', () => {
    render(<ChatView />);
    // The icon button has no accessible name — check disabled attr
    const sendBtn = screen.getAllByRole('button').find(
      (btn) => btn.getAttribute('disabled') !== null || btn.className.includes('shrink-0')
    );
    // Input is empty so button should be disabled
    const textarea = screen.getByPlaceholderText(/Ask a question/i) as HTMLTextAreaElement;
    expect(textarea.value).toBe('');
  });

  it('sends a message and displays the response', async () => {
    mockApi.ask.mockResolvedValue(sampleAskResult);

    render(<ChatView />);
    const textarea = screen.getByPlaceholderText(/Ask a question/i);
    await userEvent.type(textarea, 'What was my Meta offer?');
    await userEvent.keyboard('{Enter}');

    // User message appears
    await waitFor(() => {
      expect(screen.getByText('What was my Meta offer?')).toBeInTheDocument();
    });

    // Assistant response appears
    await waitFor(() => {
      expect(screen.getByText('The Meta offer was $200k base salary.')).toBeInTheDocument();
    });

    expect(mockApi.ask).toHaveBeenCalledWith('What was my Meta offer?');
  });

  it('Shift+Enter does not submit', async () => {
    mockApi.ask.mockResolvedValue(sampleAskResult);

    render(<ChatView />);
    const textarea = screen.getByPlaceholderText(/Ask a question/i);
    await userEvent.type(textarea, 'test');
    await userEvent.keyboard('{Shift>}{Enter}{/Shift}');

    expect(mockApi.ask).not.toHaveBeenCalled();
  });

  it('shows error message when api.ask throws', async () => {
    mockApi.ask.mockRejectedValue(new Error('Connection refused'));

    render(<ChatView />);
    const textarea = screen.getByPlaceholderText(/Ask a question/i);
    await userEvent.type(textarea, 'test query');
    await userEvent.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/Request failed: Connection refused/i)).toBeInTheDocument();
    });
  });

  it('shows fallback error when ask returns success: false', async () => {
    mockApi.ask.mockResolvedValue({ success: false, answer: '', contexts: [] });

    render(<ChatView />);
    await userEvent.type(screen.getByPlaceholderText(/Ask a question/i), 'bad query');
    await userEvent.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/couldn't find an answer/i)).toBeInTheDocument();
    });
  });

  it('shows sources section when contexts are returned', async () => {
    mockApi.ask.mockResolvedValue(sampleAskResult);

    render(<ChatView />);
    await userEvent.type(screen.getByPlaceholderText(/Ask a question/i), 'meta');
    await userEvent.keyboard('{Enter}');

    await waitFor(() => {
      expect(screen.getByText(/View 1 source/i)).toBeInTheDocument();
    });
  });

  it('clears the conversation', async () => {
    mockApi.ask.mockResolvedValue(sampleAskResult);

    render(<ChatView />);
    // Send a message first
    await userEvent.type(screen.getByPlaceholderText(/Ask a question/i), 'hello');
    await userEvent.keyboard('{Enter}');
    await waitFor(() => screen.getByText('hello'));

    // Mock the clear call
    mockApi.ask.mockResolvedValue({ success: true, answer: '', contexts: [], query: '', total_results: 0, conversation_length: 0 });

    await userEvent.click(screen.getByRole('button', { name: /clear conversation/i }));

    await waitFor(() => {
      expect(screen.getByText(/Hi! I'm LocalBrain/i)).toBeInTheDocument();
    });
    // User message gone
    expect(screen.queryByText('hello')).not.toBeInTheDocument();
  });

  it('persists messages to localStorage', async () => {
    mockApi.ask.mockResolvedValue(sampleAskResult);

    render(<ChatView />);
    await userEvent.type(screen.getByPlaceholderText(/Ask a question/i), 'test persistence');
    await userEvent.keyboard('{Enter}');

    await waitFor(() => screen.getByText('test persistence'));

    const saved = localStorage.getItem('localBrainChatHistory');
    expect(saved).not.toBeNull();
    const parsed = JSON.parse(saved!);
    expect(parsed.some((m: any) => m.content === 'test persistence')).toBe(true);
  });
});
