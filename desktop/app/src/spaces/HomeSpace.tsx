/**
 * HomeSpace (V4 Professional AI-First) — The absolute core of Parakram.
 * This is an Elite Hardware Command Center, not a passive dashboard.
 * Designed with standard, professional SaaS aesthetics.
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Rocket, Cpu, Terminal, Layers, Lightbulb, Play, GitBranch, Share2, Search, Clock,
  PenTool, Blocks, Gauge
} from 'lucide-react';
import { useAppStore, type Space } from '../stores/appStore';
import { useLiveQuery } from 'dexie-react-hooks';
import { db } from '../lib/db';

interface ProjectTemplate {
  id: string;
  title: string;
  description: string;
  board: string;
  tags: string[];
  estimated_cost: number;
}

const API = 'http://localhost:8000/api';

export default function HomeSpace() {
  const setSpace = useAppStore((s) => s.setActiveSpace);
  const [templates, setTemplates] = useState<ProjectTemplate[]>([]);
  const [prompt, setPrompt] = useState('');
  const [generating, setGenerating] = useState(false);
  const [planResult, setPlanResult] = useState<any>(null);

  useEffect(() => {
    fetch(`${API}/agent/gallery/templates`).then(r => r.json()).then(d => setTemplates(d.templates || [])).catch(() => {});
  }, []);

  const generatePlan = async () => {
    if (!prompt.trim()) return;
    setGenerating(true);
    setPlanResult(null); // Clear previous
    try {
      const res = await fetch(`${API}/analysis/planner/generate`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ prompt: prompt.trim() }),
      });
      const data = await res.json();
      setPlanResult(data.plan || data);
    } catch { /* ignore */ }
    setGenerating(false);
  };

  const saveProjectToDB = async () => {
    if (!planResult) return;
    try {
      await db.projects.add({
        id: crypto.randomUUID(),
        name: planResult.project_name || 'New Project',
        description: prompt.substring(0, 100),
        board: planResult.components?.[0]?.name || 'ESP32',
        createdAt: new Date().toISOString(),
        blocks: planResult.components || [],
      });
      setSpace('workspace');
    } catch (e) {
      console.error("Failed to save project", e);
    }
  };

  const recentProjects = useLiveQuery(() => db.projects.orderBy('createdAt').reverse().limit(6).toArray(), []);

  const workflows: {
    category: string;
    actions: { label: string; icon: any; color: string; space?: Space }[];
  }[] = [
    {
      category: 'Build & Architect',
      actions: [
        { label: 'Generate System', icon: Lightbulb, color: 'var(--accent)' },
        { label: 'Blank Project', icon: Rocket, color: 'var(--text-primary)', space: 'workspace' },
        { label: 'Import Repo', icon: GitBranch, color: 'var(--text-primary)', space: 'workspace' },
      ]
    },
    {
      category: 'Design & Program',
      actions: [
        { label: 'Visual Designer', icon: PenTool, color: 'var(--text-primary)', space: 'designer' as const },
        { label: 'Blockly Editor', icon: Blocks, color: 'var(--text-primary)', space: 'blockly' as const },
        { label: 'Calibration', icon: Gauge, color: 'var(--text-primary)', space: 'calibration' as const },
      ]
    },
    {
      category: 'Test & Validate',
      actions: [
        { label: 'Run Simulator', icon: Play, color: 'var(--text-primary)', space: 'simulator' as const },
        { label: 'Debug Serial', icon: Terminal, color: 'var(--text-primary)', space: 'debug' as const },
      ]
    },
    {
      category: 'Deploy',
      actions: [
        { label: 'Flash Device', icon: Cpu, color: 'var(--text-primary)', space: 'devices' as const },
        { label: 'Live Telemetry', icon: Share2, color: 'var(--text-primary)', space: 'telemetry' as const },
      ]
    }
  ];

  return (
    <div className="flex-1 overflow-y-auto overflow-x-hidden relative z-10 p-6 md:p-10" style={{ background: 'var(--bg-primary)' }}>
      <div className="max-w-[1400px] w-full mx-auto pt-8 md:pt-16 space-y-16 relative z-20">

        {/* Professional Hero Section */}
        <div className="space-y-6 text-center md:text-left">
          <h1 className="text-3xl md:text-5xl font-bold tracking-tight" style={{ color: 'var(--text-primary)' }}>
            Hardware System Architect
          </h1>
          <p className="text-base max-w-2xl" style={{ color: 'var(--text-muted)' }}>
            Describe your project requirements in plain english. Parakram AI will instantly generate the architecture, BOM, and firmware scaffolding.
          </p>

          <div className="mt-12">
            <div className="flex items-center gap-3 p-2 border rounded-2xl transition-colors shadow-sm bg-[var(--bg-secondary)]"
              style={{ borderColor: 'var(--border)' }}>
              
              <div className="pl-4">
                <Search size={20} style={{ color: 'var(--text-muted)' }} />
              </div>

              <input value={prompt} onChange={e => setPrompt(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && generatePlan()}
                placeholder="e.g. Build an ESP32 weather station with a BME280 sensor..."
                className="flex-1 bg-transparent py-3 text-base outline-none placeholder:text-[var(--text-muted)]"
                style={{ color: 'var(--text-primary)' }} />
              
              <button onClick={generatePlan} disabled={generating || !prompt.trim()}
                className="px-6 py-3 text-sm font-semibold rounded-xl disabled:opacity-50 transition-colors flex items-center justify-center gap-2 shadow-sm"
                style={{ background: 'var(--accent)', color: 'white' }}>
                {generating ? 'Generating...' : 'Generate Plan'}
              </button>
            </div>
          </div>
        </div>

        <AnimatePresence mode="wait">
          {planResult ? (
            /* ── Dynamic AI Result / Hardware Graph ── */
            <motion.div key="plan" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, height: 0 }}
              className="card-standard p-10 mt-10 shadow-sm rounded-xl">
              <div className="flex items-center justify-between mb-8 pb-6 border-b" style={{ borderColor: 'var(--border)' }}>
                <h3 className="text-xl font-bold flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
                  <Layers size={22} style={{ color: 'var(--text-muted)' }} /> {planResult.project_name} Architecture
                </h3>
                <div className="text-sm font-semibold px-4 py-2 rounded-lg border bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                  Estimated BOM: ${planResult.total_cost || '~12.00'}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-12">
                {/* Visual Tree */}
                <div className="p-6 rounded-xl border" style={{ background: 'var(--bg-primary)', borderColor: 'var(--border)' }}>
                  <h4 className="text-sm font-bold uppercase tracking-widest mb-6" style={{ color: 'var(--text-muted)' }}>Component Graph</h4>
                  <div className="ml-3 border-l-2 pl-6 space-y-5" style={{ borderColor: 'var(--border)' }}>
                    <div className="relative">
                      <div className="absolute -left-[31px] top-1.5 w-4 h-4 rounded-full border-[3px]" style={{ borderColor: 'var(--accent)', background: 'var(--bg-primary)' }} />
                      <span className="font-mono text-base font-bold" style={{ color: 'var(--text-primary)' }}>ESP32 Core Processor</span>
                    </div>
                    {planResult.components?.map((c: any, i: number) => (
                      <div key={i} className="relative bg-[var(--bg-secondary)] border rounded-lg p-3 mr-4 shadow-sm"
                        style={{ borderColor: 'var(--border)' }}>
                        <div className="absolute -left-[27px] top-4 w-6 border-t-2" style={{ borderColor: 'var(--border)' }} />
                        <div className="flex justify-between items-center px-2">
                          <span className="font-semibold text-sm text-[var(--text-secondary)]">{c.name}</span>
                          <span className="text-xs text-[var(--text-muted)] font-mono font-bold">${c.estimated_cost}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>

                {/* AI Workflow Suggestion */}
                <div className="flex flex-col justify-center">
                  <h4 className="text-sm font-bold uppercase tracking-widest mb-6" style={{ color: 'var(--text-muted)' }}>Implementation Strategy</h4>
                  <div className="space-y-6">
                    <div className="flex gap-4 text-base">
                      <span className="text-[var(--text-muted)] font-mono font-bold">01</span>
                      <p className="text-[var(--text-secondary)] leading-relaxed font-medium">Initialize FreeRTOS tasks for sensor reading and telemetry.</p>
                    </div>
                    <div className="flex gap-4 text-base">
                      <span className="text-[var(--text-muted)] font-mono font-bold">02</span>
                      <p className="text-[var(--text-secondary)] leading-relaxed font-medium">Configure I2C bus and SPI bindings for peripherals.</p>
                    </div>
                    <div className="flex gap-4 text-base">
                      <span className="text-[var(--text-muted)] font-mono font-bold">03</span>
                      <p className="text-[var(--text-secondary)] leading-relaxed font-medium">Establish local WiFi & MQTT client connection.</p>
                    </div>
                  </div>
                  
                  <button onClick={saveProjectToDB}
                    className="mt-10 w-full py-4 text-base font-bold rounded-xl transition-colors flex items-center justify-center gap-3 shadow-sm"
                    style={{ background: 'var(--text-primary)', color: 'var(--bg-primary)' }}>
                    <Terminal size={18} /> Save to local DB & Open Workpace
                  </button>
                </div>
              </div>
            </motion.div>
          ) : (
            /* ── Default Workflows & Recent Activity ── */
            <motion.div key="default" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-16 pt-8">
              
              {/* Recent Projects (Dexie DB) */}
              {(recentProjects && recentProjects.length > 0) && (
                <div className="space-y-4">
                  <h3 className="text-xs font-semibold uppercase tracking-widest pl-1 flex items-center gap-2" style={{ color: 'var(--text-muted)' }}>
                    <Clock size={14} /> Recent Projects
                  </h3>
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {recentProjects.map((proj) => (
                      <div key={proj.id} onClick={() => setSpace('workspace')}
                        className="p-5 border bg-[var(--bg-primary)] hover:border-[var(--text-muted)] transition-all cursor-pointer group flex flex-col justify-between h-full rounded-xl shadow-sm">
                        <div>
                          <h4 className="text-sm font-semibold mb-2 group-hover:text-[var(--accent)] transition-colors" style={{ color: 'var(--text-primary)' }}>{proj.name}</h4>
                          <p className="text-xs leading-relaxed mb-4" style={{ color: 'var(--text-muted)' }}>{proj.description || 'No description provided.'}</p>
                        </div>
                        <div className="flex items-center justify-between mt-4 border-t pt-4" style={{ borderColor: 'var(--border)' }}>
                          <div className="text-[10px] font-mono uppercase tracking-widest font-semibold" style={{ color: 'var(--text-muted)' }}>{proj.board}</div>
                          <div className="text-[10px] font-medium" style={{ color: 'var(--text-secondary)' }}>{new Date(proj.createdAt).toLocaleDateString()}</div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Organized Workflows instead of generic Quick Actions */}
              <div className="grid grid-cols-1 md:grid-cols-4 gap-8">
                {workflows.map((group) => (
                  <div key={group.category} className="space-y-4">
                    <h3 className="text-xs font-semibold uppercase tracking-widest pl-1" style={{ color: 'var(--text-muted)' }}>{group.category}</h3>
                    <div className="space-y-3">
                      {group.actions.map((action) => (
                        <button key={action.label} onClick={() => action.space && setSpace(action.space)}
                          className="w-full text-left flex items-center gap-3 px-4 py-3 border rounded-xl bg-[var(--bg-primary)] hover:bg-[var(--bg-secondary)] hover:border-[var(--text-muted)] transition-all shadow-sm group"
                          style={{ borderColor: 'var(--border)' }}>
                          <div className="flex items-center justify-center w-8 h-8 rounded-lg border bg-[var(--bg-primary)] group-hover:bg-[var(--bg-secondary)] transition-colors" style={{ borderColor: 'var(--border)' }}>
                            <action.icon size={16} style={{ color: action.color }} />
                          </div>
                          <span className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>{action.label}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                ))}
              </div>

              {/* Curated Recent / Gallery */}
              {templates.length > 0 && (
                <div className="pt-10 border-t" style={{ borderColor: 'var(--border)' }}>
                  <h3 className="text-xs font-semibold uppercase tracking-widest mb-6 pl-1" style={{ color: 'var(--text-muted)' }}>Template Library</h3>
                  <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-6">
                    {templates.slice(0, 3).map((t) => (
                      <div key={t.id}
                        className="p-5 border bg-[var(--bg-primary)] hover:border-[var(--text-muted)] transition-all cursor-pointer group flex flex-col justify-between h-full rounded-xl shadow-sm">
                        <div>
                          <h4 className="text-sm font-semibold mb-2 group-hover:text-[var(--accent)] transition-colors" style={{ color: 'var(--text-primary)' }}>{t.title}</h4>
                          <p className="text-xs leading-relaxed mb-4" style={{ color: 'var(--text-muted)' }}>{t.description}</p>
                        </div>
                        <div className="text-[10px] font-mono uppercase tracking-widest font-semibold" style={{ color: 'var(--text-muted)' }}>{t.board}</div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

            </motion.div>
          )}
        </AnimatePresence>

      </div>
    </div>
  );
}
