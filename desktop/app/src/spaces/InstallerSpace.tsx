/**
 * InstallerSpace — Toolchain & library auto-installer engine UI.
 * Manages PlatformIO, ESP-IDF, Arduino CLI, and library installations.
 */
import { useState } from 'react';
import {
  Download, Package, Wrench, Check, Loader2,
  HardDrive
} from 'lucide-react';

interface Toolchain {
  id: string;
  name: string;
  description: string;
  version: string;
  installed: boolean;
  installing: boolean;
  size: string;
}

interface Library {
  id: string;
  name: string;
  author: string;
  version: string;
  description: string;
  installed: boolean;
  installing: boolean;
}

export default function InstallerSpace() {
  const [activeTab, setActiveTab] = useState<'toolchains' | 'libraries'>('toolchains');

  const [toolchains, setToolchains] = useState<Toolchain[]>([
    { id: 'pio', name: 'PlatformIO Core', description: 'Multi-platform build system for embedded development', version: '6.1.15', installed: true, installing: false, size: '280 MB' },
    { id: 'esp-idf', name: 'ESP-IDF', description: 'Espressif IoT Development Framework (official)', version: '5.2.1', installed: false, installing: false, size: '1.2 GB' },
    { id: 'arduino-cli', name: 'Arduino CLI', description: 'Arduino command-line interface for builds and uploads', version: '1.0.4', installed: false, installing: false, size: '45 MB' },
    { id: 'gcc-arm', name: 'ARM GCC Toolchain', description: 'GNU Arm Embedded Toolchain for Cortex-M/R processors', version: '13.2', installed: false, installing: false, size: '450 MB' },
    { id: 'openocd', name: 'OpenOCD', description: 'Open On-Chip Debugger for JTAG/SWD debugging', version: '0.12.0', installed: false, installing: false, size: '25 MB' },
    { id: 'stm32cube', name: 'STM32CubeMX', description: 'STMicroelectronics MCU configuration and code generator', version: '6.10', installed: false, installing: false, size: '800 MB' },
  ]);

  const [libraries, setLibraries] = useState<Library[]>([
    { id: 'wifi', name: 'WiFi', author: 'Arduino', version: '1.2.7', description: 'WiFi connectivity library', installed: true, installing: false },
    { id: 'wire', name: 'Wire (I2C)', author: 'Arduino', version: '2.0.0', description: 'I2C communication protocol', installed: true, installing: false },
    { id: 'spi', name: 'SPI', author: 'Arduino', version: '2.0.0', description: 'SPI communication protocol', installed: true, installing: false },
    { id: 'adafruit-bme280', name: 'Adafruit BME280', author: 'Adafruit', version: '2.2.4', description: 'BME280 temperature/humidity/pressure sensor driver', installed: false, installing: false },
    { id: 'pubsubclient', name: 'PubSubClient', author: 'Nick O\'Leary', version: '2.8', description: 'MQTT client for Arduino', installed: false, installing: false },
    { id: 'adafruit-neopixel', name: 'Adafruit NeoPixel', author: 'Adafruit', version: '1.12.3', description: 'WS2812B addressable LED driver', installed: false, installing: false },
    { id: 'arduinojson', name: 'ArduinoJSON', author: 'Benoit Blanchon', version: '7.1.0', description: 'JSON serialization/deserialization', installed: false, installing: false },
    { id: 'fastled', name: 'FastLED', author: 'Daniel Garcia', version: '3.7.0', description: 'High-performance LED animation library', installed: false, installing: false },
    { id: 'esp-async-webserver', name: 'ESPAsyncWebServer', author: 'Me-No-Dev', version: '1.2.7', description: 'Async HTTP/WebSocket server for ESP', installed: false, installing: false },
    { id: 'tft-espi', name: 'TFT_eSPI', author: 'Bodmer', version: '2.5.43', description: 'High-performance TFT LCD display library', installed: false, installing: false },
  ]);

  const [installProgress, setInstallProgress] = useState<Record<string, number>>({});

  const simulateInstall = (id: string, type: 'toolchain' | 'library') => {
    if (type === 'toolchain') {
      setToolchains(prev => prev.map(t => t.id === id ? { ...t, installing: true } : t));
    } else {
      setLibraries(prev => prev.map(l => l.id === id ? { ...l, installing: true } : l));
    }

    let progress = 0;
    const interval = setInterval(() => {
      progress += Math.random() * 15 + 5;
      if (progress >= 100) {
        progress = 100;
        clearInterval(interval);
        if (type === 'toolchain') {
          setToolchains(prev => prev.map(t => t.id === id ? { ...t, installing: false, installed: true } : t));
        } else {
          setLibraries(prev => prev.map(l => l.id === id ? { ...l, installing: false, installed: true } : l));
        }
      }
      setInstallProgress(prev => ({ ...prev, [id]: progress }));
    }, 300);
  };

  const installAllLibraries = () => {
    libraries.filter(l => !l.installed && !l.installing).forEach(l => {
      simulateInstall(l.id, 'library');
    });
  };

  const installedToolchains = toolchains.filter(t => t.installed).length;
  const installedLibraries = libraries.filter(l => l.installed).length;

  return (
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-6xl mx-auto px-8 py-10">
        {/* Header */}
        <div className="flex flex-col md:flex-row md:items-center justify-between mb-8 gap-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-3" style={{ color: 'var(--text-primary)' }}>
              <Download size={24} style={{ color: 'var(--text-primary)' }} />
              Universal Installer
            </h1>
            <p className="text-sm font-medium mt-1" style={{ color: 'var(--text-muted)' }}>
              Manage system toolchains, frameworks, and shared libraries.
            </p>
          </div>
          <div className="flex items-center gap-4 text-sm font-semibold px-4 py-2 bg-[var(--bg-secondary)] border rounded-lg" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
            <span><strong style={{ color: 'var(--text-primary)' }}>{installedToolchains} / {toolchains.length}</strong> Toolchains</span>
            <span className="w-1 h-1 rounded-full" style={{ background: 'var(--border)' }} />
            <span><strong style={{ color: 'var(--text-primary)' }}>{installedLibraries} / {libraries.length}</strong> Libraries</span>
          </div>
        </div>

        {/* Tab nav & Actions */}
        <div className="flex items-center justify-between mb-8 border-b" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-2">
            {([['toolchains', 'Compiler Toolchains', Wrench], ['libraries', 'Global Libraries', Package]] as const).map(([id, label, Icon]) => (
              <button key={id} onClick={() => setActiveTab(id)}
                className="flex items-center gap-2 px-5 py-3 text-sm font-semibold border-b-2 transition-colors hover:bg-[var(--bg-secondary)] rounded-t-lg"
                style={{
                  borderBottomColor: activeTab === id ? 'var(--text-primary)' : 'transparent',
                  color: activeTab === id ? 'var(--text-primary)' : 'var(--text-muted)',
                }}>
                <Icon size={16} /> {label}
              </button>
            ))}
          </div>

          {activeTab === 'libraries' && (
            <button onClick={installAllLibraries}
              className="flex items-center gap-2 px-4 py-2 rounded-md text-sm font-semibold transition-colors border shadow-sm mb-2"
              style={{ borderColor: 'var(--text-primary)', background: 'var(--text-primary)', color: 'var(--bg-primary)' }}>
              <Download size={16} /> Install All Missing
            </button>
          )}
        </div>

        {/* Toolchains */}
        {activeTab === 'toolchains' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {toolchains.map(tc => (
              <div key={tc.id}
                className="bg-[var(--bg-primary)] border rounded-xl p-6 flex flex-col transition-shadow hover:shadow-md"
                style={{ borderColor: tc.installed ? 'var(--text-primary)' : 'var(--border)' }}>
                
                <div className="flex items-start justify-between mb-4">
                  <div className="w-12 h-12 flex items-center justify-center rounded-lg bg-[var(--bg-secondary)] border shrink-0"
                    style={{ borderColor: tc.installed ? 'var(--text-primary)' : 'var(--border)', color: tc.installed ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                    {tc.installed ? <Check size={24} /> : <HardDrive size={24} />}
                  </div>
                  
                  {tc.installed ? (
                    <span className="text-xs font-bold flex items-center gap-1 px-3 py-1 bg-[var(--bg-secondary)] border rounded-full" style={{ color: 'var(--text-primary)', borderColor: 'var(--text-primary)' }}>
                       Installed
                    </span>
                  ) : tc.installing ? (
                    <span className="text-xs font-bold flex items-center gap-2 px-3 py-1 bg-[var(--bg-secondary)] border rounded-full" style={{ color: 'var(--text-primary)', borderColor: 'var(--border)' }}>
                      <Loader2 size={14} className="animate-spin" /> {(installProgress[tc.id] || 0).toFixed(0)}%
                    </span>
                  ) : (
                    <button onClick={() => simulateInstall(tc.id, 'toolchain')}
                      className="flex items-center gap-2 px-4 py-1.5 rounded-full border text-xs font-bold transition-colors hover:bg-[var(--bg-secondary)]"
                      style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
                      <Download size={14} /> Install
                    </button>
                  )}
                </div>

                <div className="flex-1">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="text-base font-bold" style={{ color: 'var(--text-primary)' }}>{tc.name}</span>
                    <span className="text-xs font-mono px-2 py-0.5 bg-[var(--bg-secondary)] rounded-md border" style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>v{tc.version}</span>
                    <span className="text-xs font-medium px-2 py-0.5 bg-[var(--bg-secondary)] rounded-md border" style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>{tc.size}</span>
                  </div>
                  <p className="text-sm leading-relaxed" style={{ color: 'var(--text-muted)' }}>{tc.description}</p>
                </div>

                {tc.installing && (
                  <div className="mt-5 h-1.5 rounded-full overflow-hidden bg-[var(--bg-secondary)] border" style={{ borderColor: 'var(--border)' }}>
                    <div className="h-full bg-[var(--text-primary)] transition-all duration-300 ease-out" style={{ width: `${installProgress[tc.id] || 0}%` }} />
                  </div>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Libraries */}
        {activeTab === 'libraries' && (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {libraries.map(lib => (
              <div key={lib.id}
                className="bg-[var(--bg-primary)] border rounded-xl p-5 flex items-start gap-4 transition-all hover:border-[var(--text-muted)] hover:shadow-sm"
                style={{ borderColor: lib.installed ? 'var(--text-primary)' : 'var(--border)' }}>
                
                <div className="w-10 h-10 flex items-center justify-center rounded-lg bg-[var(--bg-secondary)] border shrink-0"
                  style={{ borderColor: lib.installed ? 'var(--text-primary)' : 'var(--border)', color: lib.installed ? 'var(--text-primary)' : 'var(--text-muted)' }}>
                  {lib.installed ? <Check size={20} /> : <Package size={20} />}
                </div>

                <div className="flex-1 min-w-0">
                  <div className="flex justify-between items-start mb-1 gap-2">
                    <div className="flex flex-col min-w-0">
                      <span className="text-sm font-bold truncate" style={{ color: 'var(--text-primary)' }}>{lib.name}</span>
                      <span className="text-xs font-mono" style={{ color: 'var(--text-muted)' }}>v{lib.version} · {lib.author}</span>
                    </div>

                    <div className="shrink-0 flex items-center">
                      {lib.installed ? (
                        <span className="text-xs font-semibold px-2 py-1 bg-[var(--bg-secondary)] rounded-md border" style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>Installed</span>
                      ) : lib.installing ? (
                        <Loader2 size={18} className="animate-spin" style={{ color: 'var(--text-primary)' }} />
                      ) : (
                        <button onClick={() => simulateInstall(lib.id, 'library')}
                          className="text-xs font-semibold px-3 py-1 rounded-md border hover:bg-[var(--bg-secondary)] transition-colors" 
                          style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
                          Install
                        </button>
                      )}
                    </div>
                  </div>
                  
                  <p className="text-xs" style={{ color: 'var(--text-secondary)' }}>{lib.description}</p>
                  
                  {lib.installing && (
                    <div className="mt-3 h-1 rounded-full overflow-hidden bg-[var(--bg-secondary)] border" style={{ borderColor: 'var(--border)' }}>
                      <div className="h-full bg-[var(--text-primary)] transition-all duration-300 ease-out" style={{ width: `${installProgress[lib.id] || 0}%` }} />
                    </div>
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
