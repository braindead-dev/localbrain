import { ScrollArea } from "./ui/scroll-area";
import { FileText, Folder, ChevronRight, ChevronDown } from "lucide-react";
import { useState } from "react";

export interface TreeItem {
  id: string;
  name: string;
  type: "file" | "folder";
  children?: TreeItem[];
  path?: string;
}

const mockFiles: TreeItem[] = [
  {
    id: "1",
    name: "Context Engine",
    type: "folder",
    children: [
      { id: "1-1", name: "Overview.md", type: "file", path: "Context Engine/Overview.md" },
      { id: "1-2", name: "Architecture.md", type: "file", path: "Context Engine/Architecture.md" },
      {
        id: "1-3",
        name: "Components",
        type: "folder",
        children: [
          { id: "1-3-1", name: "Parser.md", type: "file", path: "Context Engine/Components/Parser.md" },
          { id: "1-3-2", name: "Indexer.md", type: "file", path: "Context Engine/Components/Indexer.md" },
        ],
      },
    ],
  },
  {
    id: "2",
    name: "Data Sources",
    type: "folder",
    children: [
      { id: "2-1", name: "API Integration.md", type: "file", path: "Data Sources/API Integration.md" },
      { id: "2-2", name: "Local Files.md", type: "file", path: "Data Sources/Local Files.md" },
    ],
  },
  {
    id: "3",
    name: "ML Models",
    type: "folder",
    children: [
      { id: "3-1", name: "Training.md", type: "file", path: "ML Models/Training.md" },
      { id: "3-2", name: "Inference.md", type: "file", path: "ML Models/Inference.md" },
    ],
  },
  { id: "4", name: "Quick Notes.md", type: "file", path: "Quick Notes.md" },
  { id: "5", name: "Ideas.md", type: "file", path: "Ideas.md" },
];

function TreeNode({
  item,
  depth = 0,
  onFileDoubleClick
}: {
  item: TreeItem;
  depth?: number;
  onFileDoubleClick?: (item: TreeItem) => void;
}) {
  const [isOpen, setIsOpen] = useState(true);

  const handleClick = () => {
    if (item.type === "folder") {
      setIsOpen(!isOpen);
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
          isOpen ? (
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
            <TreeNode key={child.id} item={child} depth={depth + 1} onFileDoubleClick={onFileDoubleClick} />
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
  return (
    <ScrollArea className="h-full">
      <div className="p-2">
        {mockFiles.map((item) => (
          <TreeNode key={item.id} item={item} onFileDoubleClick={onFileDoubleClick} />
        ))}
      </div>
    </ScrollArea>
  );
}
