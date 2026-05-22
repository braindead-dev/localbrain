'use client';

import { useState } from "react";
import { motion, AnimatePresence } from "motion/react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Brain, FolderOpen, Key, Plug, ArrowRight, ChevronRight } from "lucide-react";
import { api } from "../lib/api";
import { toast } from "sonner";

const AVAILABLE_CONNECTORS = [
  { id: 'gmail', name: 'Gmail', description: 'Emails' },
  { id: 'calendar', name: 'Google Calendar', description: 'Events' },
  { id: 'github', name: 'GitHub', description: 'Activity' },
  { id: 'notion', name: 'Notion', description: 'Pages' },
  { id: 'reddit', name: 'Reddit', description: 'Posts' },
  { id: 'twitter', name: 'X / Twitter', description: 'Tweets' },
  { id: 'imessage', name: 'iMessage', description: 'Messages' },
];

interface Props {
  onComplete: () => void;
}

type Step = 'welcome' | 'vault' | 'apikey' | 'connectors' | 'done';
const STEPS: Step[] = ['welcome', 'vault', 'apikey', 'connectors', 'done'];

export function SetupWalkthrough({ onComplete }: Props) {
  const [step, setStep] = useState<Step>('welcome');
  const [direction, setDirection] = useState(1);

  // Vault step
  const [vaultPath, setVaultPath] = useState(`${typeof window !== 'undefined' ? '' : '~'}/LocalBrain`);
  const [vaultLoading, setVaultLoading] = useState(false);

  // API key step
  const [anthropicKey, setAnthropicKey] = useState('');
  const [keyLoading, setKeyLoading] = useState(false);


  const navigate = (next: Step) => {
    const curr = STEPS.indexOf(step);
    const nextIdx = STEPS.indexOf(next);
    setDirection(nextIdx > curr ? 1 : -1);
    setStep(next);
  };

  const nextStep = () => {
    const idx = STEPS.indexOf(step);
    if (idx < STEPS.length - 1) navigate(STEPS[idx + 1]);
  };

  // ── Vault ──────────────────────────────────────────────────────────────────
  const handleBrowse = async () => {
    const selected = await (window as any).electron?.selectDirectory();
    if (selected) setVaultPath(selected);
  };

  const handleSaveVault = async () => {
    if (!vaultPath.trim()) { toast.error('Please enter a vault path'); return; }
    setVaultLoading(true);
    try {
      const res = await api.updateConfig({ vault_path: vaultPath.trim(), create_vault: true } as any);
      if (res.success) nextStep();
      else toast.error('Failed to save vault path');
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to save vault path');
    } finally {
      setVaultLoading(false);
    }
  };

  // ── API Key ────────────────────────────────────────────────────────────────
  const handleSaveKey = async () => {
    if (!anthropicKey.trim()) { nextStep(); return; } // skip if empty
    setKeyLoading(true);
    try {
      await api.updateConfig({ anthropic_api_key: anthropicKey.trim() } as any);
      nextStep();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to save API key');
    } finally {
      setKeyLoading(false);
    }
  };

  // ── Render ─────────────────────────────────────────────────────────────────
  const variants = {
    enter: (d: number) => ({ x: d > 0 ? 60 : -60, opacity: 0 }),
    center: { x: 0, opacity: 1 },
    exit: (d: number) => ({ x: d > 0 ? -60 : 60, opacity: 0 }),
  };

  return (
    <div className="fixed inset-0 z-[100] bg-background flex items-center justify-center">
      <div className="w-full max-w-lg px-4">
        {/* Step dots */}
        {step !== 'welcome' && step !== 'done' && (
          <div className="flex justify-center gap-2 mb-8">
            {(['vault', 'apikey', 'connectors'] as Step[]).map((s, i) => (
              <div
                key={s}
                className={`h-1.5 rounded-full transition-all duration-300 ${
                  STEPS.indexOf(step) > STEPS.indexOf(s)
                    ? 'w-6 bg-primary'
                    : step === s
                    ? 'w-6 bg-primary'
                    : 'w-3 bg-border'
                }`}
              />
            ))}
          </div>
        )}

        <AnimatePresence mode="wait" custom={direction}>
          <motion.div
            key={step}
            custom={direction}
            variants={variants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.2, ease: 'easeOut' }}
          >
            {/* ── WELCOME ── */}
            {step === 'welcome' && (
              <div className="text-center space-y-6">
                <div className="flex justify-center">
                  <div className="p-5 bg-primary/10 rounded-3xl">
                    <Brain className="h-16 w-16 text-primary" />
                  </div>
                </div>
                <div className="space-y-2">
                  <h1 className="text-3xl font-bold">Welcome to LocalBrain</h1>
                  <p className="text-muted-foreground text-lg">
                    Your personal, local-first AI knowledge base.
                  </p>
                  <p className="text-muted-foreground text-sm pt-1">
                    Let's get you set up in a few quick steps.
                  </p>
                </div>
                <Button size="lg" className="w-full" onClick={nextStep}>
                  Get Started <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            )}

            {/* ── VAULT ── */}
            {step === 'vault' && (
              <div className="space-y-6">
                <div className="space-y-1">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-primary/10 rounded-lg"><FolderOpen className="h-5 w-5 text-primary" /></div>
                    <h2 className="text-xl font-semibold">Choose your vault location</h2>
                  </div>
                  <p className="text-muted-foreground text-sm">
                    LocalBrain stores your knowledge as plain markdown files. Choose a folder — it'll be created if it doesn't exist.
                  </p>
                </div>
                <div className="flex gap-2">
                  <Input
                    value={vaultPath}
                    onChange={e => setVaultPath(e.target.value)}
                    placeholder="~/LocalBrain"
                    className="flex-1"
                  />
                  <Button variant="outline" onClick={handleBrowse}>Browse</Button>
                </div>
                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1" onClick={() => navigate('apikey')}>Skip</Button>
                  <Button className="flex-1" onClick={handleSaveVault} disabled={vaultLoading}>
                    {vaultLoading ? 'Saving...' : 'Continue'} <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {/* ── API KEY ── */}
            {step === 'apikey' && (
              <div className="space-y-6">
                <div className="space-y-1">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="p-2 bg-primary/10 rounded-lg"><Key className="h-5 w-5 text-primary" /></div>
                    <h2 className="text-xl font-semibold">Anthropic API Key</h2>
                  </div>
                  <p className="text-muted-foreground text-sm">
                    LocalBrain uses Claude (Haiku) for agentic search and intelligent ingestion. Add your Anthropic API key to enable these features.
                  </p>
                </div>
                <div className="space-y-2">
                  <Input
                    type="password"
                    value={anthropicKey}
                    onChange={e => setAnthropicKey(e.target.value)}
                    placeholder="sk-ant-api03-..."
                  />
                  <button
                    className="text-xs text-primary hover:underline underline-offset-2"
                    onClick={() => (window as any).electron?.openExternal('https://console.anthropic.com/settings/keys')}
                  >
                    Get an API key from console.anthropic.com →
                  </button>
                </div>
                <div className="flex gap-3">
                  <Button variant="outline" className="flex-1" onClick={() => navigate('connectors')}>Skip for now</Button>
                  <Button className="flex-1" onClick={handleSaveKey} disabled={keyLoading}>
                    {keyLoading ? 'Saving...' : 'Continue'} <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {/* ── CONNECTORS ── */}
            {step === 'connectors' && (
              <div className="space-y-5">
                <div>
                  <div className="flex items-center gap-3 mb-2">
                    <div className="p-2 bg-primary/10 rounded-lg"><Plug className="h-5 w-5 text-primary" /></div>
                    <h2 className="text-xl font-semibold">Connect your apps</h2>
                  </div>
                  <p className="text-muted-foreground text-sm">
                    LocalBrain syncs your data from the services below. After setup, head to the Connections tab to sign in to each one.
                  </p>
                </div>

                <div className="grid grid-cols-2 gap-2">
                  {AVAILABLE_CONNECTORS.map(c => (
                    <div key={c.id} className="flex items-center gap-3 rounded-lg border border-border px-3 py-2.5 bg-muted/20">
                      <div className="w-2 h-2 rounded-full bg-primary/40 flex-shrink-0" />
                      <div className="min-w-0">
                        <p className="text-sm font-medium truncate">{c.name}</p>
                        <p className="text-xs text-muted-foreground">{c.description}</p>
                      </div>
                    </div>
                  ))}
                </div>

                <div className="flex gap-3 pt-1">
                  <Button variant="outline" className="flex-1" onClick={nextStep}>Skip</Button>
                  <Button className="flex-1" onClick={nextStep}>
                    Continue <ChevronRight className="ml-1 h-4 w-4" />
                  </Button>
                </div>
              </div>
            )}

            {/* ── DONE ── */}
            {step === 'done' && (
              <div className="text-center space-y-6">
                <div className="flex justify-center">
                  <div className="p-5 bg-green-500/10 rounded-3xl">
                    <Plug className="h-16 w-16 text-green-500" />
                  </div>
                </div>
                <div className="space-y-2">
                  <h1 className="text-3xl font-bold">You're all set!</h1>
                  <p className="text-muted-foreground">
                    Head to the Connections tab to sign in to your apps, or start exploring your vault right away.
                  </p>
                </div>
                <Button size="lg" className="w-full" onClick={onComplete}>
                  Go to LocalBrain <ArrowRight className="ml-2 h-4 w-4" />
                </Button>
              </div>
            )}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}
