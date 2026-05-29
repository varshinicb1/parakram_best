/**
 * ModelSettings — Full-page model management with API key entry and custom provider configuration.
 * Embedded in SettingsSpace.
 */
import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Key, Plus, Trash2, Save, Check, Globe, Cpu, Zap } from 'lucide-react';

interface CustomProvider {
  id: string;
  name: string;
  base_url: string;
  model: string;
  api_key: string;
  provider_name: string;
}

const PROVIDER_PRESETS = [
  { id: 'openrouter', name: 'OpenRouter', placeholder: 'sk-or-v1-...' },
  { id: 'openai', name: 'OpenAI', placeholder: 'sk-...' },
  { id: 'anthropic', name: 'Anthropic', placeholder: 'sk-ant-...' },
  { id: 'google', name: 'Google AI', placeholder: 'AIza...' },
  { id: 'groq', name: 'Groq', placeholder: 'gsk_...' },
  { id: 'together', name: 'Together AI', placeholder: 'tok_...' },
  { id: 'fireworks', name: 'Fireworks AI', placeholder: 'fw_...' },
  { id: 'deepseek', name: 'DeepSeek', placeholder: 'sk-...' },
  { id: 'mistral', name: 'Mistral AI', placeholder: '' },
];

export default function ModelSettings() {
  const [maskedKeys, setMaskedKeys] = useState<Record<string, string>>({});
  const [newKeyProvider, setNewKeyProvider] = useState('');
  const [newKeyValue, setNewKeyValue] = useState('');
  const [saveStatus, setSaveStatus] = useState<string>('');
  const [customProviders, setCustomProviders] = useState<CustomProvider[]>([]);
  const [showAddCustom, setShowAddCustom] = useState(false);
  const [customForm, setCustomForm] = useState({ id: '', name: '', base_url: '', model: '', api_key: '', provider_name: 'custom' });

  useEffect(() => {
    fetch('http://localhost:8000/api/llm/settings')
      .then(r => r.json())
      .then(data => {
        setMaskedKeys(data.api_keys || {});
        setCustomProviders(data.custom_providers || []);
      })
      .catch(() => {});
  }, []);

  const saveApiKey = async (provider: string, key: string) => {
    try {
      const res = await fetch('http://localhost:8000/api/llm/api-key', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ provider, api_key: key }),
      });
      if (res.ok) {
        setSaveStatus(`${provider} key saved`);
        setMaskedKeys(prev => ({ ...prev, [provider]: key.slice(0, 8) + '...' + key.slice(-4) }));
        setNewKeyValue('');
        setNewKeyProvider('');
        setTimeout(() => setSaveStatus(''), 3000);
      }
    } catch (e) {
      console.error('Failed to save key:', e);
    }
  };

  const deleteApiKey = async (provider: string) => {
    try {
      await fetch(`http://localhost:8000/api/llm/api-key/${provider}`, { method: 'DELETE' });
      setMaskedKeys(prev => { const n = { ...prev }; delete n[provider]; return n; });
    } catch (e) {
      console.error('Failed to delete key:', e);
    }
  };

  const addCustomProvider = async () => {
    try {
      const res = await fetch('http://localhost:8000/api/llm/custom-provider', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(customForm),
      });
      if (res.ok) {
        setCustomProviders(prev => [...prev.filter(p => p.id !== customForm.id), customForm as CustomProvider]);
        setShowAddCustom(false);
        setCustomForm({ id: '', name: '', base_url: '', model: '', api_key: '', provider_name: 'custom' });
      }
    } catch (e) {
      console.error('Failed to add provider:', e);
    }
  };

  const deleteCustomProvider = async (id: string) => {
    try {
      await fetch(`http://localhost:8000/api/llm/custom-provider/${id}`, { method: 'DELETE' });
      setCustomProviders(prev => prev.filter(p => p.id !== id));
    } catch (e) {
      console.error('Failed to delete provider:', e);
    }
  };

  return (
    <div className="flex flex-col gap-5">
      {/* Section: API Keys */}
      <div className="border rounded-xl p-5" style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <div className="flex items-center gap-2 mb-2">
          <div className="p-1.5 border rounded-lg bg-[var(--bg-primary)]" style={{ borderColor: 'var(--border)' }}>
            <Key size={16} style={{ color: 'var(--text-primary)' }} />
          </div>
          <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
            API Key Management
          </h3>
        </div>
        <p className="text-xs font-medium mb-4" style={{ color: 'var(--text-muted)' }}>
          Add your own API keys to unlock premium models. Free models work without keys.
        </p>

        {/* Existing keys */}
        {Object.entries(maskedKeys).map(([provider, masked]) => masked && (
          <div key={provider} className="flex items-center gap-3 mb-2 px-4 py-3 border rounded-lg bg-[var(--bg-primary)]"
            style={{ borderColor: 'var(--border)' }}>
            <Globe size={14} style={{ color: 'var(--text-secondary)' }} />
            <span className="text-xs font-bold uppercase flex-1" style={{ color: 'var(--text-primary)' }}>
              {provider}
            </span>
            <span className="text-xs font-mono font-medium" style={{ color: 'var(--text-muted)' }}>
              {masked}
            </span>
            <button onClick={() => deleteApiKey(provider)} className="p-1.5 ml-2 hover:bg-red-500/10 rounded-md transition-colors"
              style={{ color: '#ef4444' }}>
              <Trash2 size={14} />
            </button>
          </div>
        ))}

        {/* Add new key */}
        <div className="flex flex-col sm:flex-row items-center gap-2 mt-3">
          <select value={newKeyProvider} onChange={(e) => setNewKeyProvider(e.target.value)}
            className="w-full sm:w-auto bg-[var(--bg-primary)] border rounded-lg px-3 py-2.5 text-xs font-bold outline-none shadow-sm cursor-pointer"
            style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
            <option value="">Select Provider</option>
            {PROVIDER_PRESETS.map(p => <option key={p.id} value={p.id}>{p.name}</option>)}
          </select>
          <input
            value={newKeyValue}
            onChange={(e) => setNewKeyValue(e.target.value)}
            placeholder={PROVIDER_PRESETS.find(p => p.id === newKeyProvider)?.placeholder || 'Paste API Key...'}
            className="w-full sm:flex-1 bg-[var(--bg-primary)] border rounded-lg px-3 py-2.5 text-xs font-mono outline-none focus:border-[var(--text-primary)] transition-colors shadow-sm"
            type="password"
            style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
          />
          <button onClick={() => { if (newKeyProvider && newKeyValue) saveApiKey(newKeyProvider, newKeyValue); }}
            className="w-full sm:w-auto flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border text-xs font-bold transition-all hover:opacity-80 shadow-sm"
            style={{ borderColor: 'var(--border)', background: 'var(--text-primary)', color: 'var(--bg-primary)' }}>
            <Save size={14} /> Save
          </button>
        </div>

        {/* Save confirmation */}
        <AnimatePresence>
          {saveStatus && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
              className="mt-3 flex items-center gap-2 text-xs font-bold px-3 py-2 rounded-lg bg-[#22c55e15] border overflow-hidden"
              style={{ color: '#22c55e', borderColor: '#22c55e40' }}>
              <Check size={14} /> {saveStatus}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Section: Custom Providers */}
      <div className="border rounded-xl p-5" style={{ borderColor: 'var(--border)', background: 'var(--bg-secondary)' }}>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <div className="p-1.5 border rounded-lg bg-[var(--bg-primary)]" style={{ borderColor: 'var(--border)' }}>
              <Cpu size={16} style={{ color: '#8b5cf6' }} />
            </div>
            <h3 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
              Custom Providers
            </h3>
          </div>
          <button onClick={() => setShowAddCustom(!showAddCustom)}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-bold shadow-sm transition-all hover:opacity-80"
            style={{ background: '#8b5cf6', borderColor: '#8b5cf6', color: 'white' }}>
            <Plus size={14} /> Add Provider
          </button>
        </div>
        <p className="text-xs font-medium mb-4" style={{ color: 'var(--text-muted)' }}>
          Connect any OpenAI-compatible API endpoint (LMStudio, text-generation-webui, vLLM, etc.)
        </p>

        {/* Existing custom providers */}
        {customProviders.map(cp => (
          <div key={cp.id} className="flex items-center gap-3 mb-2 px-4 py-3 border rounded-lg bg-[var(--bg-primary)]"
            style={{ borderColor: 'var(--border)' }}>
            <Zap size={14} style={{ color: '#ec4899' }} />
            <div className="flex-1">
              <div className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>
                {cp.name}
              </div>
              <div className="text-[10px] font-mono font-medium mt-0.5" style={{ color: 'var(--text-muted)' }}>
                {cp.base_url} · {cp.model}
              </div>
            </div>
            <button onClick={() => deleteCustomProvider(cp.id)} className="p-1.5 ml-2 hover:bg-red-500/10 rounded-md transition-colors"
              style={{ color: '#ef4444' }}>
              <Trash2 size={14} />
            </button>
          </div>
        ))}

        {/* Add custom provider form */}
        <AnimatePresence>
          {showAddCustom && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
              className="mt-4 border rounded-xl p-4 flex flex-col gap-3 bg-[var(--bg-primary)] overflow-hidden" style={{ borderColor: '#8b5cf640' }}>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {['id', 'name', 'base_url', 'model'].map(field => (
                  <input key={field}
                    value={(customForm as Record<string, string>)[field] || ''}
                    onChange={(e) => setCustomForm(prev => ({ ...prev, [field]: e.target.value }))}
                    placeholder={field === 'base_url' ? 'http://localhost:1234/v1' : field.replace('_', ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    className="bg-[var(--bg-secondary)] border rounded-lg px-3 py-2.5 text-xs font-mono outline-none focus:border-[#8b5cf6] transition-colors"
                    style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
                  />
                ))}
              </div>
              <input
                value={customForm.api_key}
                onChange={(e) => setCustomForm(prev => ({ ...prev, api_key: e.target.value }))}
                placeholder="API Key (Optional)"
                type="password"
                className="bg-[var(--bg-secondary)] border rounded-lg px-3 py-2.5 text-xs font-mono outline-none focus:border-[#8b5cf6] transition-colors"
                style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
              />
              <button onClick={addCustomProvider}
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg border text-xs font-bold transition-all hover:opacity-80 shadow-sm"
                style={{ background: '#8b5cf6', borderColor: '#8b5cf6', color: 'white' }}>
                <Check size={14} /> Save Provider
              </button>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
