'use client';

import { useState } from "react";
import { Input } from "./ui/input";
import { Button } from "./ui/button";
import { ScrollArea } from "./ui/scroll-area";
import { Search, FileText, Calendar, Loader2 } from "lucide-react";
import { api, SearchContext } from "../lib/api";

export function SearchView() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchContext[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [searched, setSearched] = useState(false);

  const handleSearch = async () => {
    if (!query.trim()) return;
    
    setLoading(true);
    setError(null);
    setSearched(true);
    
    try {
      const response = await api.search(query);
      if (response.success) {
        setResults(response.contexts || []);
      } else {
        setError("Search failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Search failed");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border p-4 bg-card shadow-sm space-y-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
            <Search className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2>Search & Discover</h2>
            <p className="text-sm text-muted-foreground">
              Find notes and documents across your vault using natural language
            </p>
          </div>
        </div>
        <div className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search for anything... (e.g., 'internship applications', 'machine learning notes')"
              className="pl-10 shadow-sm"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyPress={handleKeyPress}
              disabled={loading}
            />
          </div>
          <Button 
            onClick={handleSearch}
            disabled={loading || !query.trim()}
            className="shadow-sm"
          >
            {loading ? (
              <>
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                Searching...
              </>
            ) : (
              "Search"
            )}
          </Button>
        </div>
      </div>

      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {error && (
            <div className="p-4 border border-destructive bg-destructive/10 rounded-lg text-destructive">
              {error}
            </div>
          )}

          {searched && !loading && results.length === 0 && !error && (
            <div className="p-8 text-center text-muted-foreground">
              <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg">No results found</p>
              <p className="text-sm">Try a different search query</p>
            </div>
          )}

          {!searched && !loading && (
            <div className="p-8 text-center text-muted-foreground">
              <Search className="h-12 w-12 mx-auto mb-4 opacity-50" />
              <p className="text-lg">Start searching your vault</p>
              <p className="text-sm">Use natural language to find anything in your notes</p>
            </div>
          )}

          {results.map((result, index) => (
            <div
              key={index}
              className="p-4 border border-border rounded-lg hover:bg-accent/50 hover:shadow-md cursor-pointer transition-all duration-200 shadow-sm bg-card"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-md bg-primary/10 shadow-sm flex-shrink-0">
                  <FileText className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <h3 className="font-medium truncate">{result.file}</h3>
                    {/* timestamp removed as it's not in SearchContext interface */}
                  </div>
                  <p className="text-sm text-muted-foreground whitespace-pre-wrap line-clamp-3">
                    {result.text}
                  </p>
                  {result.citations && result.citations.length > 0 && (
                    <div className="mt-2 flex flex-wrap gap-2">
                      {result.citations.map((citation, i) => (
                        <span 
                          key={i}
                          className="text-xs px-2 py-1 bg-primary/10 text-primary rounded"
                        >
                          [{i + 1}] {citation}
                        </span>
                      ))}
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
