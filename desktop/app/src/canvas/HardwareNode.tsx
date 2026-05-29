/**
 * HardwareNode — Premium glassmorphic block node for the canvas.
 * Shows category color, name, status, and animated handles.
 */
import { memo } from 'react';
import { Handle, Position, type NodeProps } from '@xyflow/react';
import {
  Cpu, Activity, Sun, Settings, Zap, Lock,
  Volume2, Database, Monitor
} from 'lucide-react';

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CATEGORY_CONFIG: Record<string, { color: string; icon: any; label: string }> = {
  sensor:        { color: '#ef4444', icon: Sun,         label: 'Sensor' },
  sensors:       { color: '#ef4444', icon: Sun,         label: 'Sensor' },
  actuator:      { color: '#f59e0b', icon: Settings,   label: 'Actuator' },
  actuators:     { color: '#f59e0b', icon: Settings,   label: 'Actuator' },
  communication: { color: '#8b5cf6', icon: Activity,      label: 'Comm' },
  display:       { color: '#06b6d4', icon: Monitor,          label: 'Display' },
  storage:       { color: '#10b981', icon: Database,  label: 'Storage' },
  power:         { color: '#eab308', icon: Zap,        label: 'Power' },
  security:      { color: '#ec4899', icon: Lock,  label: 'Security' },
  audio:         { color: '#14b8a6', icon: Volume2, label: 'Audio' },
  logic:         { color: '#6366f1', icon: Settings,   label: 'Logic' },
  boards:        { color: '#6366f1', icon: Cpu,     label: 'MCU' },
  freertos:      { color: '#a855f7', icon: Settings,   label: 'RTOS' },
  control_blocks:{ color: '#6366f1', icon: Settings,   label: 'Control' },
};

function HardwareNode({ data, selected }: NodeProps) {
  const nodeData = data as Record<string, unknown>;
  const name = (nodeData.name as string) || 'Block';
  const category = (nodeData.category as string) || 'logic';
  const config = CATEGORY_CONFIG[category] || CATEGORY_CONFIG.logic;
  const Icon = config.icon;
  const color = config.color;

  return (
    <div
      className="relative group"
      style={{
        minWidth: 180,
        borderRadius: 'var(--radius-md)',
        background: 'var(--bg-glass)',
        backdropFilter: 'blur(4px)',
        border: selected ? `1px solid ${color}` : '1px solid var(--border)',
        boxShadow: selected ? `0 0 16px ${color}33` : 'var(--shadow-sm)',
        transition: 'all 0.2s ease',
      }}
    >
      {/* Input handle */}
      <Handle
        type="target"
        position={Position.Left}
        style={{
          width: 8, height: 8,
          background: color,
          border: '1px solid var(--bg-primary)',
          borderRadius: '0%',
        }}
      />

      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2"
        style={{
          background: `linear-gradient(135deg, ${color}15, transparent)`,
          borderBottom: '1px solid var(--border)',
        }}
      >
        <div className="flex items-center justify-center w-7 h-7 rounded-[2px]"
          style={{ background: `${color}20` }}>
          <Icon size={14} style={{ color }} strokeWidth={2.5} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold truncate" style={{ color: 'var(--text-primary)' }}>
            {name}
          </div>
          <div className="text-[9px] font-medium uppercase tracking-wider" style={{ color }}>
            {config.label}
          </div>
        </div>
      </div>

      {/* Status */}
      <div className="px-3 py-2 flex items-center gap-1.5 uppercase tracking-widest">
        <div className="w-1.5 h-1.5 animate-pulse" style={{ background: 'var(--accent)', boxShadow: '0 0 8px var(--accent)' }} />
        <span className="text-[9px]" style={{ color: 'var(--accent)' }}>SYS.ONLINE</span>
      </div>

      {/* Output handle */}
      <Handle
        type="source"
        position={Position.Right}
        style={{
          width: 8, height: 8,
          background: color,
          border: '1px solid var(--bg-primary)',
          borderRadius: '0%',
        }}
      />
    </div>
  );
}

export default memo(HardwareNode);
