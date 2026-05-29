/**
 * ResourcePalette — Quick-access palette for datasheets, pinout diagrams, and library docs.
 * Searchable, categorized by component type.
 */
import { useState } from 'react';
import { BookOpen, Search, ExternalLink, Cpu, Thermometer, Gauge, Zap, Radio } from 'lucide-react';

interface Resource {
  id: string;
  name: string;
  category: string;
  type: 'datasheet' | 'pinout' | 'library' | 'guide';
  url: string;
  description: string;
}

const RESOURCES: Resource[] = [
  { id: 'esp32', name: 'ESP32 Technical Reference', category: 'MCU', type: 'datasheet', url: 'https://www.espressif.com/sites/default/files/documentation/esp32_technical_reference_manual_en.pdf', description: 'Complete ESP32 technical reference manual' },
  { id: 'esp32-pinout', name: 'ESP32 DevKit Pinout', category: 'MCU', type: 'pinout', url: 'https://docs.espressif.com/projects/esp-idf/en/latest/esp32/hw-reference/esp32/get-started-devkitc.html', description: '30/38-pin DevKit pinout diagram' },
  { id: 'bme280', name: 'BME280 Datasheet', category: 'Sensor', type: 'datasheet', url: 'https://www.bosch-sensortec.com/media/boschsensortec/downloads/datasheets/bst-bme280-ds002.pdf', description: 'Temperature, humidity, pressure sensor' },
  { id: 'mpu6050', name: 'MPU6050 Datasheet', category: 'Sensor', type: 'datasheet', url: 'https://invensense.tdk.com/wp-content/uploads/2015/02/MPU-6000-Datasheet1.pdf', description: '6-axis accelerometer + gyroscope' },
  { id: 'ssd1306', name: 'SSD1306 OLED Datasheet', category: 'Display', type: 'datasheet', url: 'https://cdn-shop.adafruit.com/datasheets/SSD1306.pdf', description: '128x64 OLED display controller' },
  { id: 'nrf24l01', name: 'nRF24L01 Datasheet', category: 'Communication', type: 'datasheet', url: 'https://www.sparkfun.com/datasheets/Components/SMD/nRF24L01Pluss_Preliminary_Product_Specification_v1_0.pdf', description: '2.4GHz wireless transceiver' },
  { id: 'pio-docs', name: 'PlatformIO Documentation', category: 'Tools', type: 'guide', url: 'https://docs.platformio.org/en/latest/', description: 'Build system & library management' },
  { id: 'arduino-ref', name: 'Arduino Language Reference', category: 'Tools', type: 'guide', url: 'https://www.arduino.cc/reference/en/', description: 'Core Arduino functions & syntax' },
  { id: 'adafruit-neopixel', name: 'Adafruit NeoPixel Library', category: 'Library', type: 'library', url: 'https://github.com/adafruit/Adafruit_NeoPixel', description: 'WS2812B addressable LED driver' },
  { id: 'pubsubclient', name: 'PubSubClient (MQTT)', category: 'Library', type: 'library', url: 'https://github.com/knolleary/pubsubclient', description: 'MQTT client for Arduino' },
];

const CATEGORY_ICONS: Record<string, typeof Cpu> = {
  MCU: Cpu,
  Sensor: Thermometer,
  Display: Gauge,
  Communication: Radio,
  Tools: Zap,
  Library: BookOpen,
};

export default function ResourcePalette() {
  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('ALL');

  const categories = ['ALL', ...new Set(RESOURCES.map(r => r.category))];

  const filtered = RESOURCES.filter(r => {
    const matchesSearch = !search || r.name.toLowerCase().includes(search.toLowerCase()) || r.description.toLowerCase().includes(search.toLowerCase());
    const matchesCategory = selectedCategory === 'ALL' || r.category === selectedCategory;
    return matchesSearch && matchesCategory;
  });

  return (
    <div className="flex flex-col gap-4 p-5">
      {/* Header */}
      <div className="flex items-center gap-3">
        <div className="p-2 border rounded-lg bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
          <BookOpen size={18} style={{ color: 'var(--text-primary)' }} />
        </div>
        <div>
          <h2 className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
            Resource Palette
          </h2>
          <p className="text-xs font-medium mt-0.5" style={{ color: 'var(--text-muted)' }}>
            Quick access to datasheets and libraries
          </p>
        </div>
      </div>

      {/* Search */}
      <div className="relative mt-2">
        <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2" style={{ color: 'var(--text-muted)' }} />
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search datasheets, libraries..."
          className="w-full bg-[var(--bg-secondary)] border rounded-xl pl-9 pr-3 py-2 text-xs font-medium outline-none focus:border-[var(--text-primary)] transition-colors shadow-sm"
          style={{ borderColor: 'var(--border)', color: 'var(--text-primary)' }}
        />
      </div>

      {/* Category filter */}
      <div className="flex items-center gap-1.5 flex-wrap">
        {categories.map(cat => (
          <button key={cat} onClick={() => setSelectedCategory(cat)}
            className="px-2.5 py-1 text-xs font-bold rounded-md border transition-colors shadow-sm"
            style={{
              borderColor: selectedCategory === cat ? 'var(--text-primary)' : 'var(--border)',
              color: selectedCategory === cat ? 'var(--bg-primary)' : 'var(--text-muted)',
              background: selectedCategory === cat ? 'var(--text-primary)' : 'transparent',
            }}>
            {cat}
          </button>
        ))}
      </div>

      {/* Resources list */}
      <div className="flex flex-col gap-2">
        {filtered.map((r) => {
          const Icon = CATEGORY_ICONS[r.category] || BookOpen;
          return (
            <a key={r.id}
              href={r.url} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-3 p-3 border rounded-xl transition-all hover:shadow-sm hover:border-[var(--text-muted)] bg-[var(--bg-primary)] group"
              style={{ borderColor: 'var(--border)', textDecoration: 'none', color: 'var(--text-primary)' }}>
              <div className="p-2 border rounded-lg bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
                <Icon size={16} style={{ color: 'var(--text-secondary)' }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="text-xs font-bold truncate">{r.name}</div>
                <div className="text-[10px] font-medium mt-0.5 uppercase" style={{ color: 'var(--text-muted)' }}>
                  {r.type} · {r.description}
                </div>
              </div>
              <div className="w-8 h-8 rounded-lg border flex items-center justify-center bg-[var(--bg-secondary)] opacity-0 group-hover:opacity-100 transition-opacity" style={{ borderColor: 'var(--border)' }}>
                <ExternalLink size={14} style={{ color: 'var(--text-primary)' }} />
              </div>
            </a>
          );
        })}
      </div>
    </div>
  );
}
