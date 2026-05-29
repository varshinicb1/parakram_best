/**
 * BlocksSpace (V2) — Dynamic 202+ golden block browser.
 * Fetches from backend API, categorized, searchable, draggable.
 */
import { useState, useMemo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Sun, Settings, Activity, Monitor, Database, Zap, Lock, Search,
  Component, Mic, Shield, Cpu, Wrench, RefreshCw, Gauge
} from 'lucide-react';

interface BlockEntry {
  id: string;
  name: string;
  category: string;
  libs?: string[];
  bus?: string;
  calibratable?: boolean;
}

const API = 'http://localhost:8000/api/agent';

const CATEGORY_COLORS: Record<string, string> = {
  sensor: '#ef4444', actuator: '#f59e0b', communication: '#8b5cf6',
  display: '#06b6d4', power: '#eab308', storage: '#10b981', security: '#ec4899',
  audio: '#a855f7', freertos: '#f97316', control_blocks: '#14b8a6',
};

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const CATEGORY_ICONS: Record<string, any> = {
  sensor: Sun, actuator: Settings, communication: Activity,
  display: Monitor, power: Zap, storage: Database, security: Lock,
  audio: Mic, freertos: Cpu, control_blocks: Wrench,
};

const CATEGORY_LABELS: Record<string, string> = {
  sensor: 'Sensors', actuator: 'Actuators', communication: 'Communication',
  display: 'Displays', power: 'Power', storage: 'Storage', security: 'Security',
  audio: 'Audio', freertos: 'FreeRTOS', control_blocks: 'Control Logic',
};

const CALIBRATABLE = new Set([
  'ph_sensor', 'tds_meter', 'ec_sensor', 'turbidity', 'thermistor',
  'hx711', 'load_cell_hx710', 'mq_gas_sensor', 'current_acs712', 'voltage_divider'
]);

export default function BlocksSpace() {
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');
  const [blocks, setBlocks] = useState<BlockEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  // Fetch blocks from backend
  useEffect(() => {
    fetchBlocks();
  }, []);

  const fetchBlocks = async () => {
    setLoading(true);
    setError('');
    try {
      const res = await fetch(`${API}/blocks/golden`);
      const data = await res.json();
      const fetched = (data.blocks || []).map((b: any) => ({
        ...b,
        calibratable: CALIBRATABLE.has(b.id),
      }));
      setBlocks(fetched);
    } catch {
      setError('Backend offline — start the backend server first');
      setBlocks([]);
    }
    setLoading(false);
  };

  const categories = useMemo(() => {
    const cats = [...new Set(blocks.map(b => b.category))].sort();
    return ['all', ...cats];
  }, [blocks]);

  const filtered = useMemo(() =>
    blocks.filter((b) => {
      const matchSearch = !search || b.name.toLowerCase().includes(search.toLowerCase()) ||
        b.id.toLowerCase().includes(search.toLowerCase());
      const matchCat = activeCategory === 'all' || b.category === activeCategory;
      return matchSearch && matchCat;
    }),
  [search, activeCategory, blocks]);

  const categoryCount = useMemo(() => {
    const counts: Record<string, number> = {};
    blocks.forEach(b => { counts[b.category] = (counts[b.category] || 0) + 1; });
    return counts;
  }, [blocks]);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="px-8 py-6 border-b bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
              <Component size={24} />
              Hardware Block Library
            </h1>
            <p className="text-sm font-medium mt-1" style={{ color: 'var(--text-muted)' }}>
              {blocks.length} verified components • MISRA C:2012 compliant • Drag to canvas
            </p>
          </div>
          <button onClick={fetchBlocks}
            className="flex items-center gap-2 px-4 py-2 border rounded-lg text-xs font-semibold hover:bg-[var(--bg-primary)] transition-colors"
            style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
            <RefreshCw size={14} className={loading ? 'animate-spin' : ''} /> Refresh
          </button>
        </div>

        <div className="mt-6 space-y-4 max-w-full">
          {/* Search */}
          <div className="relative max-w-xl">
            <Search size={16} className="absolute left-4 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
            <input type="text" value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder="Search 202+ blocks by name or ID..."
              className="w-full bg-[var(--bg-primary)] border rounded-xl pl-11 pr-4 py-3 text-sm font-medium outline-none focus:border-[var(--text-primary)] transition-colors shadow-sm"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
          </div>

          {/* Category pills */}
          <div className="flex items-center gap-2 flex-wrap">
            {categories.map((cat) => {
              const count = cat === 'all' ? blocks.length : (categoryCount[cat] || 0);
              return (
                <button key={cat} onClick={() => setActiveCategory(cat)}
                  className="px-4 py-1.5 rounded-full text-xs font-semibold transition-all border flex items-center gap-1.5"
                  style={{
                    background: activeCategory === cat ? 'var(--text-primary)' : 'var(--bg-primary)',
                    color: activeCategory === cat ? 'var(--bg-primary)' : 'var(--text-secondary)',
                    borderColor: activeCategory === cat ? 'var(--text-primary)' : 'var(--border)',
                  }}>
                  {cat === 'all' ? 'All' : (CATEGORY_LABELS[cat] || cat)}
                  <span className="opacity-60">{count}</span>
                </button>
              );
            })}
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-y-auto p-8 bg-[var(--bg-tertiary)]">
        {loading ? (
          <div className="flex items-center justify-center h-full">
            <div className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>Loading blocks from backend...</div>
          </div>
        ) : error ? (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <p className="text-sm" style={{ color: 'var(--error)' }}>{error}</p>
            <button onClick={fetchBlocks}
              className="px-4 py-2 rounded-lg text-sm font-semibold"
              style={{ background: 'var(--text-primary)', color: 'var(--bg-primary)' }}>
              Retry
            </button>
          </div>
        ) : (
          <>
            <div className="grid grid-cols-2 md:grid-cols-3 xl:grid-cols-4 2xl:grid-cols-5 gap-4">
              <AnimatePresence>
                {filtered.map((block, i) => (
                  <motion.div key={block.id}
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    exit={{ opacity: 0, scale: 0.95 }}
                    transition={{ delay: Math.min(i * 0.01, 0.3), duration: 0.15 }}
                    className="bg-[var(--bg-primary)] border rounded-xl p-5 cursor-grab active:cursor-grabbing transition-shadow hover:shadow-md hover:border-[var(--text-muted)] relative"
                    style={{ borderColor: 'var(--border)' }}
                    draggable
                    onDragStart={(e) => {
                      const de = e as unknown as React.DragEvent;
                      de.dataTransfer?.setData('application/parakram-block', JSON.stringify(block));
                    }}
                  >
                    {/* Calibration badge */}
                    {block.calibratable && (
                      <div className="absolute top-2 right-2 px-1.5 py-0.5 rounded text-[9px] font-bold uppercase tracking-wider"
                        style={{ background: 'var(--warning)', color: '#000', opacity: 0.9 }}>
                        <Gauge size={8} className="inline mr-0.5 -mt-px" /> Cal
                      </div>
                    )}

                    <div className="flex items-center gap-3 mb-3">
                      <div className="w-8 h-8 rounded-lg flex items-center justify-center border bg-[var(--bg-secondary)]"
                        style={{ borderColor: 'var(--border)' }}>
                        {(() => {
                          const Icon = CATEGORY_ICONS[block.category] || Component;
                          return <Icon size={16} strokeWidth={2} style={{ color: CATEGORY_COLORS[block.category] || 'var(--text-primary)' }} />;
                        })()}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-bold truncate" style={{ color: 'var(--text-primary)' }}>{block.name}</div>
                        <div className="text-[10px] font-semibold uppercase tracking-wider mt-0.5"
                          style={{ color: CATEGORY_COLORS[block.category] }}>
                          {CATEGORY_LABELS[block.category] || block.category}
                        </div>
                      </div>
                    </div>

                    {/* Bus/Protocol badge */}
                    {block.bus && (
                      <span className="text-[9px] font-bold uppercase tracking-wider px-2 py-0.5 rounded border"
                        style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
                        {block.bus}
                      </span>
                    )}

                    <p className="text-[11px] font-mono mt-2 truncate" style={{ color: 'var(--text-muted)' }}>{block.id}</p>
                  </motion.div>
                ))}
              </AnimatePresence>
            </div>

            {filtered.length === 0 && (
              <div className="text-center py-12">
                <p className="text-sm" style={{ color: 'var(--text-muted)' }}>No blocks match your search</p>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
