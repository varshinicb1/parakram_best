import { useState, useEffect } from 'react';
import { useBackendApi, DriverInfo } from '../hooks/useBackendApi';

function DriversPage() {
  const { fetchDrivers } = useBackendApi();
  const [drivers, setDrivers] = useState<DriverInfo[]>([]);
  const [filter, setFilter] = useState('');

  useEffect(() => {
    fetchDrivers().then(setDrivers).catch(() => setDrivers([]));
  }, []);

  const filtered = drivers.filter(d =>
    d.name.toLowerCase().includes(filter.toLowerCase()) ||
    d.driver_type.toLowerCase().includes(filter.toLowerCase()) ||
    d.capabilities.some(c => c.toLowerCase().includes(filter.toLowerCase()))
  );

  return (
    <div>
      <div className="page-header">
        <h2>Drivers ({drivers.length})</h2>
        <p>Hardware driver registry</p>
      </div>

      <div style={{ marginBottom: 16 }}>
        <input
          type="text"
          placeholder="Filter drivers by name, type, or capability..."
          value={filter}
          onChange={e => setFilter(e.target.value)}
          style={{
            width: '100%',
            padding: '8px 12px',
            background: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            borderRadius: 6,
            color: 'var(--text-primary)',
            fontSize: 14,
          }}
        />
      </div>

      <div className="card-grid">
        {filtered.map(driver => (
          <div key={driver.name} className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <strong>{driver.display_name}</strong>
              <span className={`badge ${
                driver.driver_type === 'sensor' ? 'badge-green' :
                driver.driver_type === 'actuator' ? 'badge-orange' :
                'badge-blue'
              }`}>
                {driver.driver_type}
              </span>
            </div>
            <div style={{ color: 'var(--text-secondary)', fontSize: 12, marginTop: 4 }}>
              {driver.name} v{driver.version}
            </div>
            <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 4 }}>
              {driver.capabilities.map(cap => (
                <span key={cap} style={{
                  fontSize: 11,
                  padding: '1px 6px',
                  borderRadius: 4,
                  background: 'var(--bg-tertiary)',
                  color: 'var(--text-secondary)',
                }}>
                  {cap}
                </span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export default DriversPage;
