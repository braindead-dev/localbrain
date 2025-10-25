import { useState, useRef, useEffect } from "react";
import { ScrollArea } from "./ui/scroll-area";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Send, User, Brain, MessageSquare } from "lucide-react";
import { Avatar, AvatarFallback } from "./ui/avatar";
import { TypingMessage } from "./TypingMessage";

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
    content: "Hi! I'm LocalBrain, your personal knowledge assistant. I can help you search through all your connected data sources and find the information you need. What would you like to know?",
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

  const handleSend = (queryText?: string) => {
    const messageText = queryText || input;
    if (!messageText.trim()) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: messageText,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");

    // Simulate assistant response
    setTimeout(() => {
      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: `> PROCESSING QUERY: "${messageText}"\n> SCANNING KNOWLEDGE BASE...\n> SEARCHING CONNECTED DATA SOURCES...\n\n[DEMO MODE] Query received and processed. In production, this would search through your GitHub repositories, Gmail inbox, Google Drive files, and other connected integrations to provide relevant context.\n\n> STATUS: COMPLETE\n> RESPONSE_TIME: 1.2s`,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, assistantMessage]);
    }, 1000);
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
            disabled={!input.trim()}
          >
            <Send className="h-5 w-5" />
          </Button>
        </div>
      </div>
    </div>
  );
}
