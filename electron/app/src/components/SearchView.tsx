import { Input } from "./ui/input";
import { ScrollArea } from "./ui/scroll-area";
import { Search, FileText, Calendar } from "lucide-react";

const searchResults = [
  { title: "Context Engine Overview", snippet: "A comprehensive guide to building local context engines...", date: "Oct 24, 2025" },
  { title: "Data Processing Pipeline", snippet: "Implementation details for processing context data...", date: "Oct 23, 2025" },
  { title: "API Integration", snippet: "How to integrate external APIs with the context engine...", date: "Oct 22, 2025" },
  { title: "Machine Learning Models", snippet: "Using ML models for context understanding...", date: "Oct 21, 2025" },
  { title: "Performance Optimization", snippet: "Tips for optimizing context engine performance...", date: "Oct 20, 2025" },
];

export function SearchView() {
  return (
    <div className="flex flex-col h-full">
      <div className="border-b border-border p-4 bg-card shadow-sm space-y-3">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
            <Search className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2>Search & Discover</h2>
            <p className="text-sm text-muted-foreground">Find notes and documents across your vault</p>
          </div>
        </div>
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
          <Input
            placeholder="Search in all notes..."
            className="pl-10 shadow-sm"
          />
        </div>
      </div>
      <ScrollArea className="flex-1">
        <div className="p-4 space-y-4">
          {searchResults.map((result, index) => (
            <div
              key={index}
              className="p-4 border border-border rounded-lg hover:bg-accent/50 hover:shadow-md cursor-pointer transition-all duration-200 shadow-sm bg-card"
            >
              <div className="flex items-start gap-3">
                <div className="p-2 rounded-md bg-primary/10 shadow-sm">
                  <FileText className="h-4 w-4 text-primary" />
                </div>
                <div className="flex-1">
                  <h3 className="mb-1">{result.title}</h3>
                  <p className="text-muted-foreground mb-2">{result.snippet}</p>
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <Calendar className="h-3 w-3" />
                    <span className="text-sm">{result.date}</span>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>
      </ScrollArea>
    </div>
  );
}
