/**
 * Sidebar — Complete navigation for all 14 spaces.
 * Clean icon sidebar with tooltips and active indicators.
 */
import { motion } from 'framer-motion';
import { useAppStore, type Space } from '../stores/appStore';
import {
  Home, Folder, Component, Cpu, Activity, Settings, Hexagon,
  MonitorPlay, Bug, ShieldCheck, Gauge, Package, LogIn, Puzzle, PenTool, Blocks
} from 'lucide-react';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const mainSpaces: { id: Space; icon: any; label: string }[] = [
  { id: 'home', icon: Home, label: 'Home' },
  { id: 'workspace', icon: Folder, label: 'Projects' },
  { id: 'blocks', icon: Component, label: 'Blocks (202+)' },
  { id: 'designer', icon: PenTool, label: 'Visual Designer' },
  { id: 'blockly', icon: Blocks, label: 'Blockly Editor' },
  { id: 'simulator', icon: MonitorPlay, label: 'Simulator' },
  { id: 'devices', icon: Cpu, label: 'Devices' },
  { id: 'telemetry', icon: Activity, label: 'Telemetry' },
  { id: 'debug', icon: Bug, label: 'Debug' },
  { id: 'calibration', icon: Gauge, label: 'Calibration' },
  { id: 'verification', icon: ShieldCheck, label: 'Verification' },
];

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const bottomSpaces: { id: Space; icon: any; label: string }[] = [
  { id: 'extensions', icon: Puzzle, label: 'Extensions' },
  { id: 'installer', icon: Package, label: 'Installer' },
  { id: 'settings', icon: Settings, label: 'Settings' },
  { id: 'auth', icon: LogIn, label: 'Account' },
];

export default function Sidebar() {
  const activeSpace = useAppStore((s) => s.activeSpace);
  const setActiveSpace = useAppStore((s) => s.setActiveSpace);
  const theme = useAppStore((s) => s.theme);

  const renderNavButton = ({ id, icon: Icon, label }: { id: Space; icon: typeof Home; label: string }) => {
    const isActive = activeSpace === id;
    return (
      <motion.button
        key={id}
        onClick={() => setActiveSpace(id)}
        className={`relative flex items-center justify-center w-11 h-11 rounded-xl transition-all duration-200 group ${
          isActive 
            ? 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] shadow-sm' 
            : 'text-[var(--text-secondary)] hover:bg-[var(--bg-elevated)] hover:text-[var(--text-primary)]'
        }`}
        whileHover={{ scale: isActive ? 1 : 1.05 }}
        whileTap={{ scale: 0.95 }}
        title={label}
      >
        <Icon size={20} />
        {isActive && (
          <motion.div
            className="absolute -left-1 w-1 h-5 rounded-full"
            style={{ background: 'var(--text-primary)' }}
            layoutId="sidebar-indicator"
            transition={{ type: 'tween', duration: 0.15 }}
          />
        )}
        {/* Tooltip */}
        <span className="absolute left-14 px-3 py-1.5 rounded-lg border text-xs font-semibold tracking-wide whitespace-nowrap opacity-0 pointer-events-none group-hover:opacity-100 transition-opacity z-50 shadow-md"
          style={{ background: 'var(--bg-elevated)', color: 'var(--text-primary)', borderColor: 'var(--border)' }}>
          {label}
        </span>
      </motion.button>
    );
  };

  return (
    <motion.aside
      className="flex flex-col items-center py-4 gap-1 border-r shrink-0"
      style={{
        width: 'var(--sidebar-width)',
        background: 'var(--bg-secondary)',
        borderColor: 'var(--border)',
      }}
      initial={{ x: -64 }}
      animate={{ x: 0 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {/* Logo */}
      <div className="flex items-center justify-center w-12 h-12 mb-4 cursor-pointer"
        onClick={() => setActiveSpace('home')}
        title="Parakram — AI Firmware Studio"
      >
        <Hexagon size={32} style={{ color: 'var(--accent)', filter: 'drop-shadow(0 0 8px var(--accent))' }} />
      </div>

      {/* Main nav */}
      <nav className="flex flex-col gap-1 flex-1">
        {mainSpaces.map(renderNavButton)}
      </nav>

      {/* Bottom nav */}
      <div className="flex flex-col gap-1 border-t pt-2" style={{ borderColor: 'var(--border)' }}>
        {bottomSpaces.map(renderNavButton)}
      </div>

      {/* Theme dot */}
      <div className="mt-2">
        <div className="w-3 h-3 rounded-full" style={{ background: 'var(--accent)' }} title={`Theme: ${theme}`} />
      </div>
    </motion.aside>
  );
}
