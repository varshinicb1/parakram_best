/**
 * Global application state — Zustand store.
 * Manages active space, projects, theme, devices, and build status.
 */
import { create } from 'zustand';

export type Space = 'home' | 'workspace' | 'blocks' | 'devices' | 'telemetry' | 'settings' | 'debug' | 'simulator' | 'verification' | 'admin' | 'auth' | 'installer' | 'extensions' | 'calibration' | 'designer' | 'blockly';
export type Theme = 'dark-lab' | 'cyberpunk' | 'midnight' | 'solarized' | 'retro' | 'glass';


export interface Device {
  port: string;
  name: string;
  board: string;
  connected: boolean;
}

export interface BuildStatus {
  stage: string;
  progress: number;        // 0-100
  message: string;
  isRunning: boolean;
  result?: 'success' | 'error' | null;
}

interface AppState {
  // Navigation
  activeSpace: Space;
  setActiveSpace: (space: Space) => void;
  sidebarExpanded: boolean;
  toggleSidebar: () => void;

  // Theme
  theme: Theme;
  setTheme: (theme: Theme) => void;

  // Devices
  devices: Device[];
  setDevices: (devices: Device[]) => void;

  // Build
  buildStatus: BuildStatus;
  setBuildStatus: (status: Partial<BuildStatus>) => void;

  // Prompt
  promptHistory: string[];
  addPrompt: (prompt: string) => void;

  // Canvas state
  showInspector: boolean;
  setShowInspector: (show: boolean) => void;
  showTerminal: boolean;
  setShowTerminal: (show: boolean) => void;
}

export const useAppStore = create<AppState>((set) => ({
  // Navigation
  activeSpace: 'home',
  setActiveSpace: (space) => set({ activeSpace: space }),
  sidebarExpanded: false,
  toggleSidebar: () => set((s) => ({ sidebarExpanded: !s.sidebarExpanded })),

  // Theme
  theme: 'dark-lab',
  setTheme: (theme) => {
    const themeMap: Record<Theme, string> = {
      'dark-lab': '',
      cyberpunk: 'cyberpunk',
      midnight: 'midnight',
      solarized: 'solarized',
      retro: 'retro',
      glass: 'glass',
    };
    document.documentElement.setAttribute('data-theme', themeMap[theme]);
    set({ theme });
  },

  // Devices
  devices: [],
  setDevices: (devices) => set({ devices }),

  // Build
  buildStatus: { stage: '', progress: 0, message: 'Ready', isRunning: false, result: null },
  setBuildStatus: (status) => set((s) => ({ buildStatus: { ...s.buildStatus, ...status } })),

  // Prompt
  promptHistory: [],
  addPrompt: (prompt) => set((s) => ({ promptHistory: [prompt, ...s.promptHistory].slice(0, 50) })),

  // Canvas
  showInspector: false,
  setShowInspector: (show) => set({ showInspector: show }),
  showTerminal: false,
  setShowTerminal: (show) => set({ showTerminal: show }),
}));
