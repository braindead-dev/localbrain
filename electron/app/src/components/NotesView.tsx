import { useState } from "react";
import { Button } from "./ui/button";
import { Textarea } from "./ui/textarea";
import { Input } from "./ui/input";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "./ui/card";
import { ScrollArea } from "./ui/scroll-area";
import { Badge } from "./ui/badge";
import { toast } from "sonner";
import {
  Plus,
  Trash2,
  Pin,
  Clock,
  StickyNote,
} from "lucide-react";

interface Note {
  id: string;
  title: string;
  content: string;
  isPinned: boolean;
  createdAt: Date;
  updatedAt: Date;
}

export function NotesView() {
  const [notes, setNotes] = useState<Note[]>([
    {
      id: "1",
      title: "Example Context Note",
      content: "These are quick notes you can reference in your context. Perfect for temporary information, ideas, or things to remember.",
      isPinned: true,
      createdAt: new Date(2025, 9, 20),
      updatedAt: new Date(2025, 9, 20),
    },
  ]);
  const [newNoteTitle, setNewNoteTitle] = useState("");
  const [newNoteContent, setNewNoteContent] = useState("");
  const [editingNoteId, setEditingNoteId] = useState<string | null>(null);

  const handleAddNote = () => {
    if (!newNoteTitle.trim() && !newNoteContent.trim()) {
      toast.error("Please add a title or content for your note");
      return;
    }

    const newNote: Note = {
      id: Date.now().toString(),
      title: newNoteTitle.trim() || "Untitled Note",
      content: newNoteContent.trim(),
      isPinned: false,
      createdAt: new Date(),
      updatedAt: new Date(),
    };

    setNotes([newNote, ...notes]);
    setNewNoteTitle("");
    setNewNoteContent("");
    toast.success("Note added successfully");
  };

  const handleDeleteNote = (id: string) => {
    setNotes(notes.filter((note) => note.id !== id));
    toast.success("Note deleted");
  };

  const handleTogglePin = (id: string) => {
    setNotes(
      notes.map((note) =>
        note.id === id ? { ...note, isPinned: !note.isPinned } : note
      )
    );
  };

  const handleUpdateNote = (id: string, title: string, content: string) => {
    setNotes(
      notes.map((note) =>
        note.id === id
          ? { ...note, title: title || "Untitled Note", content, updatedAt: new Date() }
          : note
      )
    );
    setEditingNoteId(null);
    toast.success("Note updated");
  };

  const sortedNotes = [...notes].sort((a, b) => {
    if (a.isPinned && !b.isPinned) return -1;
    if (!a.isPinned && b.isPinned) return 1;
    return b.updatedAt.getTime() - a.updatedAt.getTime();
  });

  const formatDate = (date: Date) => {
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return "Just now";
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  };

  return (
    <div className="flex flex-col h-full overflow-hidden m-4 rounded-2xl bg-card shadow-2xl border border-border">
      <div className="border-b border-border p-6 space-y-4 shrink-0 bg-card shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
            <StickyNote className="h-5 w-5 text-primary" />
          </div>
          <div>
            <h2>Context Notes</h2>
            <p className="text-sm text-muted-foreground">
              Quick notes to reference in your context
            </p>
          </div>
        </div>

        {/* New Note Input */}
        <Card className="shadow-md">
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Add New Note</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <Input
              placeholder="Note title..."
              value={newNoteTitle}
              onChange={(e) => setNewNoteTitle(e.target.value)}
              className="shadow-sm"
            />
            <Textarea
              placeholder="Note content..."
              value={newNoteContent}
              onChange={(e) => setNewNoteContent(e.target.value)}
              className="min-h-[80px] shadow-sm"
            />
            <Button
              onClick={handleAddNote}
              className="w-full shadow-sm hover:shadow-md transition-shadow"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Note
            </Button>
          </CardContent>
        </Card>
      </div>

      {/* Notes List */}
      <div className="flex-1 min-h-0 overflow-hidden">
        <ScrollArea className="h-full">
          <div className="p-6 space-y-3">
            {sortedNotes.length === 0 ? (
              <div className="text-center py-12">
                <StickyNote className="h-12 w-12 mx-auto text-muted-foreground mb-3 opacity-50" />
                <p className="text-muted-foreground">No notes yet</p>
                <p className="text-sm text-muted-foreground mt-1">
                  Add your first note above
                </p>
              </div>
            ) : (
              sortedNotes.map((note) => (
                <Card
                  key={note.id}
                  className="hover:border-primary/50 hover:shadow-lg transition-all duration-200 shadow-md"
                >
                  <CardHeader>
                    <div className="flex items-start justify-between gap-3">
                      <div className="flex-1 min-w-0">
                        {editingNoteId === note.id ? (
                          <Input
                            defaultValue={note.title}
                            className="mb-2 shadow-sm"
                            id={`title-${note.id}`}
                          />
                        ) : (
                          <CardTitle className="flex items-center gap-2 break-words">
                            {note.title}
                            {note.isPinned && (
                              <Badge variant="secondary" className="text-xs shadow-sm shrink-0">
                                <Pin className="h-3 w-3 mr-1" />
                                Pinned
                              </Badge>
                            )}
                          </CardTitle>
                        )}
                        <CardDescription className="flex items-center gap-1 mt-1">
                          <Clock className="h-3 w-3" />
                          {formatDate(note.updatedAt)}
                        </CardDescription>
                      </div>
                      <div className="flex gap-1 shrink-0">
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleTogglePin(note.id)}
                          className={`h-8 w-8 hover:bg-accent ${
                            note.isPinned ? "text-primary" : ""
                          }`}
                        >
                          <Pin className="h-4 w-4" />
                        </Button>
                        <Button
                          variant="ghost"
                          size="icon"
                          onClick={() => handleDeleteNote(note.id)}
                          className="h-8 w-8 hover:bg-destructive/10 hover:text-destructive"
                        >
                          <Trash2 className="h-4 w-4" />
                        </Button>
                      </div>
                    </div>
                  </CardHeader>
                  <CardContent>
                    {editingNoteId === note.id ? (
                      <div className="space-y-2">
                        <Textarea
                          defaultValue={note.content}
                          className="min-h-[100px] shadow-sm"
                          id={`content-${note.id}`}
                        />
                        <div className="flex gap-2">
                          <Button
                            size="sm"
                            onClick={() => {
                              const titleInput = document.getElementById(
                                `title-${note.id}`
                              ) as HTMLInputElement;
                              const contentInput = document.getElementById(
                                `content-${note.id}`
                              ) as HTMLTextAreaElement;
                              handleUpdateNote(
                                note.id,
                                titleInput.value,
                                contentInput.value
                              );
                            }}
                            className="shadow-sm hover:shadow-md transition-shadow"
                          >
                            Save
                          </Button>
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() => setEditingNoteId(null)}
                            className="shadow-sm hover:shadow-md transition-shadow"
                          >
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div
                        className="text-sm whitespace-pre-wrap break-words cursor-pointer hover:text-foreground/80 transition-colors"
                        onClick={() => setEditingNoteId(note.id)}
                      >
                        {note.content || (
                          <span className="text-muted-foreground italic">
                            Click to add content...
                          </span>
                        )}
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))
            )}
          </div>
        </ScrollArea>
      </div>
    </div>
  );
}
