import { useState, useEffect } from 'react';

function SettingsPage() {
  const [backendUrl, setBackendUrl] = useState('http://localhost:8400');
  const [theme, setTheme] = useState('dark');

  useEffect(() => {
    try {
      import('@tauri-apps/api').then(api => {
        api.invoke('get_backend_url').then((url: unknown) => {
          if (typeof url === 'string') setBackendUrl(url);
        });
      }).catch(() => { /* Running in browser mode */ });
    } catch {
      // Running in browser mode
    }
  }, []);

  return (
    <div>
      <div className="page-header">
        <h2>Settings</h2>
        <p>Configure Parakram Studio</p>
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 12 }}>Backend Connection</h3>
        <label style={{ color: 'var(--text-secondary)', fontSize: 14 }}>Backend URL</label>
        <input
          type="text"
          value={backendUrl}
          onChange={e => setBackendUrl(e.target.value)}
          style={{
            display: 'block',
            width: '100%',
            marginTop: 4,
            padding: '8px 12px',
            background: 'var(--bg-primary)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            color: 'var(--text-primary)',
            fontSize: 14,
          }}
        />
      </div>

      <div className="card" style={{ marginBottom: 16 }}>
        <h3 style={{ marginBottom: 12 }}>Appearance</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button
            className={`btn ${theme === 'dark' ? 'btn-primary' : ''}`}
            onClick={() => setTheme('dark')}
          >
            Dark
          </button>
          <button
            className={`btn ${theme === 'light' ? 'btn-primary' : ''}`}
            onClick={() => setTheme('light')}
          >
            Light
          </button>
        </div>
      </div>

      <div className="card">
        <h3 style={{ marginBottom: 12 }}>About</h3>
        <p style={{ color: 'var(--text-secondary)', fontSize: 14 }}>
          Parakram Studio v1.0.0<br />
          Vidyuthlabs — vidyuthlabs.co.in<br />
          License: PolyForm Noncommercial 1.0.0
        </p>
      </div>
    </div>
  );
}

export default SettingsPage;
