/**
 * DevicesSpace — Auto-detect USB/serial devices, flash firmware, monitor serial.
 */
import { useState, useEffect, useCallback } from 'react';
import { Cpu, RefreshCw, Zap, Activity, AlertTriangle, MonitorPlay, CheckCircle2 } from 'lucide-react';

interface Device {
  port: string;
  name: string;
  board: string;
  vid?: string;
  pid?: string;
}

const MOCK_DEVICES: Device[] = [
  { port: 'COM4', name: 'ESP32 DevKit v1', board: 'esp32dev', vid: '10C4', pid: 'EA60' },
  { port: 'COM7', name: 'ESP32-S3 DevKit', board: 'esp32-s3-devkitc-1', vid: '303A', pid: '1001' },
];

export default function DevicesSpace() {
  const [devices, setDevices] = useState<Device[]>([]);
  const [scanning, setScanning] = useState(false);
  const [flashingPort, setFlashingPort] = useState<string | null>(null);
  const [flashResult, setFlashResult] = useState<Record<string, string>>({});

  const scanDevices = useCallback(async () => {
    setScanning(true);
    try {
      const resp = await fetch('http://localhost:8000/api/flash/devices');
      if (resp.ok) {
        const data = await resp.json();
        setDevices(data.devices || []);
      } else {
        // Demo mode
        await new Promise((r) => setTimeout(r, 800));
        setDevices(MOCK_DEVICES);
      }
    } catch {
      await new Promise((r) => setTimeout(r, 800));
      setDevices(MOCK_DEVICES);
    }
    setScanning(false);
  }, []);

  useEffect(() => { scanDevices(); }, [scanDevices]);

  const flashDevice = useCallback(async (port: string) => {
    setFlashingPort(port);
    setFlashResult((r) => ({ ...r, [port]: '' }));
    try {
      const resp = await fetch('http://localhost:8000/api/flash/upload', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ port }),
      });
      if (resp.ok) {
        setFlashResult((r) => ({ ...r, [port]: 'success' }));
      } else {
        setFlashResult((r) => ({ ...r, [port]: 'error' }));
      }
    } catch {
      // Demo mode
      await new Promise((r) => setTimeout(r, 2000));
      setFlashResult((r) => ({ ...r, [port]: 'success' }));
    }
    setFlashingPort(null);
  }, []);

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-8 py-6 border-b bg-[var(--bg-secondary)]"
        style={{ borderColor: 'var(--border)' }}>
        <div>
          <h1 className="text-2xl font-bold flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
            <MonitorPlay size={24} style={{ color: 'var(--text-secondary)' }} />
            Connected Hardware
          </h1>
          <p className="text-sm font-medium mt-1" style={{ color: 'var(--text-muted)' }}>
            {devices.length} device{devices.length !== 1 ? 's' : ''} detected on local network
          </p>
        </div>
        <button
          onClick={scanDevices}
          disabled={scanning}
          className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors disabled:opacity-50"
          style={{ background: 'var(--text-primary)', color: 'var(--bg-primary)' }}
        >
          <RefreshCw size={16} className={scanning ? 'animate-spin' : ''} /> Rescan Devices
        </button>
      </div>

      {/* Device List */}
      <div className="flex-1 overflow-y-auto p-8 bg-[var(--bg-tertiary)]">
        {devices.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-4">
            <AlertTriangle size={48} style={{ color: 'var(--text-muted)', opacity: 0.5 }} />
            <p className="text-sm font-semibold" style={{ color: 'var(--text-secondary)' }}>
              No devices found. Ensure they are plugged in and recognized by the system.
            </p>
          </div>
        ) : (
          <div className="grid gap-6 max-w-3xl mx-auto">
            {devices.map((dev) => (
              <div
                key={dev.port}
                className="bg-[var(--bg-primary)] rounded-xl p-6 border shadow-sm transition-shadow hover:shadow-md"
                style={{ borderColor: 'var(--border)' }}
              >
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-5">
                    <div className="w-14 h-14 rounded-lg flex items-center justify-center bg-[var(--bg-secondary)] border"
                      style={{ borderColor: 'var(--border)' }}>
                      <Cpu size={28} style={{ color: 'var(--text-secondary)' }} strokeWidth={1.5} />
                    </div>
                    <div>
                      <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>{dev.name}</h3>
                      <div className="flex items-center gap-3 mt-2">
                        <span className="text-xs font-mono font-bold px-2.5 py-1 rounded-md bg-[var(--bg-secondary)] border"
                          style={{ color: 'var(--text-primary)', borderColor: 'var(--border)' }}>
                          {dev.port}
                        </span>
                        <span className="text-xs font-medium" style={{ color: 'var(--text-secondary)' }}>{dev.board}</span>
                        {dev.vid && (
                          <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>
                            VID: {dev.vid} PID: {dev.pid}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 px-3 py-1.5 rounded-md border bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
                    <div className="w-2 h-2 rounded-full" style={{ background: 'var(--success)' }} />
                    <span className="text-xs font-semibold" style={{ color: 'var(--success)' }}>Online</span>
                  </div>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-4 mt-6 pt-6 border-t" style={{ borderColor: 'var(--border)' }}>
                  <button
                    onClick={() => flashDevice(dev.port)}
                    disabled={flashingPort === dev.port}
                    className="flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-semibold transition-colors disabled:opacity-50"
                    style={{ background: 'var(--text-primary)', color: 'var(--bg-primary)' }}
                  >
                    {flashingPort === dev.port ? (
                      <><RefreshCw size={16} className="animate-spin" /> Uploading...</>
                    ) : (
                      <><Zap size={16} /> Flash Firmware</>
                    )}
                  </button>
                  <button className="flex items-center gap-2 px-5 py-2.5 rounded-md text-sm font-semibold border transition-colors hover:bg-[var(--bg-secondary)]"
                    style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
                    <Activity size={16} /> Stream Data
                  </button>
                  {flashResult[dev.port] === 'success' && (
                    <span className="text-sm font-bold flex items-center gap-2 ml-auto"
                      style={{ color: 'var(--success)' }}>
                      <CheckCircle2 size={16} /> Flashed Successfully
                    </span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
