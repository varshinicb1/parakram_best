/**
 * PromptBar — ChatGPT-style input bar at top of workspace.
 * Sends prompts to /api/agent/build and populates canvas with result.
 */
import { useState, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Sparkles, Play, Zap, Activity, Loader2 } from 'lucide-react';
import { useAppStore } from '../stores/appStore';
import type { Node } from '@xyflow/react';

const API_BASE = 'http://localhost:8000';

const PIPELINE_STAGES = [
  { key: 'parse', label: 'PARSING', icon: <Sparkles size={12} /> },
  { key: 'resolve', label: 'RESOLVING', icon: <Zap size={12} /> },
  { key: 'generate', label: 'GENERATING', icon: <Play size={12} /> },
  { key: 'compile', label: 'COMPILING', icon: <Activity size={12} /> },
];

interface Props {
  onGraphGenerated: (nodes: Node[]) => void;
}

export default function PromptBar({ onGraphGenerated }: Props) {
  const [prompt, setPrompt] = useState('');
  const [isBuilding, setIsBuilding] = useState(false);
  const [activeStage, setActiveStage] = useState(-1);
  const [result, setResult] = useState<string | null>(null);
  const addPrompt = useAppStore((s) => s.addPrompt);
  const setBuildStatus = useAppStore((s) => s.setBuildStatus);
  const setShowTerminal = useAppStore((s) => s.setShowTerminal);

  const handleBuild = useCallback(async () => {
    if (!prompt.trim() || isBuilding) return;
    setIsBuilding(true);
    setResult(null);
    addPrompt(prompt);
    setBuildStatus({ isRunning: true, message: 'Building...', stage: 'parse', progress: 0 });

    // Animate through stages
    for (let i = 0; i < PIPELINE_STAGES.length; i++) {
      setActiveStage(i);
      setBuildStatus({
        stage: PIPELINE_STAGES[i].key,
        message: PIPELINE_STAGES[i].label + '...',
        progress: ((i + 1) / PIPELINE_STAGES.length) * 100,
      });
      await new Promise((r) => setTimeout(r, 400));
    }

    try {
      const resp = await fetch(`${API_BASE}/api/agent/build`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt, board: 'esp32dev', verify: false }),
      });

      if (resp.ok) {
        const data = await resp.json();
        const nodes: Node[] = (data.graph?.nodes || []).map((n: Record<string, unknown>, i: number) => ({
          id: n.id as string || `node_${i}`,
          type: 'hardwareNode',
          position: (n.position as { x: number; y: number }) || { x: 150 + (i % 4) * 260, y: 100 + Math.floor(i / 4) * 200 },
          data: {
            name: n.name as string || n.block_id as string || 'Unknown',
            category: n.category as string || 'logic',
            blockId: n.block_id as string,
            config: n.config as Record<string, unknown> || {},
          },
        }));
        onGraphGenerated(nodes);
        setResult(`SYS.OK // ${data.blocks?.length || 0} BLOCKS GENERATED`);
        setBuildStatus({ isRunning: false, result: 'success', message: 'BUILD COMPLETE' });
      } else {
        setResult('SYS.ERR // BUILD FAILED');
        setBuildStatus({ isRunning: false, result: 'error', message: 'BUILD FAILED' });
      }
    } catch {
      setResult('SYS.WARN // BACKEND DISCONNECTED. DEMO MODE ACTIVE.');
      // Demo mode: generate fake nodes
      const demoNodes: Node[] = [
        { id: 'demo_1', type: 'hardwareNode', position: { x: 400, y: 200 },
          data: { name: 'ESP32', category: 'boards', blockId: 'esp32_manifest' } },
        { id: 'demo_2', type: 'hardwareNode', position: { x: 150, y: 120 },
          data: { name: 'BME280', category: 'sensor', blockId: 'bme280' } },
        { id: 'demo_3', type: 'hardwareNode', position: { x: 650, y: 120 },
          data: { name: 'WiFi', category: 'communication', blockId: 'wifi_station' } },
        { id: 'demo_4', type: 'hardwareNode', position: { x: 650, y: 320 },
          data: { name: 'MQTT', category: 'communication', blockId: 'mqtt_client' } },
        { id: 'demo_5', type: 'hardwareNode', position: { x: 150, y: 320 },
          data: { name: 'OLED', category: 'display', blockId: 'i2c_oled' } },
      ];
      onGraphGenerated(demoNodes);
      setBuildStatus({ isRunning: false, result: 'success', message: 'DEMO MODE_ACTIVE' });
    }

    setActiveStage(-1);
    setIsBuilding(false);
    setPrompt('');
  }, [prompt, isBuilding, addPrompt, setBuildStatus, onGraphGenerated, setShowTerminal]);

  return (
    <div className="border-b px-4 py-2.5" style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
      <div className="flex items-center gap-3 max-w-4xl mx-auto">
        <Sparkles size={18} style={{ color: 'var(--accent)', flexShrink: 0 }} />
        <input
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleBuild()}
          placeholder="Describe your system architecture..."
          disabled={isBuilding}
          className="flex-1 bg-transparent outline-none text-sm font-medium placeholder-[var(--text-muted)]"
          style={{ color: 'var(--text-primary)' }}
        />

        {/* Pipeline progress pills */}
        <AnimatePresence>
          {isBuilding && (
            <motion.div
              initial={{ opacity: 0, width: 0 }}
              animate={{ opacity: 1, width: 'auto' }}
              exit={{ opacity: 0, width: 0 }}
              className="flex items-center gap-1"
            >
              {PIPELINE_STAGES.map((stage, i) => (
                <span
                  key={stage.key}
                  className="flex items-center gap-1.5 px-3 py-1 rounded-full border text-[10px] font-bold uppercase tracking-wider transition-all"
                  style={{
                    background: i <= activeStage ? 'var(--accent-subtle)' : 'transparent',
                    color: i <= activeStage ? 'var(--accent)' : 'var(--text-muted)',
                    borderColor: i <= activeStage ? 'var(--accent)' : 'transparent',
                  }}
                >
                  {stage.icon}
                </span>
              ))}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Result badge */}
        {result && !isBuilding && (
          <motion.span
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            className="text-[10px] font-bold tracking-wider uppercase px-2 py-1 rounded-md border whitespace-nowrap shadow-sm"
            style={{
              background: result.includes('ERR') ? 'rgba(239, 68, 68, 0.1)' : 'rgba(14, 165, 233, 0.1)',
              color: result.includes('ERR') ? 'var(--error)' : 'var(--accent)',
              borderColor: result.includes('ERR') ? 'var(--error)' : 'var(--accent)',
            }}
          >
            {result}
          </motion.span>
        )}

        <motion.button
          onClick={handleBuild}
          disabled={isBuilding || !prompt.trim()}
          className="flex items-center gap-2 px-4 py-2 rounded-lg border text-xs font-semibold text-white transition-colors disabled:opacity-50 shadow-sm"
          style={{ background: 'var(--accent)', borderColor: 'var(--accent)' }}
          whileHover={{ scale: 1.05 }}
          whileTap={{ scale: 0.95 }}
        >
          {isBuilding ? <Loader2 size={14} className="animate-spin" /> : <><Sparkles size={14} /> Execute</>}
        </motion.button>
      </div>
    </div>
  );
}
