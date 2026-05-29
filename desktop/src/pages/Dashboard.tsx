import { useState, useEffect } from 'react';
import { useBackendApi } from '../hooks/useBackendApi';

function Dashboard() {
  const { fetchDriverCount, fetchHealth } = useBackendApi();
  const [driverCount, setDriverCount] = useState<number | null>(null);
  const [health, setHealth] = useState<string>('checking...');

  useEffect(() => {
    fetchDriverCount().then(setDriverCount).catch(() => setDriverCount(null));
    fetchHealth().then(h => setHealth(h ? 'connected' : 'offline')).catch(() => setHealth('offline'));
  }, []);

  return (
    <div>
      <div className="page-header">
        <h2>Dashboard</h2>
        <p>Parakram platform overview</p>
      </div>

      <div className="card-grid">
        <div className="card stat-card">
          <div className="value">{driverCount ?? '—'}</div>
          <div className="label">Firmware Drivers</div>
        </div>
        <div className="card stat-card">
          <div className="value">248</div>
          <div className="label">Golden Blocks</div>
        </div>
        <div className="card stat-card">
          <div className="value">4</div>
          <div className="label">MCU Platforms</div>
        </div>
        <div className="card stat-card">
          <div className="value">
            <span className={`badge ${health === 'connected' ? 'badge-green' : 'badge-orange'}`}>
              {health}
            </span>
          </div>
          <div className="label">Backend Status</div>
        </div>
      </div>

      <div style={{ marginTop: 24 }}>
        <div className="card">
          <h3 style={{ marginBottom: 12 }}>Quick Actions</h3>
          <div style={{ display: 'flex', gap: 12 }}>
            <button className="btn btn-primary" onClick={() => window.location.href = '/build'}>
              New Build
            </button>
            <button className="btn" onClick={() => window.location.href = '/blocks'}>
              Browse Blocks
            </button>
            <button className="btn" onClick={() => window.location.href = '/drivers'}>
              View Drivers
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
