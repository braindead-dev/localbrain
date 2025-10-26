'use client';

import { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "../components/ui/button";
import { Input } from "../components/ui/input";
import { ResizableHandle, ResizablePanel, ResizablePanelGroup } from "../components/ui/resizable";
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from "../components/ui/tooltip";
import { Toaster } from "../components/ui/sonner";
import {
  Network,
  Folder,
  Settings,
  ChevronLeft,
  ChevronRight,
  Brain,
  Home as HomeIcon,
  StickyNote,
  GripHorizontal,
  PencilLine,
  MessageSquare,
} from "lucide-react";
import { ChatView } from "../components/ChatView";
import { ConnectionsView } from "../components/ConnectionsView";
import { EditorView } from "../components/EditorView";
import { SettingsView } from "../components/SettingsView";
import { NotesView } from "../components/NotesView";
import { FileTree, TreeItem } from "../components/FileTree";
import { HomeView } from "../components/HomeView";
import { VaultIcon } from "../components/VaultIcon";
import { RearrangeIcon } from "../components/RearrangeIcon";

type TabValue = "home" | "ask" | "connections" | "search" | "notes" | "settings";

interface Tab {
  value: TabValue;
  icon: any;
  label: string;
}

interface DraggableTabProps {
  tab: Tab;
  index: number;
  isActive: boolean;
  isRearrangeMode: boolean;
  onDragStart: (index: number) => void;
  onDragOver: (index: number) => void;
  onDragEnd: () => void;
  onClick: () => void;
  disabled: boolean;
}

function DraggableTab({ tab, index, isActive, isRearrangeMode, onDragStart, onDragOver, onDragEnd, onClick, disabled }: DraggableTabProps) {
  const Icon = tab.icon;

  const handleDragStart = (e: React.DragEvent<HTMLDivElement>) => {
    if (!isRearrangeMode) return;
    e.dataTransfer.effectAllowed = "move";
    onDragStart(index);
  };

  const handleDragOver = (e: React.DragEvent<HTMLDivElement>) => {
    if (!isRearrangeMode) return;
    e.preventDefault();
    e.dataTransfer.dropEffect = "move";
    onDragOver(index);
  };

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    if (!isRearrangeMode) return;
    e.preventDefault();
    onDragEnd();
  };

  return (
    <div
      draggable={isRearrangeMode}
      onDragStart={handleDragStart}
      onDragOver={handleDragOver}
      onDrop={handleDrop}
      onDragEnd={onDragEnd}
    >
      <Tooltip>
        <TooltipTrigger asChild>
          <Button
            variant="ghost"
            size="icon"
            onClick={onClick}
            disabled={disabled}
            data-active={isActive}
            className={`h-12 w-12 rounded-lg shadow-sm ${
              isActive
                ? "bg-primary text-primary-foreground shadow-md"
                : "text-foreground"
            } ${isRearrangeMode ? "cursor-move" : ""}
            transition-colors duration-200
            data-[active=false]:hover:bg-accent
            data-[active=true]:hover:bg-primary/90`}
          >
            <Icon className="h-5 w-5" />
          </Button>
        </TooltipTrigger>
        <TooltipContent side="right">
          <p>{tab.label}</p>
        </TooltipContent>
      </Tooltip>
    </div>
  );
}

function AppContent() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(true);
  const [activeTab, setActiveTab] = useState<TabValue>("home");
  const [setupOverlayVisible, setSetupOverlayVisible] = useState(false);
  const [isRearrangeMode, setIsRearrangeMode] = useState(false);
  const [openedFile, setOpenedFile] = useState<TreeItem | null>(null);
  const [showLineNumbers, setShowLineNumbers] = useState(false);
  const [highlightedFilePath, setHighlightedFilePath] = useState<string | null>(null);

  // Initialize dark mode from localStorage or default to true
  useEffect(() => {
    const savedDarkMode = localStorage.getItem('localBrainDarkMode');
    if (savedDarkMode !== null) {
      setDarkMode(savedDarkMode === 'true');
    } else {
      // Default to dark mode on first load
      setDarkMode(true);
      localStorage.setItem('localBrainDarkMode', 'true');
    }

    // Initialize line numbers preference
    const savedLineNumbers = localStorage.getItem('localBrainShowLineNumbers');
    if (savedLineNumbers !== null) {
      setShowLineNumbers(savedLineNumbers === 'true');
    }
  }, []);

  // Apply dark mode to document root for portals (like Dialog) to inherit
  useEffect(() => {
    if (darkMode) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    // Save preference to localStorage
    localStorage.setItem('localBrainDarkMode', String(darkMode));
  }, [darkMode]);

  const homeTab: Tab = { value: "home" as TabValue, icon: HomeIcon, label: "Home" };

  const defaultTabs: Tab[] = [
    { value: "ask" as TabValue, icon: MessageSquare, label: "Ask" },
    { value: "connections" as TabValue, icon: Network, label: "Connections" },
    { value: "search" as TabValue, icon: Folder, label: "Editor" },
    { value: "notes" as TabValue, icon: PencilLine, label: "Notes" },
  ];

  const [mainTabs, setMainTabs] = useState<Tab[]>(defaultTabs);
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [selectedConnection, setSelectedConnection] = useState<string | null>(null);
  const [autoQuery, setAutoQuery] = useState<string | null>(null);
  const [connectedIntegrations, setConnectedIntegrations] = useState<Array<{id: string, name: string, connected: boolean}>>([]);

  const handleDragStart = (index: number) => {
    setDraggedIndex(index);
  };

  const handleDragOver = (index: number) => {
    if (draggedIndex === null || draggedIndex === index) return;

    const updatedTabs = [...mainTabs];
    const [draggedTab] = updatedTabs.splice(draggedIndex, 1);
    updatedTabs.splice(index, 0, draggedTab);
    setMainTabs(updatedTabs);
    setDraggedIndex(index);
  };

  const handleDragEnd = () => {
    setDraggedIndex(null);
  };

  const handleFileOpen = (file: TreeItem) => {
    setOpenedFile(file);
    setActiveTab("search"); // Switch to editor tab
    setSidebarOpen(false); // Close the vault sidebar
  };

  const handleConnectionClick = (connectionId: string) => {
    setSelectedConnection(connectionId);
    setActiveTab("connections");
  };

  const handleQueryClick = (query: string) => {
    setAutoQuery(query);
    setActiveTab("ask");
  };

  const handleFileOpenFromChat = (filePath: string) => {
    // Open the vault sidebar and highlight the file
    setSidebarOpen(true);
    setHighlightedFilePath(filePath);
  };

  return (
    <div className="h-screen w-screen flex bg-background relative">
        <Toaster />
        {/* Left Navigation Sidebar - Floating */}
        <div className={`fixed left-4 top-4 bottom-4 w-20 bg-card border border-border rounded-2xl flex flex-col items-center py-4 gap-3 shadow-2xl outline-none z-50 ${setupOverlayVisible ? 'pointer-events-none opacity-50' : ''}`}>
          {/* Navigation Icons */}
          <TooltipProvider delayDuration={0}>
            <div className="flex flex-col gap-3 flex-1">
              {/* Home Button - Always at top, not draggable */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setActiveTab("home")}
                    disabled={setupOverlayVisible}
                    data-active={activeTab === "home"}
                    className={`h-12 w-12 rounded-lg shadow-sm ${
                      activeTab === "home"
                        ? "bg-primary text-primary-foreground shadow-md"
                        : "text-foreground"
                    }
                    transition-colors duration-200
                    data-[active=false]:hover:bg-accent
                    data-[active=true]:hover:bg-primary/90`}
                  >
                    <HomeIcon className="h-5 w-5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p>Home</p>
                </TooltipContent>
              </Tooltip>

              {/* Draggable Tabs */}
              {mainTabs.map((tab, index) => (
                <DraggableTab
                  key={tab.value}
                  tab={tab}
                  index={index}
                  isActive={activeTab === tab.value}
                  isRearrangeMode={isRearrangeMode}
                  onDragStart={handleDragStart}
                  onDragOver={handleDragOver}
                  onDragEnd={handleDragEnd}
                  onClick={() => setActiveTab(tab.value)}
                  disabled={setupOverlayVisible}
                />
              ))}
            </div>

            {/* Rearrange and Settings at bottom */}
            <div className="flex flex-col gap-3">
              {/* Rearrange Button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setIsRearrangeMode(!isRearrangeMode)}
                    disabled={setupOverlayVisible}
                    data-active={isRearrangeMode}
                    className={`h-12 w-12 rounded-lg shadow-sm ${
                      isRearrangeMode
                        ? "bg-primary text-primary-foreground shadow-md"
                        : "text-foreground"
                    }
                    transition-colors duration-200
                    data-[active=false]:hover:bg-accent
                    data-[active=true]:hover:bg-primary/90`}
                  >
                    <RearrangeIcon className="h-5 w-5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p>{isRearrangeMode ? "Done Rearranging" : "Rearrange Icons"}</p>
                </TooltipContent>
              </Tooltip>

              {/* Settings Button */}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setActiveTab("settings")}
                    disabled={setupOverlayVisible}
                    data-active={activeTab === "settings"}
                    className={`h-12 w-12 rounded-lg shadow-sm ${
                      activeTab === "settings"
                        ? "bg-primary text-primary-foreground shadow-md"
                        : "text-foreground"
                    }
                    transition-colors duration-200
                    data-[active=false]:hover:bg-accent
                    data-[active=true]:hover:bg-primary/90`}
                  >
                    <Settings className="h-5 w-5" />
                  </Button>
                </TooltipTrigger>
                <TooltipContent side="right">
                  <p>Settings</p>
                </TooltipContent>
              </Tooltip>
            </div>
          </TooltipProvider>
        </div>

        {/* Main Content Area */}
        <div className="flex-1 flex overflow-hidden relative pl-28">
          {/* Main Content */}
          <div className="flex flex-col h-full w-full">
            {activeTab === "home" && (
              <HomeView
                onSetupVisibilityChange={setSetupOverlayVisible}
                onConnectionClick={handleConnectionClick}
                onQueryClick={handleQueryClick}
                connectedIntegrations={connectedIntegrations}
              />
            )}
            {activeTab === "ask" && (
              <ChatView
                autoQuery={autoQuery}
                onQueryProcessed={() => setAutoQuery(null)}
                onFileOpen={handleFileOpenFromChat}
              />
            )}
            {activeTab === "connections" && (
              <ConnectionsView />
            )}
            {activeTab === "search" && (
              <EditorView
                initialFilePath={openedFile?.path}
                showLineNumbers={showLineNumbers}
              />
            )}
            {activeTab === "notes" && <NotesView />}
            {activeTab === "settings" && (
              <SettingsView
                darkMode={darkMode}
                setDarkMode={setDarkMode}
                showLineNumbers={showLineNumbers}
                setShowLineNumbers={setShowLineNumbers}
              />
            )}
          </div>

          {/* Animated File Tree Sidebar */}
          <AnimatePresence>
            {sidebarOpen && (
              <motion.div
                key="file-sidebar"
                initial={{ x: "100%" }}
                animate={{ x: 0 }}
                exit={{ x: "100%" }}
                transition={{ type: "spring", damping: 20, stiffness: 300, mass: 0.8 }}
                className="absolute right-0 top-0 h-full w-1/4 flex flex-col border-l border-border bg-card shadow-2xl z-40"
                style={{ boxShadow: '-8px 0 24px -4px rgba(0, 0, 0, 0.5)' }}
              >
                <div className="border-b border-border px-4 py-[1.375rem] flex items-center justify-between bg-card shrink-0">
                  <div className="flex items-center gap-2">
                    <VaultIcon className="h-5 w-5" isOpen={sidebarOpen} />
                    <h2 className="text-sm">Vault</h2>
                  </div>
                  <Button
                    variant="ghost"
                    size="icon"
                    onClick={() => setSidebarOpen(false)}
                    className="h-8 w-8 hover:bg-accent"
                  >
                    <ChevronRight className="h-4 w-4" />
                  </Button>
                </div>
                <div className="px-4 py-3 border-b border-border bg-card shrink-0">
                  <Input
                    placeholder="Search files..."
                    className="h-9 shadow-sm"
                  />
                </div>
                <FileTree onFileDoubleClick={handleFileOpen} highlightedFilePath={highlightedFilePath || undefined} />
              </motion.div>
            )}
          </AnimatePresence>

          {/* Floating File Icon Button */}
          <AnimatePresence>
            {!sidebarOpen && (
              <motion.div
                key="file-button"
                initial={{ scale: 0, opacity: 0, rotate: -180 }}
                animate={{ scale: 1, opacity: 1, rotate: 0 }}
                exit={{ scale: 0, opacity: 0, rotate: 180 }}
                transition={{ type: "spring", damping: 25, stiffness: 300 }}
                className="absolute top-8 right-8 z-50"
              >
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setSidebarOpen(true)}
                  disabled={setupOverlayVisible}
                  className="h-12 w-12 rounded-xl bg-card hover:bg-accent shadow-lg hover:shadow-xl transition-all disabled:opacity-50"
                >
                  <VaultIcon className="h-[2.75rem] w-[2.75rem]" isOpen={sidebarOpen} />
                </Button>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
  );
}

export default function Home() {
  return <AppContent />;
}
