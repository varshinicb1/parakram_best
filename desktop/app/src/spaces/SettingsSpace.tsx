/**
 * SettingsSpace — LLM model management, API keys, account settings,
 * power profiler, memory analyzer, and system config.
 * Premium control panel for the entire Parakram OS.
 */
import { useState, useEffect } from 'react';
import {
  Settings, Key, Cpu, User, CreditCard, Palette, Globe,
  Eye, EyeOff, Check, Save
} from 'lucide-react';

interface LLMProvider {
  id: string;
  name: string;
  models: string[];
  apiKeyEnv: string;
  enabled: boolean;
  freeModels: string[];
}

interface Plan {
  id: string;
  name: string;
  price: number;
  features: Record<string, any>;
}

const API = 'http://localhost:8000/api';

const LLM_PROVIDERS: LLMProvider[] = [
  {
    id: 'openrouter', name: 'OpenRouter',
    models: ['mistralai/mistral-7b-instruct:free', 'google/gemma-2-9b-it:free', 'meta-llama/llama-3.1-8b-instruct:free',
             'qwen/qwen-2.5-coder-32b-instruct:free', 'deepseek/deepseek-coder-33b-instruct', 'anthropic/claude-3.5-sonnet'],
    apiKeyEnv: 'OPENROUTER_API_KEY', enabled: true,
    freeModels: ['mistralai/mistral-7b-instruct:free', 'google/gemma-2-9b-it:free', 'meta-llama/llama-3.1-8b-instruct:free', 'qwen/qwen-2.5-coder-32b-instruct:free'],
  },
  {
    id: 'ollama', name: 'Ollama (Local)',
    models: ['parakram-coder:latest', 'codellama:7b', 'deepseek-coder:6.7b', 'qwen2.5-coder:7b', 'starcoder2:3b'],
    apiKeyEnv: '', enabled: true,
    freeModels: ['parakram-coder:latest', 'codellama:7b', 'deepseek-coder:6.7b', 'qwen2.5-coder:7b', 'starcoder2:3b'],
  },
  {
    id: 'gemini', name: 'Google Gemini',
    models: ['gemini-2.0-flash', 'gemini-1.5-pro', 'gemini-1.5-flash'],
    apiKeyEnv: 'GEMINI_API_KEY', enabled: false,
    freeModels: ['gemini-2.0-flash'],
  },
  {
    id: 'anthropic', name: 'Anthropic Claude',
    models: ['claude-3.5-sonnet', 'claude-3-haiku'],
    apiKeyEnv: 'ANTHROPIC_API_KEY', enabled: false,
    freeModels: [],
  },
  {
    id: 'openai', name: 'OpenAI',
    models: ['gpt-4o', 'gpt-4o-mini', 'gpt-3.5-turbo'],
    apiKeyEnv: 'OPENAI_API_KEY', enabled: false,
    freeModels: [],
  },
  {
    id: 'groq', name: 'Groq (Fast)',
    models: ['llama-3.1-70b-versatile', 'mixtral-8x7b-32768', 'gemma2-9b-it'],
    apiKeyEnv: 'GROQ_API_KEY', enabled: false,
    freeModels: ['llama-3.1-70b-versatile', 'mixtral-8x7b-32768'],
  },
];

export default function SettingsSpace() {
  const [tab, setTab] = useState<'llm' | 'account' | 'billing' | 'appearance' | 'advanced'>('llm');
  const [providers, setProviders] = useState(LLM_PROVIDERS);
  const [activeModel, setActiveModel] = useState('qwen/qwen-2.5-coder-32b-instruct:free');
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({});
  const [showKeys, setShowKeys] = useState<Record<string, boolean>>({});
  const [plans, setPlans] = useState<Plan[]>([]);
  const [savedMsg, setSavedMsg] = useState('');
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    fetch(`${API}/billing/plans`).then(r => r.json()).then(d => setPlans(d.plans || [])).catch(() => {});
  }, []);

  const saveSettings = () => {
    localStorage.setItem('parakram_active_model', activeModel);
    localStorage.setItem('parakram_api_keys', JSON.stringify(apiKeys));
    localStorage.setItem('parakram_theme', theme);
    setSavedMsg('Settings saved!');
    setTimeout(() => setSavedMsg(''), 2000);
  };

  const tabs = [
    { id: 'llm' as const, label: 'LLM MODELS', icon: Cpu },
    { id: 'account' as const, label: 'ACCOUNT', icon: User },
    { id: 'billing' as const, label: 'BILLING', icon: CreditCard },
    { id: 'appearance' as const, label: 'APPEARANCE', icon: Palette },
    { id: 'advanced' as const, label: 'ADVANCED', icon: Settings },
  ];

  return (
    <div className="flex-1 flex overflow-hidden">
      {/* Left: Tab Navigation */}
      <div className="w-56 border-r flex flex-col shrink-0 bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
        <div className="px-4 py-4 border-b" style={{ borderColor: 'var(--border)' }}>
          <h2 className="text-sm font-semibold" style={{ color: 'var(--text-muted)' }}>Settings</h2>
        </div>
        <div className="py-2">
          {tabs.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => setTab(id)}
              className="flex items-center gap-3 w-[calc(100%-16px)] mx-2 px-3 py-2.5 text-sm font-medium transition-colors text-left rounded-lg my-0.5"
              style={{
                background: tab === id ? 'var(--bg-primary)' : 'transparent',
                color: tab === id ? 'var(--text-primary)' : 'var(--text-muted)',
                boxShadow: tab === id ? '0 1px 2px rgba(0,0,0,0.05)' : 'none',
                border: tab === id ? '1px solid var(--border)' : '1px solid transparent',
              }}>
              <Icon size={16} /> {label}
            </button>
          ))}
        </div>

        {/* Save button */}
        <div className="mt-auto p-4 border-t bg-[var(--bg-primary)]" style={{ borderColor: 'var(--border)' }}>
          <button onClick={saveSettings}
            className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm font-semibold rounded-lg transition-colors shadow-sm"
            style={{ background: 'var(--text-primary)', color: 'var(--bg-primary)' }}>
            <Save size={16} /> Save Changes
          </button>
          {savedMsg && (
            <p className="text-center text-xs font-medium mt-2 flex items-center justify-center gap-1" style={{ color: 'var(--success)' }}>
              <Check size={14} /> {savedMsg}
            </p>
          )}
        </div>
      </div>

      {/* Right: Content */}
      <div className="flex-1 overflow-y-auto p-8 space-y-8 bg-[var(--bg-tertiary)]">

        {/* ── LLM Models ─────────────────────────────────── */}
        {tab === 'llm' && (
          <div className="max-w-4xl space-y-6">
            <div className="bg-[var(--bg-primary)] border rounded-xl p-6 shadow-sm" style={{ borderColor: 'var(--border)' }}>
              <h3 className="text-base font-bold mb-1" style={{ color: 'var(--text-primary)' }}>Active LLM Model</h3>
              <p className="text-sm mb-4" style={{ color: 'var(--text-muted)' }}>This model will be used by default for firmware generation and analysis.</p>
              <div className="bg-[var(--bg-secondary)] border rounded-lg px-4 py-2.5 text-sm font-mono font-bold" style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
                {activeModel}
              </div>
            </div>

            <h3 className="text-lg font-bold pt-2" style={{ color: 'var(--text-primary)' }}>Providers</h3>
            <div className="space-y-4">
              {providers.map(provider => (
                <div key={provider.id} className="bg-[var(--bg-primary)] border rounded-xl p-6 shadow-sm transition-shadow hover:shadow-md" style={{ borderColor: 'var(--border)' }}>
                  <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-3">
                      <Globe size={18} style={{ color: provider.enabled ? 'var(--text-primary)' : 'var(--text-muted)' }} />
                      <h4 className="text-base font-bold" style={{ color: 'var(--text-primary)', opacity: provider.enabled ? 1 : 0.6 }}>{provider.name}</h4>
                      {provider.freeModels.length > 0 && provider.enabled && (
                        <span className="text-xs font-semibold px-2 py-0.5 rounded-full" style={{ background: '#22c55e20', color: 'var(--success)' }}>
                          {provider.freeModels.length} Free
                        </span>
                      )}
                    </div>
                      <label className="flex items-center gap-2 cursor-pointer">
                        <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
                          {provider.enabled ? 'Enabled' : 'Disabled'}
                        </span>
                        <div className="w-10 h-5 rounded-full relative cursor-pointer transition-colors"
                        style={{ background: provider.enabled ? 'var(--text-primary)' : 'var(--border)' }}
                        onClick={() => {
                          setProviders(p => p.map(pr => pr.id === provider.id ? { ...pr, enabled: !pr.enabled } : pr));
                        }}>
                        <div className="w-4 h-4 rounded-full absolute top-0.5 transition-transform bg-[var(--bg-primary)]"
                          style={{ left: provider.enabled ? '22px' : '2px', transform: 'translateX(0)' }} />
                      </div>
                    </label>
                  </div>

                  <div className={`space-y-4 transition-opacity duration-200 ${provider.enabled ? 'opacity-100' : 'opacity-40 pointer-events-none'}`}>
                    {provider.apiKeyEnv && (
                      <div className="flex items-center gap-3 bg-[var(--bg-secondary)] border rounded-lg px-3 py-1.5 focus-within:border-[var(--text-primary)] transition-colors" style={{ borderColor: 'var(--border)' }}>
                        <Key size={16} style={{ color: 'var(--text-muted)' }} />
                        <input
                          type={showKeys[provider.id] ? 'text' : 'password'}
                          value={apiKeys[provider.id] || ''}
                          onChange={e => setApiKeys({ ...apiKeys, [provider.id]: e.target.value })}
                          placeholder={`Enter ${provider.apiKeyEnv}...`}
                          className="flex-1 bg-transparent border-none text-sm font-mono outline-none py-1"
                          style={{ color: 'var(--text-primary)' }}
                        />
                        <button onClick={() => setShowKeys({ ...showKeys, [provider.id]: !showKeys[provider.id] })}
                          className="p-1.5 hover:bg-[var(--border)] rounded transition-colors" style={{ color: 'var(--text-muted)' }}>
                          {showKeys[provider.id] ? <EyeOff size={16} /> : <Eye size={16} />}
                        </button>
                      </div>
                    )}

                    {/* Model list */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                      {provider.models.map(model => {
                        const isFree = provider.freeModels.includes(model);
                        const isActive = activeModel === model;
                        return (
                          <button key={model} onClick={() => setActiveModel(model)}
                            className="flex items-center gap-3 px-3 py-2.5 border rounded-lg text-left text-sm font-mono transition-colors"
                            style={{
                              borderColor: isActive ? 'var(--text-primary)' : 'var(--border)',
                              background: isActive ? 'var(--bg-secondary)' : 'transparent',
                              color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                            }}>
                            <div className="w-4 h-4 rounded-full border flex items-center justify-center shrink-0"
                              style={{ 
                                borderColor: isActive ? 'var(--text-primary)' : 'var(--text-muted)',
                                background: isActive ? 'var(--text-primary)' : 'transparent' 
                              }}>
                              {isActive && <Check size={10} className="text-[var(--bg-primary)]" strokeWidth={3} />}
                            </div>
                            <span className="truncate flex-1">{model.split('/').pop()}</span>
                            {isFree && <span className="text-[10px] font-bold tracking-widest px-1.5 py-0.5 rounded uppercase" style={{ background: '#22c55e20', color: 'var(--success)' }}>Free</span>}
                          </button>
                        );
                      })}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Account ────────────────────────────────────── */}
        {tab === 'account' && (
          <div className="space-y-6 max-w-xl bg-[var(--bg-primary)] border rounded-xl p-8 shadow-sm" style={{ borderColor: 'var(--border)' }}>
            <div>
              <h3 className="text-lg font-bold mb-1" style={{ color: 'var(--text-primary)' }}>Account Profile</h3>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Manage your personal information and credentials.</p>
            </div>
            
            <div className="space-y-4 pt-2">
              {[
                { label: 'Display Name', placeholder: 'Your name', type: 'text' },
                { label: 'Email', placeholder: 'you@example.com', type: 'email' },
                { label: 'Organization', placeholder: 'Your company (optional)', type: 'text' },
              ].map(field => (
                <div key={field.label}>
                  <label className="text-sm font-medium block mb-1.5" style={{ color: 'var(--text-primary)' }}>{field.label}</label>
                  <input type={field.type} placeholder={field.placeholder}
                    className="w-full bg-[var(--bg-secondary)] border rounded-lg px-4 py-2.5 text-sm outline-none focus:border-[var(--text-primary)] transition-colors"
                    style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
                </div>
              ))}
            </div>
            
            <div className="pt-4 border-t space-y-4" style={{ borderColor: 'var(--border)' }}>
              <h4 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>Change Password</h4>
              <div>
                <label className="text-sm font-medium block mb-1.5" style={{ color: 'var(--text-primary)' }}>New Password</label>
                <input type="password" placeholder="••••••••"
                  className="w-full bg-[var(--bg-secondary)] border rounded-lg px-4 py-2.5 text-sm outline-none focus:border-[var(--text-primary)] transition-colors mb-3"
                  style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
                <label className="text-sm font-medium block mb-1.5" style={{ color: 'var(--text-primary)' }}>Confirm Password</label>
                <input type="password" placeholder="••••••••"
                  className="w-full bg-[var(--bg-secondary)] border rounded-lg px-4 py-2.5 text-sm outline-none focus:border-[var(--text-primary)] transition-colors"
                  style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
              </div>
            </div>
          </div>
        )}

        {/* ── Billing ────────────────────────────────────── */}
        {tab === 'billing' && (
          <div className="space-y-6 max-w-5xl">
            <div>
              <h3 className="text-lg font-bold mb-1" style={{ color: 'var(--text-primary)' }}>Subscription Plans</h3>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Choose the plan that best fits your development needs.</p>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {plans.map(plan => (
                <div key={plan.id} className="bg-[var(--bg-primary)] border rounded-xl p-6 space-y-5 flex flex-col shadow-sm transition-shadow hover:shadow-md relative"
                  style={{
                    borderColor: plan.id === 'free' ? 'var(--text-primary)' : 'var(--border)',
                  }}>
                  {plan.id === 'free' && (
                    <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-3 py-0.5 rounded-full text-xs font-bold bg-[var(--text-primary)] shadow-sm whitespace-nowrap" style={{ color: 'var(--bg-primary)' }}>
                      Current Plan
                    </div>
                  )}
                  <div>
                    <h4 className="text-sm font-semibold mb-2" style={{ color: 'var(--text-primary)' }}>{plan.name}</h4>
                    <p className="text-3xl font-bold" style={{ color: 'var(--text-primary)' }}>
                      {plan.price === 0 ? 'Free' : plan.price === -1 ? 'Custom' : `$${plan.price}`}
                      {plan.price > 0 && <span className="text-sm font-normal" style={{ color: 'var(--text-muted)' }}>/mo</span>}
                    </p>
                  </div>
                  <div className="space-y-3 flex-1 pt-2">
                    {Object.entries(plan.features || {}).map(([key, val]) => (
                      <div key={key} className="flex items-center gap-3 text-sm">
                        <span className="w-4 flex justify-center" style={{ color: val === true ? 'var(--success)' : val === false ? 'var(--text-muted)' : 'var(--text-primary)' }}>
                          {val === true ? '✓' : val === false ? '—' : '✓'}
                        </span>
                        <span style={{ color: val === false ? 'var(--text-muted)' : 'var(--text-secondary)' }}>
                          {key.replace(/_/g, ' ')} {val !== true && val !== false ? `(${val})` : ''}
                        </span>
                      </div>
                    ))}
                  </div>
                  <button className="w-full px-4 py-2.5 text-sm font-semibold rounded-lg transition-colors border"
                    style={{
                      borderColor: plan.id === 'free' ? 'var(--border)' : 'var(--text-primary)',
                      background: plan.id === 'free' ? 'transparent' : 'var(--text-primary)',
                      color: plan.id === 'free' ? 'var(--text-muted)' : 'var(--bg-primary)',
                    }}>
                    {plan.id === 'free' ? 'Active' : 'Upgrade'}
                  </button>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Appearance ─────────────────────────────────── */}
        {tab === 'appearance' && (
          <div className="space-y-8 max-w-xl bg-[var(--bg-primary)] border rounded-xl p-8 shadow-sm" style={{ borderColor: 'var(--border)' }}>
            <div>
              <h3 className="text-lg font-bold mb-1" style={{ color: 'var(--text-primary)' }}>Appearance</h3>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Customize the visual experience of your workspace.</p>
            </div>
            
            <div className="space-y-6 pt-2">
              <div>
                <label className="text-sm font-medium block mb-3" style={{ color: 'var(--text-primary)' }}>Color Theme</label>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {[
                    { id: 'dark', label: 'Dark' },
                    { id: 'light', label: 'Light' },
                    { id: 'midnight', label: 'Midnight' },
                    { id: 'zinc', label: 'Zinc (V4 SaaS)' }
                  ].map(t => (
                    <button key={t.id} onClick={() => setTheme(t.id)}
                      className="px-4 py-3 text-sm font-medium border rounded-lg transition-all flex flex-col items-center gap-2 shadow-sm hover:shadow"
                      style={{
                        borderColor: theme === t.id ? 'var(--text-primary)' : 'var(--border)',
                        color: theme === t.id ? 'var(--text-primary)' : 'var(--text-secondary)',
                        background: theme === t.id ? 'var(--bg-secondary)' : 'var(--bg-primary)',
                      }}>
                      <div className="w-8 h-8 rounded-full border shadow-sm" style={{ 
                        background: t.id === 'light' ? '#f4f4f5' : t.id === 'dark' ? '#18181b' : t.id === 'midnight' ? '#0f172a' : '#27272a',
                        borderColor: 'var(--border)'
                      }} />
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>
              
              <div className="pt-4 border-t" style={{ borderColor: 'var(--border)' }}>
                <label className="text-sm font-medium block mb-3" style={{ color: 'var(--text-primary)' }}>Editor Font Size</label>
                <div className="flex items-center gap-4">
                  <span className="text-xs" style={{ color: 'var(--text-muted)' }}>Small</span>
                  <input type="range" min="10" max="18" defaultValue="14" className="flex-1 accent-[var(--text-primary)]" />
                  <span className="text-lg" style={{ color: 'var(--text-primary)' }}>Large</span>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Advanced ───────────────────────────────────── */}
        {tab === 'advanced' && (
          <div className="space-y-6 max-w-xl bg-[var(--bg-primary)] border rounded-xl p-8 shadow-sm" style={{ borderColor: 'var(--border)' }}>
            <div>
              <h3 className="text-lg font-bold mb-1" style={{ color: 'var(--text-primary)' }}>Advanced Settings</h3>
              <p className="text-sm" style={{ color: 'var(--text-muted)' }}>Configure core system paths and network preferences.</p>
            </div>
            
            <div className="space-y-4 pt-2">
              {[
                { label: 'PlatformIO Path', value: '~/.platformio', desc: 'PlatformIO installation directory' },
                { label: 'Projects Directory', value: './projects', desc: 'Default project storage' },
                { label: 'Ollama Instance URL', value: 'http://localhost:11434', desc: 'Local endpoint for Ollama' },
                { label: 'Backend API URL', value: 'http://localhost:8000', desc: 'Core server address' },
                { label: 'Default Serial Baud Rate', value: '115200', desc: 'Terminal monitor speed' },
              ].map(setting => (
                <div key={setting.label}>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-sm font-medium" style={{ color: 'var(--text-primary)' }}>{setting.label}</label>
                    <span className="text-xs" style={{ color: 'var(--text-muted)' }}>{setting.desc}</span>
                  </div>
                  <input defaultValue={setting.value}
                    className="w-full bg-[var(--bg-secondary)] border rounded-lg px-4 py-2.5 text-sm font-mono outline-none focus:border-[var(--text-primary)] transition-colors"
                    style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
                </div>
              ))}
            </div>

            <div className="pt-6 border-t space-y-4" style={{ borderColor: 'var(--border)' }}>
              <h4 className="text-sm font-bold" style={{ color: 'var(--error)' }}>Danger Zone</h4>
              <p className="text-xs" style={{ color: 'var(--text-muted)' }}>These actions cannot be undone and will permanently delete data.</p>
              <div className="flex items-center gap-3">
                <button className="px-5 py-2.5 text-sm font-semibold border rounded-lg transition-colors"
                  style={{ borderColor: 'var(--error)', border: '1px solid var(--error)', color: 'var(--error)' }}>
                  Clear All App Data
                </button>
                <button className="px-5 py-2.5 text-sm font-semibold border rounded-lg transition-colors bg-[var(--bg-secondary)] hover:bg-[var(--bg-tertiary)]"
                  style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
                  Restore Defaults
                </button>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
