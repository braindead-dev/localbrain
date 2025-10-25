import { useState, useEffect } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "./ui/button";
import { Card } from "./ui/card";
import { Input } from "./ui/input";
import { Label } from "./ui/label";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "./ui/dialog";
import { ScrollArea } from "./ui/scroll-area";
import { FolderOpen, Brain, Folder, X, Search, StickyNote, Lightbulb, CheckCircle2, AlertCircle, Activity, Database, HardDrive, ChevronLeft, ChevronRight, Zap, Shield, Boxes, Sparkles, Check, XCircle } from "lucide-react";

interface HomeViewProps {
  onSetupVisibilityChange: (visible: boolean) => void;
  onConnectionClick: (connectionId: string) => void;
  onQueryClick: (query: string) => void;
  connectedIntegrations: Array<{id: string, name: string, connected: boolean}>;
}

export function HomeView({ onSetupVisibilityChange, onConnectionClick, onQueryClick, connectedIntegrations }: HomeViewProps) {
  const [vaultPath, setVaultPath] = useState<string | null>(null);
  const [isSelecting, setIsSelecting] = useState(false);
  const [showSetup, setShowSetup] = useState(false);
  const [isFirstTime, setIsFirstTime] = useState(true);
  const [showPathDialog, setShowPathDialog] = useState(false);
  const [pathInput, setPathInput] = useState("");
  const [completedSteps, setCompletedSteps] = useState<number[]>([]);
  const [dismissedWidgets, setDismissedWidgets] = useState<string[]>([]);
  const [expandedSection, setExpandedSection] = useState<'connectors' | 'ingestion' | 'vault' | null>(null);
  const [currentSlide, setCurrentSlide] = useState(0);
  const [hasSeenCarousel, setHasSeenCarousel] = useState(true);
  const [showCarousel, setShowCarousel] = useState(false);

  useEffect(() => {
    // Check if vault location is already set
    const savedPath = localStorage.getItem("localBrainVaultPath");
    const carouselSeen = localStorage.getItem("localBrainCarouselSeen");
    const welcomeCompleted = localStorage.getItem("localBrainWelcomeCompleted");

    setVaultPath(savedPath);
    setHasSeenCarousel(carouselSeen === "true");

    // If welcome widget was completed before, mark all steps as completed
    if (welcomeCompleted === "true") {
      setCompletedSteps([1, 2, 3]);
    }

    if (!savedPath) {
      if (!carouselSeen) {
        // First time user - show carousel
        setShowCarousel(true);
        setShowSetup(false);
        onSetupVisibilityChange(true);
      } else {
        // Returning user without vault - show setup directly
        setShowSetup(true);
        setIsFirstTime(true);
        onSetupVisibilityChange(true);
      }
    }
  }, [onSetupVisibilityChange]);

  const handleSelectVault = () => {
    setShowPathDialog(true);
  };

  const handleBrowseFolder = async () => {
    setIsSelecting(true);
    
    try {
      // Try to use the File System Access API (modern browsers)
      if ('showDirectoryPicker' in window) {
        const dirHandle = await (window as any).showDirectoryPicker();
        const path = dirHandle.name; // In a real app, you'd get the full path
        setPathInput(path);
      } else {
        // Fallback: inform user to paste the path manually
        alert("Your browser doesn't support folder selection. Please paste the folder path manually.");
      }
    } catch (error) {
      // User cancelled or error occurred
      console.log("Folder selection cancelled or error:", error);
    } finally {
      setIsSelecting(false);
    }
  };

  const handleConfirmPath = () => {
    if (pathInput && pathInput.trim()) {
      const trimmedPath = pathInput.trim();
      localStorage.setItem("localBrainVaultPath", trimmedPath);
      setVaultPath(trimmedPath);
      setShowSetup(false);
      setShowPathDialog(false);
      setPathInput("");
      onSetupVisibilityChange(false);
    }
  };

  const handleCancelPathDialog = () => {
    setShowPathDialog(false);
    setPathInput("");
  };

  const handleCancelSetup = () => {
    setShowSetup(false);
    onSetupVisibilityChange(false);
  };

  const toggleStep = (stepNumber: number) => {
    const newCompletedSteps = completedSteps.includes(stepNumber)
      ? completedSteps.filter(s => s !== stepNumber)
      : [...completedSteps, stepNumber];

    setCompletedSteps(newCompletedSteps);

    // Check if all steps are now completed
    if (newCompletedSteps.length === 3 && !completedSteps.includes(stepNumber)) {
      // Save to localStorage that welcome is completed
      localStorage.setItem("localBrainWelcomeCompleted", "true");

      // Wait 1.5 seconds before hiding the widget
      setTimeout(() => {
        // Only hide if still all 3 are completed (user didn't uncheck)
        setCompletedSteps(prev => {
          if (prev.length === 3) {
            return prev;
          }
          return prev;
        });
      }, 1500);
    }
  };

  const dismissWidget = (widgetId: string) => {
    setDismissedWidgets(prev => [...prev, widgetId]);
  };

  const handleNextSlide = () => {
    if (currentSlide === 3) {
      // User has seen all slides
      localStorage.setItem("localBrainCarouselSeen", "true");
      setHasSeenCarousel(true);
      setShowCarousel(false);
      setShowSetup(true);
      setIsFirstTime(true);
    } else {
      setCurrentSlide((prev) => prev + 1);
    }
  };

  const allStepsCompleted = completedSteps.length === 3;
  const allWidgetsDismissed = dismissedWidgets.length === 4;

  return (
    <div className="h-full flex flex-col bg-background relative m-4 rounded-2xl overflow-hidden border border-border shadow-2xl">
      {/* Header */}
      <div className={`border-b border-border px-6 py-5 bg-card shadow-sm ${showSetup ? 'pointer-events-none' : ''}`}>
        <div className="relative flex justify-center items-center">
          <div className="flex items-center gap-3">
            <motion.div
              className="p-2 bg-primary/10 rounded-lg shadow-sm"
              initial={{ x: 100 }}
              animate={{ x: 0 }}
              transition={{
                type: "spring",
                damping: 22,
                stiffness: 90,
                duration: 1.0,
              }}
            >
              <Brain className="h-8 w-8 text-primary" />
            </motion.div>
            <div className="overflow-hidden">
              <motion.h1
                initial={{ x: -500 }}
                animate={{ x: 0 }}
                transition={{
                  type: "spring",
                  damping: 22,
                  stiffness: 90,
                  duration: 1.0,
                }}
              >
                Welcome to LocalBrain
              </motion.h1>
            </div>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <ScrollArea className={`flex-1 overflow-auto ${showSetup || showCarousel ? 'pointer-events-none' : ''}`}>
        {!showSetup && !showCarousel && (
          <div className="px-6 py-8">
            <div className="max-w-7xl mx-auto space-y-6">
              {/* Quick Start Guide */}
              <AnimatePresence>
                {!allStepsCompleted && (
                  <motion.div
                    initial={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0, marginBottom: 0 }}
                    transition={{ duration: 0.3 }}
                    className="flex items-center justify-center min-h-[calc(100vh-200px)]"
                  >
                    <Card className="p-10 shadow-lg bg-gradient-to-br from-card to-card/80">
                      <h2 className="mb-8 text-2xl text-center font-semibold">Let's Get Started!</h2>
                      <div className="flex gap-8 items-start justify-center">
                          {/* Step 1 */}
                          <div className="flex flex-col items-center flex-1 max-w-sm">
                            <div
                              className={`flex-shrink-0 w-14 h-14 rounded-full text-primary-foreground flex items-center justify-center shadow-lg text-xl font-bold -mb-7 z-10 cursor-pointer transition-all duration-500 hover:scale-110 active:scale-95 ${
                                completedSteps.includes(1) ? 'bg-green-500' : 'bg-primary'
                              }`}
                              onClick={() => toggleStep(1)}
                            >
                              <motion.div
                                key={completedSteps.includes(1) ? 'check-1' : 'num-1'}
                                initial={{ scale: 0, rotate: -180 }}
                                animate={{ scale: 1, rotate: 0 }}
                                exit={{ scale: 0, rotate: 180 }}
                                transition={{ duration: 0.4, type: "spring" }}
                              >
                                {completedSteps.includes(1) ? <Check className="h-6 w-6" strokeWidth={3} /> : '1'}
                              </motion.div>
                            </div>
                            <div
                              className={`cursor-pointer transition-all duration-200 rounded-xl p-6 pt-10 border-2 bg-background hover:bg-accent/30 hover:border-primary/50 hover:shadow-xl w-full h-[220px] flex flex-col justify-center ${
                                completedSteps.includes(1)
                                  ? 'border-green-500/50 bg-green-500/5'
                                  : 'border-border'
                              }`}
                              onClick={() => toggleStep(1)}
                            >
                              <h3 className={`mb-3 text-center font-semibold text-lg transition-all duration-500 ${completedSteps.includes(1) ? 'line-through decoration-2 text-muted-foreground' : ''}`}>
                                Connect Your Apps
                              </h3>
                              <p className={`text-muted-foreground text-sm text-center leading-relaxed transition-all duration-500 ${completedSteps.includes(1) ? 'line-through decoration-2' : ''}`}>
                                Head to the Connections tab to link LocalBrain with your favorite apps like GitHub, Notion, Slack, and more. This enables seamless data integration.
                              </p>
                            </div>
                          </div>

                          {/* Step 2 */}
                          <div className="flex flex-col items-center flex-1 max-w-sm">
                            <div
                              className={`flex-shrink-0 w-14 h-14 rounded-full text-primary-foreground flex items-center justify-center shadow-lg text-xl font-bold -mb-7 z-10 cursor-pointer transition-all duration-500 hover:scale-110 active:scale-95 ${
                                completedSteps.includes(2) ? 'bg-green-500' : 'bg-primary'
                              }`}
                              onClick={() => toggleStep(2)}
                            >
                              <motion.div
                                key={completedSteps.includes(2) ? 'check-2' : 'num-2'}
                                initial={{ scale: 0, rotate: -180 }}
                                animate={{ scale: 1, rotate: 0 }}
                                exit={{ scale: 0, rotate: 180 }}
                                transition={{ duration: 0.4, type: "spring" }}
                              >
                                {completedSteps.includes(2) ? <Check className="h-6 w-6" strokeWidth={3} /> : '2'}
                              </motion.div>
                            </div>
                            <div
                              className={`cursor-pointer transition-all duration-200 rounded-xl p-6 pt-10 border-2 bg-background hover:bg-accent/30 hover:border-primary/50 hover:shadow-xl w-full h-[220px] flex flex-col justify-center ${
                                completedSteps.includes(2)
                                  ? 'border-green-500/50 bg-green-500/5'
                                  : 'border-border'
                              }`}
                              onClick={() => toggleStep(2)}
                            >
                              <h3 className={`mb-3 text-center font-semibold text-lg transition-all duration-500 ${completedSteps.includes(2) ? 'line-through decoration-2 text-muted-foreground' : ''}`}>
                                Start Collecting Context
                              </h3>
                              <p className={`text-muted-foreground text-sm text-center leading-relaxed transition-all duration-500 ${completedSteps.includes(2) ? 'line-through decoration-2' : ''}`}>
                                Once connected, LocalBrain will automatically gather and organize information from your integrated apps. Sit back and let it work its magic.
                              </p>
                            </div>
                          </div>

                          {/* Step 3 */}
                          <div className="flex flex-col items-center flex-1 max-w-sm">
                            <div
                              className={`flex-shrink-0 w-14 h-14 rounded-full text-primary-foreground flex items-center justify-center shadow-lg text-xl font-bold -mb-7 z-10 cursor-pointer transition-all duration-500 hover:scale-110 active:scale-95 ${
                                completedSteps.includes(3) ? 'bg-green-500' : 'bg-primary'
                              }`}
                              onClick={() => toggleStep(3)}
                            >
                              <motion.div
                                key={completedSteps.includes(3) ? 'check-3' : 'num-3'}
                                initial={{ scale: 0, rotate: -180 }}
                                animate={{ scale: 1, rotate: 0 }}
                                exit={{ scale: 0, rotate: 180 }}
                                transition={{ duration: 0.4, type: "spring" }}
                              >
                                {completedSteps.includes(3) ? <Check className="h-6 w-6" strokeWidth={3} /> : '3'}
                              </motion.div>
                            </div>
                            <div
                              className={`cursor-pointer transition-all duration-200 rounded-xl p-6 pt-10 border-2 bg-background hover:bg-accent/30 hover:border-primary/50 hover:shadow-xl w-full h-[220px] flex flex-col justify-center ${
                                completedSteps.includes(3)
                                  ? 'border-green-500/50 bg-green-500/5'
                                  : 'border-border'
                              }`}
                              onClick={() => toggleStep(3)}
                            >
                              <h3 className={`mb-3 text-center font-semibold text-lg transition-all duration-500 ${completedSteps.includes(3) ? 'line-through decoration-2 text-muted-foreground' : ''}`}>
                                Ask Questions
                              </h3>
                              <p className={`text-muted-foreground text-sm text-center leading-relaxed transition-all duration-500 ${completedSteps.includes(3) ? 'line-through decoration-2' : ''}`}>
                                Use the Ask tab to query your personal knowledge base and get instant answers from all your connected data. Your AI assistant is ready!
                              </p>
                            </div>
                          </div>
                        </div>
                      </Card>
                    </motion.div>
                  )}
                </AnimatePresence>

              {/* System Status and Activity Feed - Side by Side */}
              <AnimatePresence>
                {allStepsCompleted && (
                  <motion.div
                    initial={{ opacity: 0, y: 20 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.8, ease: "easeOut", delay: 0.3 }}
                    className="grid grid-cols-2 gap-6"
                  >
                {/* Status Widget */}
                <Card className="p-6 shadow-lg">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <Activity className="h-5 w-5 text-primary" />
                    </div>
                    <h2>System Status</h2>
                  </div>

                  <div className="space-y-4">
                    {/* Connector Health - Expandable */}
                    <div className="p-4 bg-background/50 rounded-lg border border-border">
                      <button
                        onClick={() => setExpandedSection(expandedSection === 'connectors' ? null : 'connectors')}
                        className="w-full"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            {connectedIntegrations.every(i => i.connected) && connectedIntegrations.length > 0 ? (
                              <CheckCircle2 className="h-4 w-4 text-green-500" />
                            ) : (
                              <XCircle className="h-4 w-4 text-red-500" />
                            )}
                            <h3 className="text-sm font-medium">Connectors</h3>
                          </div>
                          <motion.div
                            animate={{ rotate: expandedSection === 'connectors' ? 180 : 0 }}
                            transition={{ duration: 0.2 }}
                          >
                            <svg className="h-4 w-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </motion.div>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <p className="text-2xl font-bold">
                            {connectedIntegrations.filter(i => i.connected).length}/{connectedIntegrations.length}
                          </p>
                          <p className="text-xs text-muted-foreground">Active connections</p>
                        </div>
                      </button>

                      <AnimatePresence>
                        {expandedSection === 'connectors' && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-4 pt-4 border-t border-border space-y-2">
                              {connectedIntegrations.map((integration) => (
                                <button
                                  key={integration.id}
                                  onClick={() => onConnectionClick(integration.id)}
                                  className="w-full flex items-center justify-between text-xs hover:bg-accent/50 p-2 rounded transition-colors"
                                >
                                  <span className="flex items-center gap-2">
                                    <div className={`h-2 w-2 rounded-full ${integration.connected ? 'bg-green-500' : 'bg-gray-400'}`} />
                                    {integration.name}
                                  </span>
                                  <span className="text-muted-foreground">
                                    {integration.connected ? 'Connected' : 'Inactive'} →
                                  </span>
                                </button>
                              ))}
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* Ingestion Statistics - Expandable */}
                    <div className="p-4 bg-background/50 rounded-lg border border-border">
                      <button
                        onClick={() => setExpandedSection(expandedSection === 'ingestion' ? null : 'ingestion')}
                        className="w-full"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <Database className="h-4 w-4 text-blue-500" />
                            <h3 className="text-sm font-medium">Ingestion</h3>
                          </div>
                          <motion.div
                            animate={{ rotate: expandedSection === 'ingestion' ? 180 : 0 }}
                            transition={{ duration: 0.2 }}
                          >
                            <svg className="h-4 w-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </motion.div>
                        </div>
                        <div className="flex items-baseline gap-2">
                          <p className="text-2xl font-bold">1,247</p>
                          <p className="text-xs text-muted-foreground">Items indexed</p>
                        </div>
                      </button>

                      <AnimatePresence>
                        {expandedSection === 'ingestion' && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-4 pt-4 border-t border-border space-y-2">
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Documents</span>
                                <span className="font-medium">523</span>
                              </div>
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Emails</span>
                                <span className="font-medium">384</span>
                              </div>
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Code Files</span>
                                <span className="font-medium">198</span>
                              </div>
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Notes</span>
                                <span className="font-medium">142</span>
                              </div>
                              <div className="pt-2 mt-2 border-t border-border">
                                <div className="flex items-center justify-between text-xs">
                                  <span className="text-muted-foreground">Last sync</span>
                                  <span className="font-medium">5 minutes ago</span>
                                </div>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>

                    {/* Vault Path - Expandable */}
                    <div className="p-4 bg-background/50 rounded-lg border border-border">
                      <button
                        onClick={() => setExpandedSection(expandedSection === 'vault' ? null : 'vault')}
                        className="w-full"
                      >
                        <div className="flex items-center justify-between mb-3">
                          <div className="flex items-center gap-2">
                            <HardDrive className="h-4 w-4 text-purple-500" />
                            <h3 className="text-sm font-medium">Vault</h3>
                          </div>
                          <motion.div
                            animate={{ rotate: expandedSection === 'vault' ? 180 : 0 }}
                            transition={{ duration: 0.2 }}
                          >
                            <svg className="h-4 w-4 text-muted-foreground" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </motion.div>
                        </div>
                        <p className="text-xs font-mono truncate text-left">{vaultPath || "Not configured"}</p>
                      </button>

                      <AnimatePresence>
                        {expandedSection === 'vault' && (
                          <motion.div
                            initial={{ height: 0, opacity: 0 }}
                            animate={{ height: "auto", opacity: 1 }}
                            exit={{ height: 0, opacity: 0 }}
                            transition={{ duration: 0.2 }}
                            className="overflow-hidden"
                          >
                            <div className="mt-4 pt-4 border-t border-border space-y-2">
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Storage used</span>
                                <span className="font-medium">2.4 GB</span>
                              </div>
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Total files</span>
                                <span className="font-medium">1,247</span>
                              </div>
                              <div className="flex items-center justify-between text-xs">
                                <span className="text-muted-foreground">Embeddings</span>
                                <span className="font-medium">3,842</span>
                              </div>
                              <div className="pt-2 mt-2 border-t border-border">
                                <p className="text-xs text-muted-foreground break-all">
                                  {vaultPath || "Not configured"}
                                </p>
                              </div>
                            </div>
                          </motion.div>
                        )}
                      </AnimatePresence>
                    </div>
                  </div>
                </Card>

                {/* Activity Feed */}
                <Card className="p-6 shadow-lg">
                  <div className="flex items-center gap-3 mb-6">
                    <div className="p-2 bg-primary/10 rounded-lg">
                      <Activity className="h-5 w-5 text-primary" />
                    </div>
                    <h2>Recent Activity</h2>
                  </div>

                  <ScrollArea className="h-[600px] pr-4">
                    <div className="space-y-3">
                      {/* Recent Search */}
                      <button
                        onClick={() => onQueryClick("How to implement authentication in Next.js")}
                        className="w-full flex items-start gap-3 p-3 rounded-lg hover:bg-accent/50 transition-all cursor-pointer text-left hover:scale-[1.02] active:scale-[0.98]"
                      >
                        <div className="p-2 bg-blue-500/10 rounded-lg mt-1">
                          <Search className="h-4 w-4 text-blue-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h3 className="text-sm font-medium">Search Query</h3>
                            <span className="text-xs text-muted-foreground">2 min ago</span>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1 break-words">
                            "How to implement authentication in Next.js"
                          </p>
                        </div>
                      </button>

                      {/* Recent Note */}
                      <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-accent/50 transition-colors cursor-pointer">
                        <div className="p-2 bg-green-500/10 rounded-lg mt-1">
                          <StickyNote className="h-4 w-4 text-green-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h3 className="text-sm font-medium">Note Created</h3>
                            <span className="text-xs text-muted-foreground">1 hour ago</span>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1 break-words">
                            Meeting notes: Project planning session
                          </p>
                        </div>
                      </div>

                      {/* Recent Insight */}
                      <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-accent/50 transition-colors cursor-pointer">
                        <div className="p-2 bg-yellow-500/10 rounded-lg mt-1">
                          <Lightbulb className="h-4 w-4 text-yellow-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h3 className="text-sm font-medium">Insight Generated</h3>
                            <span className="text-xs text-muted-foreground">3 hours ago</span>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1 break-words">
                            Connected patterns found between React documentation and your recent code
                          </p>
                        </div>
                      </div>

                      {/* Recent Search */}
                      <button
                        onClick={() => onQueryClick("Best practices for Electron app development")}
                        className="w-full flex items-start gap-3 p-3 rounded-lg hover:bg-accent/50 transition-all cursor-pointer text-left hover:scale-[1.02] active:scale-[0.98]"
                      >
                        <div className="p-2 bg-blue-500/10 rounded-lg mt-1">
                          <Search className="h-4 w-4 text-blue-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h3 className="text-sm font-medium">Search Query</h3>
                            <span className="text-xs text-muted-foreground">5 hours ago</span>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1 break-words">
                            "Best practices for Electron app development"
                          </p>
                        </div>
                      </button>

                      {/* Recent Note */}
                      <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-accent/50 transition-colors cursor-pointer">
                        <div className="p-2 bg-green-500/10 rounded-lg mt-1">
                          <StickyNote className="h-4 w-4 text-green-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h3 className="text-sm font-medium">Note Created</h3>
                            <span className="text-xs text-muted-foreground">Yesterday</span>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1 break-words">
                            Ideas for improving user interface
                          </p>
                        </div>
                      </div>

                      {/* Additional Activity Items */}
                      <div className="flex items-start gap-3 p-3 rounded-lg hover:bg-accent/50 transition-colors cursor-pointer">
                        <div className="p-2 bg-purple-500/10 rounded-lg mt-1">
                          <Database className="h-4 w-4 text-purple-500" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center justify-between">
                            <h3 className="text-sm font-medium">Data Sync</h3>
                            <span className="text-xs text-muted-foreground">Yesterday</span>
                          </div>
                          <p className="text-sm text-muted-foreground mt-1 break-words">
                            Synced 127 new items from Gmail
                          </p>
                        </div>
                      </div>
                    </div>
                  </ScrollArea>
                </Card>
              </motion.div>
                )}
              </AnimatePresence>
            </div>
          </div>
        )}
      </ScrollArea>

      {/* Setup Overlay */}
      {showSetup && (
        <div className="absolute inset-0 flex items-center justify-center z-50 p-6">
          {/* Backdrop with blur */}
          <div className="absolute inset-0 bg-background/90 backdrop-blur-lg" />
          
          {/* Setup Card */}
          <Card className="max-w-xl w-full p-8 shadow-2xl border-2 relative z-10">
            {isFirstTime ? (
              // First-time setup
              <div className="text-center space-y-6">
                <div className="flex justify-center">
                  <div className="p-4 bg-primary/10 rounded-2xl">
                    <Brain className="h-16 w-16 text-primary" />
                  </div>
                </div>
                
                <div className="space-y-2">
                  <h1>Welcome to LocalBrain</h1>
                  <p className="text-muted-foreground">
                    Your personal, local-first knowledge management system
                  </p>
                </div>

                <div className="bg-muted rounded-lg p-5 space-y-3 text-center">
                  <h2>First-Time Setup</h2>
                  <p className="text-muted-foreground text-sm">
                    LocalBrain needs a location to store your vault. This folder will contain all the context and data collected from your connected apps.
                  </p>
                </div>

                <Button
                  onClick={handleSelectVault}
                  disabled={isSelecting}
                  size="lg"
                  className="w-full shadow-lg hover:shadow-xl transition-all"
                >
                  <FolderOpen className="h-5 w-5 mr-2" />
                  {isSelecting ? "Selecting..." : "Choose Vault Location"}
                </Button>

                <p className="text-xs text-muted-foreground">
                  You can change this location later in Settings
                </p>
              </div>
            ) : (
              // Change vault location
              <div className="space-y-6">
                <div className="space-y-2 text-center">
                  <h2>Change Vault Location</h2>
                  <p className="text-muted-foreground text-sm">
                    Select a new folder to store your LocalBrain vault.
                  </p>
                </div>

                <div className="bg-muted rounded-lg p-4 space-y-2">
                  <p className="text-sm">Current location:</p>
                  <code className="block px-3 py-2 bg-background rounded text-xs break-all">
                    {vaultPath}
                  </code>
                </div>

                <div className="bg-amber-500/10 border border-amber-500/20 rounded-lg p-4">
                  <p className="text-sm text-amber-600 dark:text-amber-400">
                    <strong>Note:</strong> Changing your vault location will not move existing data. Make sure to manually transfer your files if needed.
                  </p>
                </div>

                <div className="flex gap-3">
                  <Button
                    onClick={handleCancelSetup}
                    variant="outline"
                    className="flex-1 shadow-sm"
                  >
                    Cancel
                  </Button>
                  <Button
                    onClick={handleSelectVault}
                    disabled={isSelecting}
                    className="flex-1 shadow-lg hover:shadow-xl transition-all"
                  >
                    <FolderOpen className="h-4 w-4 mr-2" />
                    {isSelecting ? "Selecting..." : "Choose New Location"}
                  </Button>
                </div>
              </div>
            )}
          </Card>
        </div>
      )}

      {/* Path Selection Dialog */}
      <Dialog open={showPathDialog} onOpenChange={setShowPathDialog}>
        <DialogContent className="sm:max-w-[500px]">
          <DialogHeader>
            <DialogTitle>Choose Vault Location</DialogTitle>
            <DialogDescription>
              Select a folder for your LocalBrain vault or paste the path directly.
            </DialogDescription>
          </DialogHeader>
          
          <div className="space-y-4 py-4">
            <div className="space-y-2">
              <Label htmlFor="vault-path">Vault Path</Label>
              <div className="flex gap-2">
                <Input
                  id="vault-path"
                  placeholder="/path/to/your/vault or C:\Users\YourName\Documents\LocalBrain"
                  value={pathInput}
                  onChange={(e) => setPathInput(e.target.value)}
                  className="flex-1"
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' && pathInput.trim()) {
                      handleConfirmPath();
                    }
                  }}
                />
                <Button
                  type="button"
                  variant="outline"
                  size="icon"
                  onClick={handleBrowseFolder}
                  disabled={isSelecting}
                  title="Browse for folder"
                >
                  <Folder className="h-4 w-4" />
                </Button>
              </div>
              <p className="text-xs text-muted-foreground">
                You can paste the full path or click the folder icon to browse.
              </p>
            </div>
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={handleCancelPathDialog}
            >
              Cancel
            </Button>
            <Button
              onClick={handleConfirmPath}
              disabled={!pathInput.trim()}
            >
              Confirm Location
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Carousel Overlay */}
      {showCarousel && (
        <div className="absolute inset-0 flex items-center justify-center z-50 p-6">
          {/* Backdrop with blur */}
          <div className="absolute inset-0 bg-background/95 backdrop-blur-2xl" />

          {/* Carousel Card */}
          <Card className="max-w-4xl w-full p-10 shadow-2xl border-2 relative z-10 bg-gradient-to-br from-card to-card/80">
            <AnimatePresence mode="wait">
              {currentSlide === 0 && (
                <motion.div
                  key="slide-0"
                  initial={{ opacity: 0, x: 100 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -100 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center gap-8"
                >
                  <div className="flex-1 space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-blue-500/10 rounded-xl">
                        <Search className="h-8 w-8 text-blue-500" />
                      </div>
                      <h2 className="text-2xl font-semibold">Search Everything</h2>
                    </div>
                    <p className="text-muted-foreground text-lg leading-relaxed">
                      Powerful semantic search across all your connected data sources in one place.
                      Find what you need instantly, no matter where it's stored.
                    </p>
                  </div>
                  <div className="flex-shrink-0 w-64 h-64 bg-gradient-to-br from-blue-500/20 to-blue-600/20 rounded-2xl flex items-center justify-center border-2 border-blue-500/30">
                    <Search className="h-32 w-32 text-blue-500/40" />
                  </div>
                </motion.div>
              )}

              {currentSlide === 1 && (
                <motion.div
                  key="slide-1"
                  initial={{ opacity: 0, x: 100 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -100 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center gap-8"
                >
                  <div className="flex-1 space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-green-500/10 rounded-xl">
                        <Shield className="h-8 w-8 text-green-500" />
                      </div>
                      <h2 className="text-2xl font-semibold">Local & Private</h2>
                    </div>
                    <p className="text-muted-foreground text-lg leading-relaxed">
                      All your data stays on your machine. Complete privacy and control with no cloud dependencies.
                      Your knowledge, your rules.
                    </p>
                  </div>
                  <div className="flex-shrink-0 w-64 h-64 bg-gradient-to-br from-green-500/20 to-green-600/20 rounded-2xl flex items-center justify-center border-2 border-green-500/30">
                    <Shield className="h-32 w-32 text-green-500/40" />
                  </div>
                </motion.div>
              )}

              {currentSlide === 2 && (
                <motion.div
                  key="slide-2"
                  initial={{ opacity: 0, x: 100 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -100 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center gap-8"
                >
                  <div className="flex-1 space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-purple-500/10 rounded-xl">
                        <Boxes className="h-8 w-8 text-purple-500" />
                      </div>
                      <h2 className="text-2xl font-semibold">Smart Connections</h2>
                    </div>
                    <p className="text-muted-foreground text-lg leading-relaxed">
                      AI-powered insights that automatically connect ideas across your knowledge base.
                      Discover relationships you never knew existed.
                    </p>
                  </div>
                  <div className="flex-shrink-0 w-64 h-64 bg-gradient-to-br from-purple-500/20 to-purple-600/20 rounded-2xl flex items-center justify-center border-2 border-purple-500/30">
                    <Boxes className="h-32 w-32 text-purple-500/40" />
                  </div>
                </motion.div>
              )}

              {currentSlide === 3 && (
                <motion.div
                  key="slide-3"
                  initial={{ opacity: 0, x: 100 }}
                  animate={{ opacity: 1, x: 0 }}
                  exit={{ opacity: 0, x: -100 }}
                  transition={{ duration: 0.3 }}
                  className="flex items-center gap-8"
                >
                  <div className="flex-1 space-y-4">
                    <div className="flex items-center gap-3">
                      <div className="p-3 bg-amber-500/10 rounded-xl">
                        <Sparkles className="h-8 w-8 text-amber-500" />
                      </div>
                      <h2 className="text-2xl font-semibold">Intelligent Organization</h2>
                    </div>
                    <p className="text-muted-foreground text-lg leading-relaxed">
                      Automatic organization of your context in an easy-to-browse structure.
                      Files, notes, and data organized the way you think.
                    </p>
                  </div>
                  <div className="flex-shrink-0 w-64 h-64 bg-gradient-to-br from-amber-500/20 to-amber-600/20 rounded-2xl flex items-center justify-center border-2 border-amber-500/30">
                    <Sparkles className="h-32 w-32 text-amber-500/40" />
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {/* Navigation Controls */}
            <div className="flex items-center justify-between mt-8">
              <Button
                variant="outline"
                size="icon"
                onClick={() => setCurrentSlide((prev) => (prev === 0 ? 0 : prev - 1))}
                disabled={currentSlide === 0}
                className="rounded-full"
              >
                <ChevronLeft className="h-5 w-5" />
              </Button>

              <div className="flex gap-2">
                {[0, 1, 2, 3].map((index) => (
                  <button
                    key={index}
                    onClick={() => setCurrentSlide(index)}
                    className={`h-2 rounded-full transition-all ${
                      currentSlide === index
                        ? 'w-8 bg-primary'
                        : 'w-2 bg-muted-foreground/30 hover:bg-muted-foreground/50'
                    }`}
                  />
                ))}
              </div>

              <Button
                onClick={handleNextSlide}
                className="rounded-full"
              >
                {currentSlide === 3 ? "Get Started" : "Next"}
                <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            </div>
          </Card>
        </div>
      )}
    </div>
  );
}
