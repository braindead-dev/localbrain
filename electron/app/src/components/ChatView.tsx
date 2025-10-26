import { useState, useRef, useEffect } from "react";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Send, User, Brain, MessageSquare, Loader2, ChevronDown, ChevronUp, RotateCcw } from "lucide-react";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { TypingMessage } from "./TypingMessage";
import { api, SearchContext } from "../lib/api";
import { toast } from "sonner";
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "./ui/collapsible";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
  contexts?: SearchContext[];  // For assistant messages from ask endpoint
}

const initialMessages: Message[] = [
  {
    id: "1",
    role: "assistant",
    content: "Hi! I'm LocalBrain. I can answer questions about your vault using natural language. Ask me anything about your notes, emails, messages, or any content you've ingested.\n\nI'll remember our conversation context, so you can ask follow-up questions!",
    timestamp: new Date(),
  },
];

interface ChatViewProps {
  autoQuery?: string | null;
  onQueryProcessed?: () => void;
  onFileOpen?: (filePath: string) => void;
}

export function ChatView({ autoQuery, onQueryProcessed, onFileOpen }: ChatViewProps) {
  // Load messages from localStorage on mount (last 25 messages)
  const [messages, setMessages] = useState<Message[]>(() => {
    if (typeof window !== 'undefined') {
      try {
        const saved = localStorage.getItem('localBrainChatHistory');
        if (saved) {
          const parsed = JSON.parse(saved);
          // Convert timestamp strings back to Date objects
          return parsed.map((msg: any) => ({
            ...msg,
            timestamp: new Date(msg.timestamp)
          }));
        }
      } catch (error) {
        console.error('Error loading chat history:', error);
      }
    }
    return initialMessages;
  });
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Save messages to localStorage whenever they change (keep last 25)
  useEffect(() => {
    if (typeof window !== 'undefined' && messages.length > 0) {
      try {
        // Keep only last 25 messages to match backend limit
        const messagesToSave = messages.slice(-25);
        localStorage.setItem('localBrainChatHistory', JSON.stringify(messagesToSave));
      } catch (error) {
        console.error('Error saving chat history:', error);
      }
    }
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Handle auto-query when component receives one
  useEffect(() => {
    if (autoQuery && autoQuery.trim()) {
      setInput(autoQuery);
      // Simulate sending the message
      setTimeout(() => {
        handleSend(autoQuery);
        onQueryProcessed?.();
      }, 100);
    }
  }, [autoQuery]);

  const handleSend = async (queryText?: string) => {
    const messageText = queryText || input;
    if (!messageText.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: messageText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    try {
      // Call the new ask API with conversational answer synthesis
      const result = await api.ask(messageText);

      if (result.success) {
        const assistantMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: result.answer,
          timestamp: new Date(),
          contexts: result.contexts,  // Store contexts for expandable sources section
        };

        setMessages((prev) => [...prev, assistantMessage]);
      } else {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: `I couldn't find an answer to that question.\n\nTry:\n- Using different keywords\n- Being more specific\n- Checking if content has been ingested into your vault`,
          timestamp: new Date(),
        };

        setMessages((prev) => [...prev, errorMessage]);
      }
    } catch (error: any) {
      console.error('Ask error:', error);
      toast.error(error.message || 'Request failed. Is the daemon running?');

      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `❌ Request failed: ${error.message}\n\nMake sure the LocalBrain daemon is running:\n\`\`\`bash\ncd electron/backend\npython src/daemon.py\n\`\`\``,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleClearConversation = async () => {
    try {
      // Clear conversation history on backend
      await api.ask("", true);  // Empty query with clear_history flag

      // Reset messages to initial state
      setMessages(initialMessages);

      // Clear localStorage
      if (typeof window !== 'undefined') {
        localStorage.removeItem('localBrainChatHistory');
      }

      toast.success("Conversation history cleared");
    } catch (error: any) {
      console.error('Clear conversation error:', error);
      toast.error("Failed to clear conversation");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex flex-col h-full m-4 rounded-2xl overflow-hidden shadow-2xl border border-border bg-card">
      {/* Header */}
      <div className="border-b border-border p-4 bg-card shadow-sm flex items-center justify-between">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
            <MessageSquare className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2 className="text-lg font-semibold">Ask LocalBrain</h2>
            <p className="text-sm text-muted-foreground">Conversational access to your vault</p>
          </div>
          <Button
            variant="outline"
            size="sm"
            onClick={handleClearConversation}
            className="gap-2 ml-4"
          >
            <RotateCcw className="h-4 w-4" />
            Clear Conversation
          </Button>
        </div>
        <div>{/* Spacer for right side */}</div>
      </div>

      <div className="flex-1 overflow-hidden">
        <ScrollArea className="h-full p-6">
          <div className="max-w-4xl mx-auto space-y-4">
            {messages.map((message) => (
              <div
                key={message.id}
                className={`flex gap-3 items-start ${
                  message.role === "user" ? "justify-end" : ""
                }`}
              >
                {message.role === "assistant" && (
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback className="bg-primary/10">
                      <Brain className="h-4 w-4 text-primary" />
                    </AvatarFallback>
                  </Avatar>
                )}
                <div
                  className={`rounded-lg p-4 max-w-[80%] shadow-sm ${
                    message.role === "user"
                      ? "bg-primary text-primary-foreground"
                      : "bg-muted"
                  }`}
                >
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>

                  {/* Show expandable sources for assistant messages with contexts */}
                  {message.role === "assistant" && message.contexts && message.contexts.length > 0 && (
                    <Collapsible className="mt-4">
                      <CollapsibleTrigger className="flex items-center gap-2 text-xs text-muted-foreground hover:text-foreground transition-colors">
                        <ChevronDown className="h-3 w-3" />
                        <span>View {message.contexts.length} source{message.contexts.length !== 1 ? 's' : ''}</span>
                      </CollapsibleTrigger>
                      <CollapsibleContent className="mt-2 space-y-2">
                        {message.contexts.map((ctx, idx) => (
                          <div key={idx} className="text-xs border-l-2 border-primary/30 pl-3 py-1">
                            <div
                              className="font-semibold text-primary mb-1 cursor-pointer hover:underline"
                              onDoubleClick={() => {
                                if (onFileOpen) {
                                  onFileOpen(ctx.file);
                                  toast.success(`Opening vault to show ${ctx.file}`);
                                }
                              }}
                              title="Double-click to open vault"
                            >
                              [{idx + 1}] {ctx.file}
                            </div>
                            <div className="text-muted-foreground whitespace-pre-wrap">
                              {(ctx.text || ctx.content || '').substring(0, 200)}
                              {(ctx.text || ctx.content || '').length > 200 ? '...' : ''}
                            </div>
                          </div>
                        ))}
                      </CollapsibleContent>
                    </Collapsible>
                  )}
                </div>
                {message.role === "user" && (
                  <Avatar className="h-8 w-8 shrink-0">
                    <AvatarFallback>
                      <User className="h-4 w-4" />
                    </AvatarFallback>
                  </Avatar>
                )}
              </div>
            ))}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
      </div>

      <div className="border-t border-border p-4 bg-card">
        <div className="max-w-4xl mx-auto flex items-end gap-2">
          <Textarea
            placeholder="Ask a question..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            className="min-h-[60px] max-h-[200px] resize-none shadow-sm"
          />
          <Button
            onClick={() => handleSend()}
            size="icon"
            className="h-[60px] w-[60px] shrink-0 shadow-sm"
            disabled={!input.trim() || isLoading}
          >
            {isLoading ? (
              <Loader2 className="h-5 w-5 animate-spin" />
            ) : (
              <Send className="h-5 w-5" />
            )}
          </Button>
        </div>
      </div>
    </div>
  );
}
