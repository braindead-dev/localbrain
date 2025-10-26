import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Card } from "./ui/card";
import { Brain, StickyNote } from "lucide-react";
import { api } from "../lib/api";

interface NotesViewProps {
  onQueryClick?: (query: string) => void;
}

export function NotesView({ onQueryClick }: NotesViewProps) {
  const [quickNote, setQuickNote] = useState("");
  const [isDragging, setIsDragging] = useState(false);
  const [isOverDropzone, setIsOverDropzone] = useState(false);
  const [justSubmitted, setJustSubmitted] = useState(false);

  // Reset drag states on ANY mouse interaction to recover from stuck states
  useEffect(() => {
    const resetStates = () => {
      setIsDragging(false);
      setIsOverDropzone(false);
    };

    const handleMouseEnter = () => {
      if (isDragging || isOverDropzone) {
        resetStates();
      }
    };

    const handleMouseMove = () => {
      if (isDragging || isOverDropzone) {
        resetStates();
      }
    };

    const handleClick = () => {
      if (isDragging || isOverDropzone) {
        resetStates();
      }
    };

    const handleFocus = () => {
      resetStates();
    };

    const handleVisibilityChange = () => {
      if (!document.hidden) {
        resetStates();
      }
    };

    // Reset immediately on mount
    resetStates();

    // Add multiple event listeners to catch stuck states
    document.addEventListener('mouseenter', handleMouseEnter, true);
    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('click', handleClick);
    window.addEventListener('focus', handleFocus);
    document.addEventListener('visibilitychange', handleVisibilityChange);

    return () => {
      document.removeEventListener('mouseenter', handleMouseEnter, true);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('click', handleClick);
      window.removeEventListener('focus', handleFocus);
      document.removeEventListener('visibilitychange', handleVisibilityChange);
    };
  }, [isDragging, isOverDropzone]);

  const handleSubmitNote = async () => {
    if (quickNote.trim()) {
      // Force all drag states to false immediately
      setIsDragging(false);
      setIsOverDropzone(false);

      try {
        // Ingest the note into the vault
        await api.ingest(
          quickNote.trim(),
          'QuickNote',
          new Date().toISOString()
        );

        // Small delay before showing success to ensure drag states are cleared
        setTimeout(() => {
          setJustSubmitted(true);

          // Reset after success animation
          setTimeout(() => {
            setQuickNote("");
            setJustSubmitted(false);
          }, 600);
        }, 50);
      } catch (error) {
        console.error("Failed to submit note:", error);
        // Still clear the note even on error (user can see console for debugging)
        setTimeout(() => {
          setQuickNote("");
        }, 600);
      }
    }
  };

  const handleDragStart = (e: React.DragEvent) => {
    if (quickNote.trim()) {
      setIsDragging(true);
      e.dataTransfer.effectAllowed = "move";
      e.dataTransfer.setData("text/plain", quickNote);

      // Use the current target as the drag image for smooth visual feedback
      const draggedElement = e.currentTarget as HTMLElement;
      e.dataTransfer.setDragImage(draggedElement, draggedElement.offsetWidth / 2, draggedElement.offsetHeight / 2);
    }
  };

  const handleDragEnd = () => {
    // Always reset both states immediately when drag ends
    setIsDragging(false);
    setIsOverDropzone(false);
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    setIsOverDropzone(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    // Check if we're truly leaving the dropzone (not just entering a child)
    const relatedTarget = e.relatedTarget as Node;
    if (!relatedTarget || !e.currentTarget.contains(relatedTarget)) {
      setIsOverDropzone(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();

    // Immediately reset all drag states
    setIsDragging(false);
    setIsOverDropzone(false);

    handleSubmitNote();
  };

  return (
    <div
      className="h-full flex flex-col bg-background m-4 rounded-2xl overflow-hidden border border-border shadow-2xl"
      style={{ opacity: 1, visibility: 'visible' }}
    >
      {/* Header */}
      <div className="border-b border-border px-6 py-5 bg-card shadow-sm">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-primary/10 rounded-lg shadow-sm">
            <StickyNote className="h-5 w-5 text-primary" />
          </div>
          <h2 className="text-lg font-semibold">Quick Notes</h2>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex items-center justify-center p-8 bg-background">
        {/* Quick Notes Drag & Drop */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{
            type: "spring",
            stiffness: 200,
            damping: 25,
          }}
          className="w-full max-w-5xl"
        >
          <div className="flex gap-8 items-stretch justify-center">
            {/* Sticky Note - Source */}
            <div
              className={`flex-1 max-w-xl ${
                quickNote.trim() ? 'cursor-grab active:cursor-grabbing' : 'cursor-default'
              }`}
            >
              <motion.div
                key="sticky-note"
                draggable={quickNote.trim().length > 0}
                onDragStart={handleDragStart as any}
                onDragEnd={handleDragEnd as any}
                initial={{ scale: 1 }}
                animate={isDragging ? {
                  scale: 0.98,
                  rotateZ: 2,
                } : {
                  scale: 1,
                  rotateZ: 0,
                }}
                whileHover={quickNote.trim() && !isDragging ? { scale: 1.02, transition: { duration: 0.2 } } : {}}
                transition={{
                  type: "spring",
                  stiffness: 500,
                  damping: 35,
                  mass: 0.5,
                }}
                style={{
                  opacity: 1,
                }}
              >
              <Card className="p-8 shadow-2xl h-full min-h-[400px] flex flex-col bg-gradient-to-br from-yellow-50 to-yellow-100 dark:from-yellow-900/20 dark:to-amber-900/20 border-yellow-200 dark:border-yellow-800">
                <div className="flex items-center gap-3 mb-6">
                  <StickyNote className="h-6 w-6 text-yellow-600 dark:text-yellow-500" />
                  <h3 className="text-lg font-semibold text-yellow-900 dark:text-yellow-100">Quick Note</h3>
                </div>
                <textarea
                  value={quickNote}
                  onChange={(e) => setQuickNote(e.target.value)}
                  placeholder="Jot down a quick thought, idea, or reminder..."
                  className="w-full flex-1 p-4 rounded-lg border-0 bg-white/50 dark:bg-black/20 resize-none focus:outline-none focus:ring-2 focus:ring-yellow-400 text-base placeholder:text-yellow-600/60 dark:placeholder:text-yellow-400/60 text-yellow-900 dark:text-yellow-100 transition-all"
                />
                <AnimatePresence>
                  {quickNote.trim() && (
                    <motion.p
                      initial={{ opacity: 0, y: -10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -10 }}
                      transition={{
                        type: "spring",
                        stiffness: 400,
                        damping: 30,
                      }}
                      className="text-sm text-yellow-700 dark:text-yellow-400 mt-4 text-center italic font-medium"
                    >
                      ✨ Drag this note to send it to the agent →
                    </motion.p>
                  )}
                </AnimatePresence>
              </Card>
            </motion.div>
            </div>

            {/* Dropzone */}
            <div
              key="dropzone"
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              className="flex-1 max-w-xl"
            >
              <motion.div
                key="dropzone-motion"
                initial={{ scale: 1 }}
                animate={isOverDropzone ? {
                  scale: 1.05,
                } : {
                  scale: 1,
                }}
                transition={{
                  type: "spring",
                  stiffness: 400,
                  damping: 30,
                }}
              >
                <Card className={`p-8 h-full min-h-[400px] flex flex-col items-center justify-center border-2 border-dashed bg-gradient-to-br shadow-2xl ${
                  justSubmitted
                    ? 'border-green-500 bg-green-100 dark:bg-green-900/30'
                    : isOverDropzone
                    ? 'border-yellow-500 bg-yellow-100 dark:bg-yellow-900/30'
                    : 'border-yellow-300 dark:border-yellow-700 from-yellow-50/50 to-yellow-100/50 dark:from-yellow-900/10 dark:to-amber-900/10'
                }`}>
                  <motion.div
                    animate={{
                      scale: justSubmitted ? 1.15 : isOverDropzone ? 1.1 : 1,
                    }}
                    transition={{
                      type: "spring",
                      stiffness: 400,
                      damping: 30,
                    }}
                    className="flex flex-col items-center"
                  >
                    <motion.div
                      animate={{
                        scale: justSubmitted ? 1.3 : isOverDropzone ? 1.15 : 1,
                        rotate: isOverDropzone && !justSubmitted ? [0, -5, 5, -5, 5, 0] : 0,
                      }}
                      transition={{
                        scale: {
                          type: "spring",
                          stiffness: 400,
                          damping: 30,
                        },
                        rotate: {
                          duration: 0.5,
                          ease: "easeInOut",
                          repeat: isOverDropzone && !justSubmitted ? Infinity : 0,
                          type: "tween",
                        },
                      }}
                      className={`p-6 rounded-full mb-6 ${
                        justSubmitted
                          ? 'bg-green-500/20'
                          : 'bg-yellow-500/20'
                      }`}
                    >
                      <Brain className={`h-12 w-12 ${
                        justSubmitted
                          ? 'text-green-600 dark:text-green-500'
                          : 'text-yellow-600 dark:text-yellow-500'
                      }`} />
                    </motion.div>
                    <h3 className="text-xl font-semibold text-yellow-900 dark:text-yellow-100 text-center mb-3">
                      Send to Agent
                    </h3>
                    <AnimatePresence mode="wait">
                      <motion.p
                        key={justSubmitted ? 'success' : isOverDropzone ? 'drop' : 'default'}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -10 }}
                        transition={{
                          type: "spring",
                          stiffness: 400,
                          damping: 30,
                        }}
                        className={`text-sm text-center max-w-xs leading-relaxed ${
                          justSubmitted
                            ? 'text-green-700 dark:text-green-400 font-semibold'
                            : 'text-yellow-700 dark:text-yellow-400'
                        }`}
                      >
                        {justSubmitted ? '✅ Note sent!' : isOverDropzone ? '✨ Drop to send!' : 'Drop your note here to process it with AI'}
                      </motion.p>
                    </AnimatePresence>
                  </motion.div>
                </Card>
              </motion.div>
            </div>
          </div>
        </motion.div>
      </div>
    </div>
  );
}
