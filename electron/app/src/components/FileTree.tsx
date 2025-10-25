import { ScrollArea } from "./ui/scroll-area";
import { FileText, Folder, ChevronRight, ChevronDown, Loader2, AlertCircle } from "lucide-react";
import { useState, useEffect } from "react";
import { api, DirectoryItem } from "../lib/api";

export interface TreeItem {
  id: string;
  name: string;
  type: "file" | "folder";
  children?: TreeItem[];
  path?: string;
  loaded?: boolean;
}

function TreeNode({
  item,
  depth = 0,
  onFileDoubleClick,
  onLoadChildren
}: {
  item: TreeItem;
  depth?: number;
  onFileDoubleClick?: (item: TreeItem) => void;
  onLoadChildren?: (item: TreeItem) => Promise<void>;
}) {
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(false);

  const handleClick = async () => {
    if (item.type === "folder") {
      const willOpen = !isOpen;
      setIsOpen(willOpen);
      
      // Load children if opening and not already loaded
      if (willOpen && !item.loaded && onLoadChildren) {
        setIsLoading(true);
        await onLoadChildren(item);
        setIsLoading(false);
      }
    }
  };

  const handleDoubleClick = () => {
    if (item.type === "file" && onFileDoubleClick) {
      onFileDoubleClick(item);
    }
  };

  return (
    <div>
      <div
        className="flex items-center gap-2 px-2 py-1.5 hover:bg-accent hover:shadow-sm cursor-pointer rounded-sm transition-all duration-150 active:scale-[0.98]"
        style={{ paddingLeft: `${depth * 12 + 8}px` }}
        onClick={handleClick}
        onDoubleClick={handleDoubleClick}
      >
        {item.type === "folder" && (
          isLoading ? (
            <Loader2 className="h-4 w-4 text-muted-foreground animate-spin" />
          ) : isOpen ? (
            <ChevronDown className="h-4 w-4 text-muted-foreground" />
          ) : (
            <ChevronRight className="h-4 w-4 text-muted-foreground" />
          )
        )}
        {item.type === "folder" ? (
          <Folder className="h-4 w-4 text-primary/80" />
        ) : (
          <FileText className="h-4 w-4 text-muted-foreground" />
        )}
        <span className="text-sm text-foreground">{item.name}</span>
      </div>
      {item.type === "folder" && isOpen && item.children && (
        <div>
          {item.children.map((child) => (
            <TreeNode 
              key={child.id} 
              item={child} 
              depth={depth + 1} 
              onFileDoubleClick={onFileDoubleClick}
              onLoadChildren={onLoadChildren}
            />
          ))}
        </div>
      )}
    </div>
  );
}

interface FileTreeProps {
  onFileDoubleClick?: (item: TreeItem) => void;
}

export function FileTree({ onFileDoubleClick }: FileTreeProps) {
  const [files, setFiles] = useState<TreeItem[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Load root directory on mount
  useEffect(() => {
    loadDirectory("");
  }, []);

  const loadDirectory = async (path: string) => {
    try {
      setIsLoading(true);
      setError(null);
      const result = await api.listDirectory(path);
      
      // Convert API items to TreeItems
      const items: TreeItem[] = result.items
        .filter(item => item.type === 'directory' || item.name.endsWith('.md'))
        .map((item, index) => ({
          id: path ? `${path}/${item.name}` : item.name,
          name: item.name,
          type: item.type === 'directory' ? 'folder' as const : 'file' as const,
          path: path ? `${path}/${item.name}` : item.name,
          children: item.type === 'directory' ? [] : undefined,
          loaded: false,
        }));
      
      setFiles(items);
    } catch (error: any) {
      console.error('Error loading directory:', error);
      setError(error.message || 'Failed to load vault files');
    } finally {
      setIsLoading(false);
    }
  };

  const handleLoadChildren = async (item: TreeItem) => {
    if (!item.path || item.loaded) return;
    
    try {
      const result = await api.listDirectory(item.path);
      
      // Convert API items to TreeItems
      const children: TreeItem[] = result.items
        .filter(child => child.type === 'directory' || child.name.endsWith('.md'))
        .map(child => ({
          id: `${item.path}/${child.name}`,
          name: child.name,
          type: child.type === 'directory' ? 'folder' as const : 'file' as const,
          path: `${item.path}/${child.name}`,
          children: child.type === 'directory' ? [] : undefined,
          loaded: false,
        }));
      
      // Update the tree with children
      setFiles(prevFiles => updateTreeItem(prevFiles, item.id, { 
        children, 
        loaded: true 
      }));
    } catch (error: any) {
      console.error('Error loading children:', error);
    }
  };

  // Helper to update a tree item by ID
  const updateTreeItem = (items: TreeItem[], id: string, updates: Partial<TreeItem>): TreeItem[] => {
    return items.map(item => {
      if (item.id === id) {
        return { ...item, ...updates };
      }
      if (item.children) {
        return { ...item, children: updateTreeItem(item.children, id, updates) };
      }
      return item;
    });
  };

  if (isLoading) {
    return (
      <div className="flex items-center justify-center h-full p-4">
        <div className="flex flex-col items-center gap-2">
          <Loader2 className="h-6 w-6 animate-spin text-primary" />
          <p className="text-sm text-muted-foreground">Loading vault...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex items-center justify-center h-full p-4">
        <div className="flex flex-col items-center gap-2 text-center">
          <AlertCircle className="h-6 w-6 text-destructive" />
          <p className="text-sm text-muted-foreground">{error}</p>
          <p className="text-xs text-muted-foreground">Make sure the daemon is running</p>
        </div>
      </div>
    );
  }

  if (files.length === 0) {
    return (
      <div className="flex items-center justify-center h-full p-4">
        <p className="text-sm text-muted-foreground text-center">
          No files in vault yet.<br />
          Start ingesting content!
        </p>
      </div>
    );
  }

  return (
    <ScrollArea className="h-full">
      <div className="p-2">
        {files.map((item) => (
          <TreeNode 
            key={item.id} 
            item={item} 
            onFileDoubleClick={onFileDoubleClick}
            onLoadChildren={handleLoadChildren}
          />
        ))}
      </div>
    </ScrollArea>
  );
}
