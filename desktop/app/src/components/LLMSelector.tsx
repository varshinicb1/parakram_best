/**
 * LLMSelector — Visual model selector with free/paid model support.
 * Users can switch models, add API keys, and configure custom providers.
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Brain, ChevronDown, Check, Zap, Globe, Cpu, Sparkles, Star, Lock } from 'lucide-react';

interface Model {
  id: string;
  name: string;
  provider: string;
  category: string;
  context: number;
  free: boolean;
  active: boolean;
}

const CATEGORY_ICONS: Record<string, typeof Brain> = {
  coding: Zap,
  reasoning: Sparkles,
  general: Globe,
  local: Cpu,
  custom: Star,
};

const CATEGORY_COLORS: Record<string, string> = {
  coding: '#00d4ff',
  reasoning: '#d97706',
  general: '#22c55e',
  local: '#8b5cf6',
  custom: '#ec4899',
};

export default function LLMSelector() {
  const [models, setModels] = useState<Model[]>([]);
  const [activeId, setActiveId] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    fetch('http://localhost:8000/api/llm/models')
      .then(r => r.json())
      .then(data => {
        setModels(data.models || []);
        setActiveId(data.active || '');
      })
      .catch(() => {});
  }, []);

  const switchModel = async (id: string) => {
    setLoading(true);
    try {
      const res = await fetch('http://localhost:8000/api/llm/select', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ model_id: id }),
      });
      if (res.ok) {
        setActiveId(id);
        setModels(prev => prev.map(m => ({ ...m, active: m.id === id })));
      }
    } catch (e) {
      console.error('Failed to switch model:', e);
    }
    setLoading(false);
    setIsOpen(false);
  };

  const activeModel = models.find(m => m.id === activeId);
  const activeCat = activeModel?.category || 'general';
  const activeColor = CATEGORY_COLORS[activeCat] || '#00d4ff';
  const ActiveIcon = CATEGORY_ICONS[activeCat] || Brain;

  return (
    <div className="relative">
      <motion.button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 px-3 py-1.5 rounded-lg border text-xs font-bold transition-all shadow-sm"
        style={{
          background: 'var(--bg-secondary)',
          borderColor: 'var(--border)',
          color: 'var(--text-primary)',
        }}
        whileHover={{ scale: 1.02 }}
        whileTap={{ scale: 0.98 }}
      >
        <ActiveIcon size={14} style={{ color: activeColor }} />
        {activeModel?.name || 'Select Model'}
        {activeModel?.free && <span className="px-1.5 py-0.5 rounded-md text-[10px]" style={{ background: '#22c55e15', color: '#22c55e' }}>Free</span>}
        <ChevronDown size={12} className={`transition-transform ${isOpen ? 'rotate-180' : ''}`} style={{ color: 'var(--text-muted)' }} />
      </motion.button>

      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: -5, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: -5, scale: 0.95 }}
            className="absolute top-full mt-2 right-0 w-80 border rounded-xl overflow-hidden z-50 shadow-lg"
            style={{
              background: 'var(--bg-secondary)',
              borderColor: 'var(--border)',
              maxHeight: '400px',
              overflowY: 'auto',
            }}
          >
            <div className="p-3 border-b text-xs font-bold uppercase tracking-wider"
              style={{ borderColor: 'var(--border)', color: 'var(--text-muted)', background: 'var(--bg-primary)' }}>
              Intelligence Core
            </div>

            {/* Group by category */}
            {['coding', 'reasoning', 'general', 'local', 'custom'].map(cat => {
              const catModels = models.filter(m => m.category === cat);
              if (catModels.length === 0) return null;
              const catColor = CATEGORY_COLORS[cat];

              return (
                <div key={cat}>
                  <div className="px-4 py-1.5 text-[10px] font-bold uppercase tracking-wider border-b"
                    style={{ color: catColor, borderColor: 'var(--border)', background: `${catColor}10` }}>
                    {cat} Models
                  </div>
                  {catModels.map((m) => {
                    const Icon = CATEGORY_ICONS[m.category] || Brain;
                    const color = CATEGORY_COLORS[m.category] || '#00d4ff';
                    return (
                      <button
                        key={m.id}
                        onClick={() => switchModel(m.id)}
                        disabled={loading}
                        className="w-full flex items-center gap-3 px-4 py-2.5 text-left transition-colors hover:bg-[var(--bg-primary)] disabled:opacity-50 border-l-2"
                        style={{
                          borderLeftColor: m.active ? color : 'transparent',
                          color: 'var(--text-primary)',
                        }}
                      >
                        <Icon size={14} style={{ color }} />
                        <div className="flex-1 min-w-0">
                          <div className="flex items-center gap-2">
                            <span className="text-xs font-bold truncate">{m.name}</span>
                            {m.free ? (
                              <span className="px-1.5 py-0.5 text-[10px] font-bold rounded-md border"
                                style={{ color: '#22c55e', borderColor: '#22c55e40', background: '#22c55e10' }}>Free</span>
                            ) : (
                              <Lock size={10} style={{ color: 'var(--text-muted)' }} />
                            )}
                          </div>
                          <div className="text-[10px] font-medium mt-0.5" style={{ color: 'var(--text-muted)' }}>
                            {m.provider} · {(m.context / 1000).toFixed(0)}k context
                          </div>
                        </div>
                        {m.active && <Check size={14} style={{ color }} />}
                      </button>
                    );
                  })}
                </div>
              );
            })}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
