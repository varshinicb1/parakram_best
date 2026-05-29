/**
 * ExtensionSpace — VS Code-style extension management panel.
 * Browse installed extensions, marketplace, enable/disable, install.
 */
import { useState, useEffect } from 'react';
import {
  Puzzle, Download, Search, ToggleLeft, ToggleRight,
  Cpu, Thermometer, Radio, Wrench, Shield, Upload, Battery, Activity
} from 'lucide-react';

interface Extension {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  icon: string;
  category: string;
  enabled: boolean;
  loaded: boolean;
  builtin: boolean;
  provides: string[];
  error?: string;
}

interface MarketplaceItem {
  id: string;
  name: string;
  version: string;
  description: string;
  author: string;
  category: string;
  downloads: number;
}

const ICON_MAP: Record<string, typeof Cpu> = {
  cpu: Cpu, thermometer: Thermometer, radio: Radio, wrench: Wrench,
  shield: Shield, upload: Upload, battery: Battery, activity: Activity,
  puzzle: Puzzle,
};

const CATEGORY_COLORS: Record<string, string> = {
  'board-support': '#3b82f6',
  sensor: '#22c55e',
  protocol: '#d97706',
  tool: '#8b5cf6',
  general: 'var(--accent)',
};

const API = 'http://localhost:8000/api/extensions';

export default function ExtensionSpace() {
  const [tab, setTab] = useState<'installed' | 'marketplace'>('installed');
  const [extensions, setExtensions] = useState<Extension[]>([]);
  const [marketplace, setMarketplace] = useState<MarketplaceItem[]>([]);
  const [search, setSearch] = useState('');
  const [installing, setInstalling] = useState<string | null>(null);

  useEffect(() => {
    fetch(`${API}/list`).then(r => r.json()).then(d => setExtensions(d.extensions || [])).catch(() => {});
    fetch(`${API}/marketplace`).then(r => r.json()).then(d => setMarketplace(d.available || [])).catch(() => {});
  }, []);

  const toggleExtension = async (ext: Extension) => {
    try {
      await fetch(`${API}/${ext.id}/toggle`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ enabled: !ext.enabled }),
      });
      setExtensions(prev => prev.map(e => e.id === ext.id ? { ...e, enabled: !e.enabled } : e));
    } catch { /* ignore */ }
  };

  const installExtension = async (item: MarketplaceItem) => {
    setInstalling(item.id);
    try {
      await fetch(`${API}/install`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ manifest: item }),
      });
      // Refresh
      const res = await fetch(`${API}/list`);
      const data = await res.json();
      setExtensions(data.extensions || []);
      setMarketplace(prev => prev.filter(m => m.id !== item.id));
    } catch { /* ignore */ }
    setInstalling(null);
  };

  const filteredExtensions = extensions.filter(e =>
    !search || e.name.toLowerCase().includes(search.toLowerCase()) || e.category.includes(search.toLowerCase())
  );

  const filteredMarketplace = marketplace.filter(m =>
    !search || m.name.toLowerCase().includes(search.toLowerCase())
  );

  const builtinCount = extensions.filter(e => e.builtin).length;
  const userCount = extensions.filter(e => !e.builtin).length;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
              <Puzzle size={24} style={{ color: 'var(--text-primary)' }} />
              Extension Manager
            </h1>
            <p className="text-sm font-medium mt-1" style={{ color: 'var(--text-muted)' }}>
              Browse, install, and configure modules to extend your workspace.
            </p>
          </div>
          <div className="flex items-center gap-4 text-xs font-semibold px-4 py-2 bg-[var(--bg-secondary)] border rounded-lg" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
            <span><strong style={{ color: 'var(--text-primary)' }}>{builtinCount}</strong> Built-in</span>
            <span className="w-1 h-1 rounded-full" style={{ background: 'var(--border)' }} />
            <span><strong style={{ color: 'var(--text-primary)' }}>{userCount}</strong> Installed</span>
          </div>
        </div>

        {/* Tab nav & Search wrapper */}
        <div className="flex items-center justify-between mb-8 border-b" style={{ borderColor: 'var(--border)' }}>
          {/* Tabs */}
          <div className="flex items-center gap-2">
            {([['installed', `Installed (${extensions.length})`, Puzzle], ['marketplace', 'Marketplace', Download]] as const).map(([id, label, Icon]) => (
              <button key={id} onClick={() => setTab(id)}
                className="flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-colors hover:bg-[var(--bg-secondary)] rounded-t-lg"
                style={{
                  borderBottomColor: tab === id ? 'var(--text-primary)' : 'transparent',
                  color: tab === id ? 'var(--text-primary)' : 'var(--text-muted)',
                }}>
                <Icon size={16} /> {label}
              </button>
            ))}
          </div>

          {/* Search */}
          <div className="relative mb-2 w-72">
            <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
            <input value={search} onChange={(e) => setSearch(e.target.value)}
              placeholder={`Search ${tab}...`}
              className="w-full bg-[var(--bg-secondary)] border rounded-md pl-10 pr-4 py-2 text-sm font-medium outline-none focus:border-[var(--text-primary)] transition-colors shadow-sm"
              style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
            />
          </div>
        </div>

        {/* Installed */}
        {tab === 'installed' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {filteredExtensions.map(ext => {
              const IconComp = ICON_MAP[ext.icon] || Puzzle;
              const catColor = CATEGORY_COLORS[ext.category] || 'var(--text-primary)';
              return (
                <div key={ext.id}
                  className="bg-[var(--bg-primary)] border rounded-xl p-6 flex flex-col transition-shadow hover:shadow-md"
                  style={{
                    borderColor: ext.enabled ? catColor : 'var(--border)',
                    opacity: ext.enabled ? 1 : 0.6,
                  }}>
                  {/* Header Row */}
                  <div className="flex items-start justify-between mb-4">
                    <div className="w-12 h-12 flex items-center justify-center rounded-lg bg-[var(--bg-secondary)] border shrink-0"
                      style={{ borderColor: ext.enabled ? catColor : 'var(--border)', color: ext.enabled ? catColor : 'var(--text-muted)' }}>
                      <IconComp size={24} />
                    </div>
                    {/* Toggle */}
                    <button onClick={() => toggleExtension(ext)} className="p-1 -mr-1 transition-colors hover:text-[var(--text-primary)]"
                      style={{ color: ext.enabled ? catColor : 'var(--text-muted)' }}
                      title={ext.enabled ? 'Disable' : 'Enable'}>
                      {ext.enabled ? <ToggleRight size={28} /> : <ToggleLeft size={28} />}
                    </button>
                  </div>
                  
                  {/* Info */}
                  <div className="flex-1">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>
                        {ext.name}
                      </span>
                      <span className="text-xs font-mono px-2 py-0.5 bg-[var(--bg-secondary)] rounded-md border"
                        style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
                        v{ext.version}
                      </span>
                    </div>
                    
                    <div className="flex items-center gap-1.5 mb-3 flex-wrap">
                      <span className="text-xs font-semibold px-2 py-0.5 rounded-md"
                        style={{ background: `${catColor}15`, color: catColor }}>
                        {ext.category}
                      </span>
                      {ext.builtin && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-md bg-[var(--bg-secondary)] border"
                          style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
                          Built-in
                        </span>
                      )}
                    </div>
                    
                    <p className="text-sm leading-relaxed mb-4" style={{ color: 'var(--text-muted)' }}>
                      {ext.description}
                    </p>
                  </div>
                  
                  {/* Capabilities */}
                  {ext.provides.length > 0 && (
                    <div className="flex gap-2 flex-wrap pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
                      {ext.provides.slice(0, 3).map(p => (
                        <span key={p} className="text-[10px] font-mono font-medium px-2 py-1 bg-[var(--bg-secondary)] rounded-md border truncate max-w-[120px]"
                          style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }} title={p}>
                          {p}
                        </span>
                      ))}
                      {ext.provides.length > 3 && (
                        <span className="text-[10px] font-mono font-medium px-2 py-1 bg-[var(--bg-secondary)] rounded-md border"
                          style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
                          +{ext.provides.length - 3}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}

        {/* Marketplace */}
        {tab === 'marketplace' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {filteredMarketplace.length === 0 ? (
              <div className="col-span-full text-center py-16 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                You have installed all available published extensions.
              </div>
            ) : filteredMarketplace.map(item => (
              <div key={item.id}
                className="bg-[var(--bg-primary)] border rounded-xl p-6 flex flex-col sm:flex-row items-start sm:items-center gap-5 transition-shadow hover:shadow-md"
                style={{ borderColor: 'var(--border)' }}>
                <div className="w-14 h-14 flex items-center justify-center rounded-xl bg-[var(--bg-secondary)] border shrink-0"
                  style={{ borderColor: 'var(--border)' }}>
                  <Puzzle size={24} style={{ color: 'var(--text-primary)' }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-3 mb-1">
                    <span className="text-base font-bold truncate" style={{ color: 'var(--text-primary)' }}>{item.name}</span>
                    <span className="text-xs font-mono px-2 py-0.5 bg-[var(--bg-secondary)] rounded-md border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>v{item.version}</span>
                  </div>
                  <p className="text-sm leading-relaxed mb-3 line-clamp-2" style={{ color: 'var(--text-muted)' }}>{item.description}</p>
                  <div className="flex items-center justify-between">
                    <div className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>
                      By {item.author}  •  {item.downloads.toLocaleString()} installs
                    </div>
                    <button onClick={() => installExtension(item)}
                      disabled={installing === item.id}
                      className="flex items-center gap-2 px-4 py-2 rounded-md transition-colors text-sm font-semibold border disabled:opacity-50"
                      style={{ 
                        background: 'var(--text-primary)', 
                        color: 'var(--bg-primary)',
                        borderColor: 'var(--text-primary)'
                      }}>
                      {installing === item.id ? 'Installing...' : <><Download size={16} /> Install</>}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
