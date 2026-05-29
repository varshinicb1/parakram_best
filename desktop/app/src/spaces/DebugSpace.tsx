/**
 * DebugSpace — Serial Monitor + Protocol Analyzer + Crash Decoder.
 * Industry-leading debug terminal that beats Embedder's CLI serial monitor.
 */
import { useState, useRef, useEffect } from 'react';
import {
  Terminal, Play, Square, Trash2, Download, Zap,
  Radio, Cpu, AlertTriangle, Filter, Send
} from 'lucide-react';

interface SerialLine {
  id: number;
  timestamp: string;
  raw: string;
  type: 'log' | 'error' | 'warning' | 'data' | 'init' | 'memory';
  protocol?: string;
  decoded?: string;
}

interface ProtocolFrame {
  protocol: string;
  direction: string;
  address: string;
  data: string[];
  decoded: string;
  raw: string;
}

interface I2CDevice {
  address: string;
  device: string;
  protocol: string;
}

const API = 'http://localhost:8000/api/analysis';
const BAUD_RATES = [9600, 19200, 38400, 57600, 115200, 230400, 460800, 921600];

export default function DebugSpace() {
  const [tab, setTab] = useState<'serial' | 'protocol' | 'crash'>('serial');
  const [connected, setConnected] = useState(false);
  const [baudRate, setBaudRate] = useState(115200);
  const [lines, setLines] = useState<SerialLine[]>([]);
  const [filter, setFilter] = useState('');
  const [autoScroll, _setAutoScroll] = useState(true);
  const [sendInput, setSendInput] = useState('');
  const [protocolFrames, setProtocolFrames] = useState<ProtocolFrame[]>([]);
  const [i2cDevices, setI2CDevices] = useState<I2CDevice[]>([]);
  const [stats, setStats] = useState<{ total_frames: number; by_protocol: Record<string, number> } | null>(null);
  const terminalRef = useRef<HTMLDivElement>(null);
  const lineCounter = useRef(0);

  useEffect(() => {
    if (autoScroll && terminalRef.current) {
      terminalRef.current.scrollTop = terminalRef.current.scrollHeight;
    }
  }, [lines, autoScroll]);

  // Simulate serial connection for demo
  const toggleConnection = () => {
    if (connected) {
      setConnected(false);
      return;
    }
    setConnected(true);
    // Demo data stream
    const demoLines = [
      { raw: '[BOOT] ESP32 Rev 3.0, Flash: 4MB, PSRAM: 8MB', type: 'init' as const },
      { raw: '[INIT] WiFi: Connecting to "ParakramLab"...', type: 'init' as const },
      { raw: '[INIT] WiFi: Connected! IP: 192.168.1.42', type: 'init' as const },
      { raw: '[OK] MQTT broker connected: mqtt://iot.parakram.dev', type: 'init' as const },
      { raw: 'I2C Write to 0x76: [0xF4, 0x27]', type: 'data' as const },
      { raw: 'I2C Read from 0x76: [0x62, 0x8A, 0x00, 0x52, 0x34, 0x00, 0x96, 0x12]', type: 'data' as const },
      { raw: '[SENSOR] BME280: Temp=23.4°C, Humidity=56%, Pressure=1013.2hPa', type: 'data' as const },
      { raw: '[SENSOR] MPU6050: AccX=0.12g, AccY=-0.03g, AccZ=0.98g', type: 'data' as const },
      { raw: '[MEMORY] Free heap: 245,312 bytes (76% free)', type: 'memory' as const },
      { raw: '[WARN] WiFi RSSI: -72 dBm (weak signal)', type: 'warning' as const },
      { raw: 'SPI MOSI: [0x40, 0x00, 0xFF, 0x00]', type: 'data' as const },
      { raw: '[TASK] SensorRead: 1.2ms execution time', type: 'log' as const },
      { raw: '[MQTT] Published to /sensors/bme280: {"temp":23.4,"hum":56}', type: 'data' as const },
      { raw: 'CAN ID=0x123 DLC=8 Data=[01 02 03 04 05 06 07 08]', type: 'data' as const },
      { raw: '[ERROR] I2C timeout on address 0x68 — check wiring', type: 'error' as const },
      { raw: '[SENSOR] VL53L0X: Distance=342mm', type: 'data' as const },
      { raw: '[MEMORY] Largest free block: 112,640 bytes', type: 'memory' as const },
      { raw: '[OTA] Checking for firmware updates...', type: 'log' as const },
      { raw: '[OTA] Current version: v1.2.3 — Up to date', type: 'log' as const },
    ];
    let idx = 0;
    const interval = setInterval(() => {
      if (idx >= demoLines.length) idx = 0;
      const d = demoLines[idx++];
      const now = new Date();
      setLines(prev => [...prev.slice(-500), {
        id: lineCounter.current++,
        timestamp: `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}.${now.getMilliseconds().toString().padStart(3, '0')}`,
        raw: d.raw,
        type: d.type,
      }]);
    }, 800);
    return () => clearInterval(interval);
  };

  const analyzeProtocol = async () => {
    const text = lines.map(l => l.raw).join('\n');
    try {
      const res = await fetch(`${API}/protocol/decode`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: text }),
      });
      const data = await res.json();
      setProtocolFrames(data.frames || []);
      setStats(data.statistics || null);
      setTab('protocol');
    } catch { /* ignore */ }
  };

  const scanI2C = async () => {
    const text = lines.map(l => l.raw).join('\n');
    try {
      const res = await fetch(`${API}/protocol/i2c-scan`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ data: text }),
      });
      const data = await res.json();
      setI2CDevices(data.devices || []);
    } catch { /* ignore */ }
  };

  const getTypeColor = (type: string) => {
    const colors: Record<string, string> = {
      error: '#ef4444', warning: '#f59e0b', data: '#22c55e',
      init: '#3b82f6', memory: '#8b5cf6', log: 'var(--text-secondary)',
    };
    return colors[type] || 'var(--text-secondary)';
  };

  const filteredLines = lines.filter(l =>
    !filter || l.raw.toLowerCase().includes(filter.toLowerCase()) || l.type === filter.toLowerCase()
  );

  const exportLog = () => {
    const text = lines.map(l => `[${l.timestamp}] ${l.raw}`).join('\n');
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'parakram_serial.log'; a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden animate-fade-in">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
        <div className="flex items-center gap-3">
          <Terminal size={20} style={{ color: 'var(--text-secondary)' }} />
          <h1 className="text-base font-semibold" style={{ color: 'var(--text-primary)' }}>
            Debug Terminal
          </h1>
          <div className="flex items-center gap-2 ml-4 px-2.5 py-1 rounded-md border bg-[var(--bg-primary)]" style={{ borderColor: 'var(--border)' }}>
            <span className="w-2 h-2 rounded-full"
              style={{ background: connected ? 'var(--success)' : 'var(--error)' }} />
            <span className="text-xs font-medium" style={{ color: connected ? 'var(--success)' : 'var(--error)' }}>
              {connected ? 'Connected' : 'Disconnected'}
            </span>
          </div>
        </div>

        <div className="flex items-center gap-3">
          {/* Baud rate selector */}
          <select value={baudRate} onChange={e => setBaudRate(Number(e.target.value))}
            className="bg-[var(--bg-primary)] border rounded-md px-3 py-1.5 text-xs font-mono outline-none"
            style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
            {BAUD_RATES.map(b => <option key={b} value={b}>{b} baud</option>)}
          </select>

          <button onClick={toggleConnection}
            className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold rounded-md transition-colors"
            style={{ 
              background: connected ? 'var(--error)' : 'var(--text-primary)', 
              color: connected ? 'white' : 'var(--bg-primary)' 
            }}>
            {connected ? <><Square size={14} /> Stop</> : <><Play size={14} /> Connect</>}
          </button>

          <div className="h-6 w-px bg-[var(--border)] mx-1" />

          <button onClick={() => setLines([])} className="p-1.5 rounded transition-colors hover:bg-[var(--bg-tertiary)]" style={{ color: 'var(--text-muted)' }} title="Clear">
            <Trash2 size={16} />
          </button>
          <button onClick={exportLog} className="p-1.5 rounded transition-colors hover:bg-[var(--bg-tertiary)]" style={{ color: 'var(--text-muted)' }} title="Export">
            <Download size={16} />
          </button>
          <button onClick={analyzeProtocol} className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold border rounded-md transition-colors hover:bg-[var(--bg-tertiary)]"
            style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
            <Radio size={14} /> Analyze
          </button>
          <button onClick={scanI2C} className="flex items-center gap-2 px-3 py-1.5 text-xs font-semibold border rounded-md transition-colors hover:bg-[var(--bg-tertiary)]"
            style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
            <Cpu size={14} /> I2C Scan
          </button>
        </div>
      </div>

      {/* Tab bar */}
      <div className="flex items-center border-b px-2 pt-2 bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
        {([['serial', 'Serial Monitor', Terminal], ['protocol', 'Protocol Analyzer', Radio], ['crash', 'Crash Decoder', AlertTriangle]] as const).map(([id, label, Icon]) => (
          <button key={id} onClick={() => setTab(id)}
            className="flex items-center gap-2 px-4 py-2.5 text-xs font-semibold border-b-2 transition-colors hover:bg-[var(--bg-tertiary)] rounded-t-lg"
            style={{
              borderBottomColor: tab === id ? 'var(--text-primary)' : 'transparent',
              color: tab === id ? 'var(--text-primary)' : 'var(--text-muted)',
              background: tab === id ? 'var(--bg-primary)' : 'transparent',
            }}>
            <Icon size={14} /> {label}
          </button>
        ))}

        {/* Stats badge */}
        {stats && (
          <div className="ml-auto px-4 flex items-center gap-4 text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
            {Object.entries(stats.by_protocol).map(([proto, count]) => (
              <span key={proto}>{proto}: <span style={{ color: 'var(--text-primary)' }}>{count}</span></span>
            ))}
          </div>
        )}
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-3 px-4 py-2.5 border-b bg-[var(--bg-primary)]" style={{ borderColor: 'var(--border)' }}>
        <Filter size={14} style={{ color: 'var(--text-muted)' }} />
        <input value={filter} onChange={e => setFilter(e.target.value)}
          placeholder="Filter: error, warning, data, init, memory, or text..."
          className="flex-1 bg-transparent text-xs font-mono outline-none"
          style={{ color: 'var(--text-primary)' }} />
        <span className="text-xs font-medium" style={{ color: 'var(--text-muted)' }}>
          {filteredLines.length} / {lines.length} lines
        </span>
      </div>

      {/* Content */}
      <div className="flex-1 flex overflow-hidden bg-[var(--bg-primary)]">
        {/* Main terminal */}
        <div className="flex-1 flex flex-col min-w-0">
          {tab === 'serial' && (
            <>
              <div ref={terminalRef} className="flex-1 overflow-y-auto p-4 font-mono text-xs leading-relaxed">
                {filteredLines.map(line => (
                  <div key={line.id} className="flex gap-4 hover:bg-[var(--bg-tertiary)] transition-colors py-1 px-2 rounded">
                    <span className="shrink-0" style={{ color: 'var(--text-muted)' }}>{line.timestamp}</span>
                    <span style={{ color: getTypeColor(line.type) }}>{line.raw}</span>
                  </div>
                ))}
                {lines.length === 0 && (
                  <div className="text-center py-16 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                    Click Connect to start serial monitor
                  </div>
                )}
              </div>

              {/* Send input */}
              <div className="flex items-center gap-3 px-4 py-3 border-t bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
                <Send size={14} style={{ color: 'var(--text-muted)' }} />
                <input value={sendInput} onChange={e => setSendInput(e.target.value)}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && sendInput.trim()) {
                      setLines(prev => [...prev, {
                        id: lineCounter.current++,
                        timestamp: new Date().toLocaleTimeString('en-US', { hour12: false }),
                        raw: `>> ${sendInput}`, type: 'log',
                      }]);
                      setSendInput('');
                    }
                  }}
                  placeholder="Send command..." className="flex-1 bg-[var(--bg-primary)] border rounded-md px-3 py-1.5 text-xs font-mono outline-none focus:border-[var(--text-primary)] transition-colors"
                  style={{ color: 'var(--text-primary)', borderColor: 'var(--border)' }} />
              </div>
            </>
          )}

          {tab === 'protocol' && (
            <div className="flex-1 overflow-y-auto p-6 space-y-2 bg-[var(--bg-tertiary)]">
              {protocolFrames.length === 0 ? (
                <div className="text-center py-16 text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                  Click Analyze to decode protocols from serial data
                </div>
              ) : protocolFrames.map((frame, i) => (
                <div key={i} className="flex items-center gap-4 px-4 py-2 border rounded-md text-xs font-mono shadow-sm bg-[var(--bg-primary)]"
                  style={{ borderColor: 'var(--border)' }}>
                  <span className="text-xs font-bold px-2 py-1 rounded-md"
                    style={{
                      background: 'var(--bg-tertiary)',
                      color: frame.protocol === 'I2C' ? '#3b82f6' : frame.protocol === 'SPI' ? '#8b5cf6' : frame.protocol === 'CAN' ? '#f59e0b' : '#22c55e',
                    }}>{frame.protocol}</span>
                  {frame.direction && <span style={{ color: 'var(--text-muted)' }}>{frame.direction}</span>}
                  {frame.address && <span style={{ color: 'var(--text-primary)', fontWeight: 'bold' }}>{frame.address}</span>}
                  <span className="flex-1 truncate" style={{ color: 'var(--text-secondary)' }}>{frame.raw}</span>
                  {frame.decoded && <span className="text-xs font-medium" style={{ color: 'var(--success)' }}>{frame.decoded}</span>}
                </div>
              ))}
            </div>
          )}

          {tab === 'crash' && (
            <div className="flex-1 overflow-y-auto p-8 bg-[var(--bg-tertiary)]">
              <div className="text-center py-12 space-y-6 bg-[var(--bg-primary)] border rounded-xl shadow-sm max-w-2xl mx-auto" style={{ borderColor: 'var(--border)' }}>
                <AlertTriangle size={48} style={{ color: 'var(--warning)', margin: '0 auto' }} />
                <div>
                  <h3 className="text-lg font-bold" style={{ color: 'var(--text-primary)' }}>Crash Decoder</h3>
                  <p className="text-sm mt-2 max-w-sm mx-auto" style={{ color: 'var(--text-muted)' }}>
                    Paste a crash dump (ESP32 Guru Meditation, STM32 HardFault) to decode the stack trace.
                  </p>
                </div>
                <textarea placeholder="Paste crash dump here..."
                  className="w-full max-w-lg mx-auto h-40 bg-[var(--bg-secondary)] border rounded-md p-4 font-mono text-xs outline-none resize-none focus:border-[var(--text-primary)] transition-colors block"
                  style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }} />
                <button className="flex items-center justify-center gap-2 px-6 py-2.5 mx-auto text-sm font-semibold rounded-md transition-colors"
                  style={{ background: 'var(--warning)', color: '#000' }}>
                  <Zap size={16} /> Decode Stack Trace
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Right: I2C Device Panel */}
        {i2cDevices.length > 0 && (
          <div className="w-64 border-l overflow-y-auto shrink-0 bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
            <div className="px-4 py-3 border-b bg-[var(--bg-tertiary)]" style={{ borderColor: 'var(--border)' }}>
              <span className="text-sm font-semibold" style={{ color: 'var(--text-muted)' }}>
                I2C Devices ({i2cDevices.length})
              </span>
            </div>
            {i2cDevices.map((dev, i) => (
              <div key={i} className="px-4 py-3 border-b border-transparent hover:bg-[var(--bg-tertiary)] transition-colors" style={{ borderColor: 'var(--border)' }}>
                <div className="flex items-center justify-between">
                  <span className="text-sm font-mono font-bold" style={{ color: 'var(--text-primary)' }}>{dev.address}</span>
                  <Cpu size={14} style={{ color: 'var(--text-muted)' }} />
                </div>
                <p className="text-xs mt-1" style={{ color: 'var(--text-secondary)' }}>{dev.device}</p>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
