/**
 * IdeaPalette — AI-powered project suggestions based on current hardware graph.
 */
import { useState } from 'react';
import { motion } from 'framer-motion';
import { Lightbulb, Sparkles, ArrowRight, RefreshCw } from 'lucide-react';

interface Idea {
  id: string;
  title: string;
  description: string;
  difficulty: 'beginner' | 'intermediate' | 'advanced';
  components: string[];
}

const STARTER_IDEAS: Idea[] = [
  {
    id: '1', title: 'Add Deep Sleep Mode', difficulty: 'intermediate',
    description: 'Reduce power consumption by 99.5% with ESP32 deep sleep. Wake via timer or GPIO interrupt.',
    components: ['ESP32', 'RTC'],
  },
  {
    id: '2', title: 'OTA Firmware Updates', difficulty: 'intermediate',
    description: 'Enable wireless firmware updates via WiFi. No more USB cables for deployment.',
    components: ['ESP32', 'WiFi', 'HTTP Server'],
  },
  {
    id: '3', title: 'MQTT Telemetry Dashboard', difficulty: 'beginner',
    description: 'Stream sensor data to a cloud MQTT broker. Visualize in real-time with a web dashboard.',
    components: ['ESP32', 'WiFi', 'MQTT', 'Sensor'],
  },
  {
    id: '4', title: 'Multi-Sensor Fusion', difficulty: 'advanced',
    description: 'Combine IMU, barometer, and GPS using a Kalman filter for precise positioning.',
    components: ['MPU6050', 'BMP280', 'GPS Module'],
  },
  {
    id: '5', title: 'BLE Beacon Scanner', difficulty: 'beginner',
    description: 'Scan for nearby Bluetooth Low Energy beacons and log their RSSI signal strength.',
    components: ['ESP32', 'BLE'],
  },
  {
    id: '6', title: 'Watchdog Timer Recovery', difficulty: 'intermediate',
    description: 'Add hardware watchdog to automatically reset the MCU if firmware hangs.',
    components: ['ESP32', 'WDT'],
  },
  {
    id: '7', title: 'NeoPixel Status Ring', difficulty: 'beginner',
    description: 'Use addressable WS2812B LEDs to show system status, WiFi strength, and alerts.',
    components: ['ESP32', 'WS2812B', 'NeoPixel Library'],
  },
  {
    id: '8', title: 'Encrypted Communication', difficulty: 'advanced',
    description: 'Use TLS/SSL for all WiFi communications. Store certs in SPIFFS partition.',
    components: ['ESP32', 'WiFi', 'mbedTLS'],
  },
];

const DIFFICULTY_COLORS = {
  beginner: '#22c55e',
  intermediate: '#d97706',
  advanced: '#ef4444',
};

export default function IdeaPalette() {
  const [ideas] = useState<Idea[]>(STARTER_IDEAS);
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <div className="flex flex-col gap-4 p-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <Lightbulb size={20} style={{ color: '#d97706' }} />
          <div>
            <h2 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
              Project Ideas
            </h2>
            <p className="text-xs font-medium mt-0.5" style={{ color: 'var(--text-muted)' }}>
              AI-powered suggestions to enhance your firmware
            </p>
          </div>
        </div>
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg border text-xs font-bold transition-colors hover:bg-[var(--bg-secondary)]"
          style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      {/* Ideas grid */}
      <div className="grid grid-cols-2 gap-3">
        {ideas.map((idea) => (
          <div key={idea.id}
            onClick={() => setSelectedId(selectedId === idea.id ? null : idea.id)}
            className="text-left border rounded-xl p-4 transition-all cursor-pointer hover:shadow-sm"
            style={{
              borderColor: selectedId === idea.id ? 'var(--text-primary)' : 'var(--border)',
              background: selectedId === idea.id ? 'var(--bg-secondary)' : 'var(--bg-primary)',
            }}>
            <div className="flex items-start justify-between gap-3">
              <div className="flex items-center gap-2">
                <Sparkles size={14} style={{ color: DIFFICULTY_COLORS[idea.difficulty] }} />
                <span className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
                  {idea.title}
                </span>
              </div>
              <span className="px-2 py-0.5 text-xs font-bold rounded-md border shrink-0 capitalize"
                style={{ color: DIFFICULTY_COLORS[idea.difficulty], borderColor: `${DIFFICULTY_COLORS[idea.difficulty]}40`, background: `${DIFFICULTY_COLORS[idea.difficulty]}10` }}>
                {idea.difficulty}
              </span>
            </div>
            <p className="mt-2 text-xs font-medium leading-relaxed" style={{ color: 'var(--text-muted)' }}>
              {idea.description}
            </p>
            <div className="flex items-center gap-1.5 mt-3 flex-wrap">
              {idea.components.map(c => (
                <span key={c} className="px-2 py-0.5 text-xs font-semibold border rounded-md"
                  style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
                  {c}
                </span>
              ))}
            </div>
            {selectedId === idea.id && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                className="mt-3 pt-3 border-t flex items-center gap-1.5 text-xs font-bold transition-colors hover:opacity-80"
                style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}>
                <span>Add to Project</span> <ArrowRight size={14} />
              </motion.div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
