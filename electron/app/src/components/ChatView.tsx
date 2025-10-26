import { useState, useRef, useEffect } from "react";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Send, User, Brain, MessageSquare, Loader2 } from "lucide-react";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { TypingMessage } from "./TypingMessage";
import { api } from "../lib/api";
import { toast } from "sonner";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: Date;
}

const initialMessages: Message[] = [
  {
    id: "1",
    role: "assistant",
    content: "Hi! I'm LocalBrain. I can search through your vault using natural language. Ask me anything about your notes, emails, messages, or any content you've ingested.",
    timestamp: new Date(),
  },
];

interface ChatViewProps {
  autoQuery?: string | null;
  onQueryProcessed?: () => void;
}

export function ChatView({ autoQuery, onQueryProcessed }: ChatViewProps) {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

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
      // Call real search API
      const result = await api.search(messageText);

      let responseContent = '';
      
      if (result.success && result.contexts.length > 0) {
        // Format the contexts into a readable response
        responseContent = `Found ${result.total_results} relevant context${result.total_results === 1 ? '' : 's'} in your vault:\n\n`;
        
        result.contexts.forEach((ctx, idx) => {
          responseContent += `**[${idx + 1}] ${ctx.file}**`;
          if (ctx.line_start) {
            responseContent += ` (lines ${ctx.line_start}-${ctx.line_end})`;
          }
          responseContent += `\n\`\`\`\n${ctx.text || ctx.content}\n\`\`\`\n\n`;
        });
        
        responseContent += `\n---\n\n💡 You can click on any file in the Vault sidebar to view the full content.`;
      } else {
        responseContent = `No results found for "${messageText}".\n\nTry:\n- Using different keywords\n- Being more specific\n- Checking if content has been ingested into your vault`;
      }

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: responseContent,
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error: any) {
      console.error('Search error:', error);
      toast.error(error.message || 'Search failed. Is the daemon running?');
      
      const errorMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `❌ Search failed: ${error.message}\n\nMake sure the LocalBrain daemon is running:\n\`\`\`bash\ncd electron/backend\npython src/daemon.py\n\`\`\``,
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
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
      <div className="border-b border-border p-4 bg-card shadow-sm flex items-center gap-3">
        <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
          <MessageSquare className="h-5 w-5 text-primary" />
        </div>
        <div>
          <h2 className="text-lg font-semibold">Ask LocalBrain</h2>
          <p className="text-sm text-muted-foreground">Query your connected knowledge base</p>
        </div>
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
