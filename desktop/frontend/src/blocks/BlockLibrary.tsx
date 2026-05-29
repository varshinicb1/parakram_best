/**
 * BlockLibrary -- Sidebar with categorized hardware blocks for drag-and-drop.
 * Expanded with IoT, Security, Audio, Display, I2C Sensors, and FreeRTOS blocks.
 */

import { type DragEvent, useState } from 'react';
import { BLOCK_CATEGORIES, type Block } from '../types/Block';

// ─── Full Block Library ─────────────────────────────────────

const LIBRARY_BLOCKS: Block[] = [
    // ── Sensors ──────────────────────────────────────────
    {
        id: 'dht22_temperature_humidity', name: 'DHT22 Sensor', category: 'sensor',
        description: 'Temperature & Humidity sensor',
        inputs: [], outputs: [
            { name: 'temperature', data_type: 'float', description: 'Celsius' },
            { name: 'humidity', data_type: 'float', description: 'Percentage' },
        ],
        configuration: [{ key: 'pin', label: 'Data Pin', value_type: 'int', default: '4' }],
        code_template: 'dht22_template', icon: '🌡️', color: '#ef4444',
    },
    {
        id: 'bmp280_pressure', name: 'BMP280 Pressure', category: 'sensor',
        description: 'Barometric pressure & altitude',
        inputs: [], outputs: [
            { name: 'pressure', data_type: 'float' },
            { name: 'temperature', data_type: 'float' },
            { name: 'altitude', data_type: 'float' },
        ],
        configuration: [{ key: 'i2c_address', label: 'I2C Address', value_type: 'string', default: '0x76' }],
        code_template: 'bmp280_template', icon: '📊', color: '#3b82f6',
    },
    {
        id: 'bme280', name: 'BME280', category: 'sensor',
        description: 'Temp + humidity + pressure with I2C retry init',
        inputs: [], outputs: [
            { name: 'temperature', data_type: 'float' },
            { name: 'humidity', data_type: 'float' },
            { name: 'pressure', data_type: 'float' },
            { name: 'altitude', data_type: 'float' },
        ],
        configuration: [
            { key: 'i2c_address', label: 'I2C Address', value_type: 'string', default: '0x76' },
            { key: 'sda_pin', label: 'SDA Pin', value_type: 'int', default: '21' },
            { key: 'scl_pin', label: 'SCL Pin', value_type: 'int', default: '22' },
            { key: 'sea_level_hpa', label: 'Sea Level hPa', value_type: 'float', default: '1013.25' },
        ],
        code_template: 'bme280_template', icon: '🌤️', color: '#0ea5e9',
    },
    {
        id: 'mpu6050', name: 'MPU6050 IMU', category: 'sensor',
        description: '6-axis accelerometer + gyroscope',
        inputs: [], outputs: [
            { name: 'accel_x', data_type: 'float' }, { name: 'accel_y', data_type: 'float' },
            { name: 'accel_z', data_type: 'float' }, { name: 'gyro_x', data_type: 'float' },
            { name: 'gyro_y', data_type: 'float' }, { name: 'gyro_z', data_type: 'float' },
        ],
        configuration: [
            { key: 'i2c_address', label: 'I2C Address', value_type: 'string', default: '0x68' },
            { key: 'accel_range', label: 'Accel Range (g)', value_type: 'int', default: '2' },
        ],
        code_template: 'mpu6050_template', icon: '🧭', color: '#f59e0b',
    },
    {
        id: 'bh1750', name: 'BH1750 Light', category: 'sensor',
        description: 'Ambient light sensor (lux)',
        inputs: [], outputs: [{ name: 'lux', data_type: 'float' }],
        configuration: [{ key: 'i2c_address', label: 'I2C Address', value_type: 'string', default: '0x23' }],
        code_template: 'bh1750_template', icon: '💡', color: '#eab308',
    },
    {
        id: 'ads1115', name: 'ADS1115 ADC', category: 'sensor',
        description: '16-bit 4-channel ADC',
        inputs: [], outputs: [
            { name: 'channel_0', data_type: 'float' }, { name: 'channel_1', data_type: 'float' },
            { name: 'channel_2', data_type: 'float' }, { name: 'channel_3', data_type: 'float' },
        ],
        configuration: [
            { key: 'i2c_address', label: 'I2C Address', value_type: 'string', default: '0x48' },
            { key: 'gain', label: 'Gain', value_type: 'string', default: 'GAIN_ONE' },
        ],
        code_template: 'ads1115_template', icon: '📈', color: '#22c55e',
    },
    {
        id: 'ina219', name: 'INA219 Power', category: 'sensor',
        description: 'Current/voltage/power monitor',
        inputs: [], outputs: [
            { name: 'bus_voltage', data_type: 'float' }, { name: 'current_ma', data_type: 'float' },
            { name: 'power_mw', data_type: 'float' },
        ],
        configuration: [{ key: 'i2c_address', label: 'I2C Address', value_type: 'string', default: '0x40' }],
        code_template: 'ina219_template', icon: '⚡', color: '#ef4444',
    },
    {
        id: 'vl53l0x', name: 'VL53L0X Distance', category: 'sensor',
        description: 'Time-of-Flight laser distance (up to 2m)',
        inputs: [], outputs: [
            { name: 'distance_mm', data_type: 'int' }, { name: 'out_of_range', data_type: 'bool' },
        ],
        configuration: [{ key: 'i2c_address', label: 'I2C Address', value_type: 'string', default: '0x29' }],
        code_template: 'vl53l0x_template', icon: '📏', color: '#6366f1',
    },

    // ── Communication ────────────────────────────────────
    {
        id: 'wifi_station', name: 'WiFi Station', category: 'communication',
        description: 'Connect to WiFi network',
        inputs: [], outputs: [
            { name: 'connected', data_type: 'bool' }, { name: 'ip_address', data_type: 'string' },
        ],
        configuration: [
            { key: 'ssid', label: 'SSID', value_type: 'string' },
            { key: 'password', label: 'Password', value_type: 'string' },
        ],
        code_template: 'wifi_template', icon: '📶', color: '#8b5cf6',
    },
    {
        id: 'mqtt_client', name: 'MQTT Client', category: 'communication',
        description: 'MQTT publish & subscribe',
        inputs: [{ name: 'data', data_type: 'any' }, { name: 'wifi_connected', data_type: 'bool' }],
        outputs: [{ name: 'message', data_type: 'string' }, { name: 'connected', data_type: 'bool' }],
        configuration: [
            { key: 'broker', label: 'Broker', value_type: 'string' },
            { key: 'topic', label: 'Topic', value_type: 'string', default: 'parakram/data' },
        ],
        code_template: 'mqtt_template', icon: '☁️', color: '#06b6d4',
    },
    {
        id: 'http_client', name: 'HTTP Client', category: 'communication',
        description: 'HTTP GET/POST with JSON parsing',
        inputs: [{ name: 'data', data_type: 'any' }, { name: 'wifi_connected', data_type: 'bool' }],
        outputs: [
            { name: 'response', data_type: 'string' }, { name: 'status_code', data_type: 'int' },
        ],
        configuration: [
            { key: 'url', label: 'URL', value_type: 'string', default: 'http://api.example.com/data' },
            { key: 'method', label: 'Method', value_type: 'string', default: 'POST' },
        ],
        code_template: 'http_template', icon: '🌐', color: '#0ea5e9',
    },
    {
        id: 'websocket_client', name: 'WebSocket', category: 'communication',
        description: 'Persistent bidirectional WebSocket',
        inputs: [{ name: 'message_out', data_type: 'string' }],
        outputs: [{ name: 'message_in', data_type: 'string' }, { name: 'connected', data_type: 'bool' }],
        configuration: [
            { key: 'ws_url', label: 'WS URL', value_type: 'string', default: 'ws://192.168.1.100:8080' },
        ],
        code_template: 'websocket_template', icon: '🔌', color: '#8b5cf6',
    },
    {
        id: 'ota_updater', name: 'OTA Updates', category: 'communication',
        description: 'Over-the-air firmware updates',
        inputs: [{ name: 'wifi_connected', data_type: 'bool' }],
        outputs: [{ name: 'updating', data_type: 'bool' }, { name: 'progress', data_type: 'float' }],
        configuration: [
            { key: 'hostname', label: 'Hostname', value_type: 'string', default: 'parakram-device' },
        ],
        code_template: 'ota_template', icon: '📥', color: '#22c55e',
    },
    {
        id: 'ntp_client', name: 'NTP Time Sync', category: 'communication',
        description: 'Network time with timezone',
        inputs: [{ name: 'wifi_connected', data_type: 'bool' }],
        outputs: [
            { name: 'epoch', data_type: 'int' }, { name: 'time_string', data_type: 'string' },
        ],
        configuration: [
            { key: 'ntp_server', label: 'NTP Server', value_type: 'string', default: 'pool.ntp.org' },
            { key: 'gmt_offset', label: 'GMT Offset (sec)', value_type: 'int', default: '19800' },
        ],
        code_template: 'ntp_template', icon: '🕐', color: '#6366f1',
    },
    {
        id: 'ble_server', name: 'BLE Server', category: 'communication',
        description: 'Bluetooth LE GATT server',
        inputs: [{ name: 'data', data_type: 'any' }],
        outputs: [{ name: 'connected', data_type: 'bool' }, { name: 'received', data_type: 'string' }],
        configuration: [
            { key: 'device_name', label: 'BLE Name', value_type: 'string', default: 'Parakram-BLE' },
        ],
        code_template: 'ble_template', icon: '🔵', color: '#3b82f6',
    },

    // ── Actuators ────────────────────────────────────────
    {
        id: 'led_output', name: 'LED Output', category: 'actuator',
        description: 'Control an LED or digital pin',
        inputs: [{ name: 'trigger', data_type: 'bool' }], outputs: [],
        configuration: [{ key: 'pin', label: 'GPIO Pin', value_type: 'int', default: '2' }],
        code_template: 'led_template', icon: '💡', color: '#f59e0b',
    },
    {
        id: 'servo_motor', name: 'Servo Motor', category: 'actuator',
        description: 'Control servo position 0-180°',
        inputs: [{ name: 'angle', data_type: 'float' }],
        outputs: [{ name: 'current_angle', data_type: 'float' }],
        configuration: [{ key: 'pin', label: 'Signal Pin', value_type: 'int', default: '13' }],
        code_template: 'servo_template', icon: '⚙️', color: '#10b981',
    },

    // ── Logic ────────────────────────────────────────────
    {
        id: 'threshold_logic', name: 'Threshold Logic', category: 'logic',
        description: 'Compare value against threshold',
        inputs: [{ name: 'value', data_type: 'float' }],
        outputs: [{ name: 'triggered', data_type: 'bool' }],
        configuration: [
            { key: 'threshold', label: 'Threshold', value_type: 'float', default: '30.0' },
            {
                key: 'comparison', label: 'Comparison', value_type: 'select', default: 'greater_than',
                options: ['greater_than', 'less_than', 'equal', 'not_equal']
            },
        ],
        code_template: 'threshold_template', icon: '🔀', color: '#f59e0b',
    },

    // ── Output ───────────────────────────────────────────
    {
        id: 'serial_output', name: 'Serial Output', category: 'output',
        description: 'Print data to Serial monitor',
        inputs: [{ name: 'data', data_type: 'any' }], outputs: [],
        configuration: [
            { key: 'baud_rate', label: 'Baud Rate', value_type: 'int', default: '115200' },
        ],
        code_template: 'serial_template', icon: '🖥️', color: '#06b6d4',
    },

    // ── Control (from behavior synthesis) ────────────────
    {
        id: 'moving_average', name: 'Moving Average', category: 'control',
        description: 'Sliding window noise filter',
        inputs: [{ name: 'value', data_type: 'float' }],
        outputs: [{ name: 'smoothed', data_type: 'float' }],
        configuration: [{ key: 'window_size', label: 'Window Size', value_type: 'int', default: '5' }],
        code_template: 'moving_average', icon: '📉', color: '#8b5cf6',
    },
    {
        id: 'pid_controller', name: 'PID Controller', category: 'control',
        description: 'Closed-loop PID control',
        inputs: [{ name: 'measurement', data_type: 'float' }, { name: 'setpoint', data_type: 'float' }],
        outputs: [{ name: 'output', data_type: 'float' }],
        configuration: [
            { key: 'kp', label: 'Kp', value_type: 'float', default: '1.0' },
            { key: 'ki', label: 'Ki', value_type: 'float', default: '0.1' },
            { key: 'kd', label: 'Kd', value_type: 'float', default: '0.05' },
        ],
        code_template: 'pid_controller', icon: '🎛️', color: '#f59e0b',
    },
    {
        id: 'hysteresis', name: 'Hysteresis', category: 'control',
        description: 'Schmitt trigger with dual thresholds',
        inputs: [{ name: 'value', data_type: 'float' }],
        outputs: [{ name: 'active', data_type: 'bool' }],
        configuration: [
            { key: 'high_threshold', label: 'ON Threshold', value_type: 'float', default: '30.0' },
            { key: 'low_threshold', label: 'OFF Threshold', value_type: 'float', default: '25.0' },
        ],
        code_template: 'hysteresis', icon: '↕️', color: '#10b981',
    },
    {
        id: 'state_machine', name: 'State Machine', category: 'control',
        description: 'Finite state machine with transitions',
        inputs: [{ name: 'trigger', data_type: 'any' }],
        outputs: [{ name: 'state', data_type: 'int' }, { name: 'changed', data_type: 'bool' }],
        configuration: [
            { key: 'states', label: 'States', value_type: 'string', default: 'IDLE,RUNNING,ERROR' },
        ],
        code_template: 'state_machine', icon: '🔄', color: '#ec4899',
    },

    // ── Security ─────────────────────────────────────────
    {
        id: 'tls_config', name: 'TLS Config', category: 'security',
        description: 'Root CA & client certs for secure connections',
        inputs: [], outputs: [{ name: 'configured', data_type: 'bool' }],
        configuration: [
            { key: 'root_ca', label: 'Root CA (PEM)', value_type: 'string' },
            { key: 'verify_server', label: 'Verify Server', value_type: 'bool', default: 'true' },
        ],
        code_template: 'tls_template', icon: '🔒', color: '#dc2626',
    },
    {
        id: 'api_key_vault', name: 'API Key Vault', category: 'security',
        description: 'Secure NVS credential storage',
        inputs: [], outputs: [{ name: 'ready', data_type: 'bool' }],
        configuration: [
            { key: 'namespace', label: 'Namespace', value_type: 'string', default: 'secrets' },
        ],
        code_template: 'vault_template', icon: '🔑', color: '#f59e0b',
    },
    {
        id: 'encrypted_storage', name: 'Encrypted Storage', category: 'security',
        description: 'AES-256 encrypted NVS partitions',
        inputs: [{ name: 'data', data_type: 'string' }],
        outputs: [{ name: 'ready', data_type: 'bool' }],
        configuration: [
            { key: 'namespace', label: 'Namespace', value_type: 'string', default: 'encrypted' },
        ],
        code_template: 'encrypted_template', icon: '🛡️', color: '#dc2626',
    },
    {
        id: 'secure_boot', name: 'Secure Boot', category: 'security',
        description: 'ESP32 secure boot & flash encryption',
        inputs: [], outputs: [
            { name: 'secure_boot_enabled', data_type: 'bool' },
            { name: 'flash_encrypted', data_type: 'bool' },
        ],
        configuration: [
            { key: 'secure_boot_v2', label: 'Secure Boot V2', value_type: 'bool', default: 'true' },
        ],
        code_template: 'secure_boot_template', icon: '🔐', color: '#991b1b',
    },

    // ── Audio ────────────────────────────────────────────
    {
        id: 'i2s_microphone', name: 'I2S Microphone', category: 'audio',
        description: 'INMP441 digital microphone via I2S',
        inputs: [], outputs: [
            { name: 'audio_data', data_type: 'any' },
            { name: 'rms_level', data_type: 'float' },
            { name: 'peak', data_type: 'float' },
        ],
        configuration: [
            { key: 'bck_pin', label: 'BCK Pin', value_type: 'int', default: '26' },
            { key: 'ws_pin', label: 'WS Pin', value_type: 'int', default: '25' },
            { key: 'data_pin', label: 'Data Pin', value_type: 'int', default: '22' },
            { key: 'sample_rate', label: 'Sample Rate', value_type: 'int', default: '16000' },
        ],
        code_template: 'i2s_mic_template', icon: '🎤', color: '#e11d48',
    },
    {
        id: 'i2s_speaker', name: 'I2S Speaker', category: 'audio',
        description: 'MAX98357A DAC speaker via I2S',
        inputs: [{ name: 'audio_data', data_type: 'any' }],
        outputs: [{ name: 'playing', data_type: 'bool' }],
        configuration: [
            { key: 'bck_pin', label: 'BCK Pin', value_type: 'int', default: '27' },
            { key: 'ws_pin', label: 'WS Pin', value_type: 'int', default: '14' },
            { key: 'data_pin', label: 'Data Out Pin', value_type: 'int', default: '12' },
        ],
        code_template: 'i2s_spk_template', icon: '🔊', color: '#f97316',
    },
    {
        id: 'audio_processor', name: 'Audio Processor', category: 'audio',
        description: 'FFT, RMS, peak detection',
        inputs: [{ name: 'audio_data', data_type: 'any' }],
        outputs: [
            { name: 'dominant_freq', data_type: 'float' },
            { name: 'rms_db', data_type: 'float' },
            { name: 'is_loud', data_type: 'bool' },
        ],
        configuration: [
            { key: 'fft_size', label: 'FFT Size', value_type: 'int', default: '1024' },
            { key: 'noise_threshold_db', label: 'Noise Threshold (dB)', value_type: 'float', default: '-40' },
        ],
        code_template: 'audio_proc_template', icon: '🎵', color: '#a855f7',
    },

    // ── Display ──────────────────────────────────────────
    {
        id: 'lvgl_app', name: 'LVGL Application', category: 'display',
        description: 'Full LVGL display with widgets',
        inputs: [{ name: 'data', data_type: 'any' }],
        outputs: [{ name: 'touch_pressed', data_type: 'bool' }],
        configuration: [
            { key: 'screen_width', label: 'Width', value_type: 'int', default: '320' },
            { key: 'screen_height', label: 'Height', value_type: 'int', default: '240' },
            { key: 'rotation', label: 'Rotation', value_type: 'int', default: '1' },
        ],
        code_template: 'lvgl_template', icon: '🖥️', color: '#0ea5e9',
    },
    {
        id: 'spi_display', name: 'SPI Display', category: 'display',
        description: 'ILI9341/ST7789 via TFT_eSPI',
        inputs: [], outputs: [{ name: 'ready', data_type: 'bool' }],
        configuration: [
            { key: 'driver', label: 'Driver', value_type: 'string', default: 'ILI9341' },
            { key: 'cs_pin', label: 'CS Pin', value_type: 'int', default: '5' },
            { key: 'dc_pin', label: 'DC Pin', value_type: 'int', default: '16' },
        ],
        code_template: 'spi_display_template', icon: '📺', color: '#14b8a6',
    },
    {
        id: 'i2c_oled', name: 'I2C OLED', category: 'display',
        description: 'SSD1306 128x64 OLED',
        inputs: [{ name: 'text', data_type: 'string' }],
        outputs: [{ name: 'ready', data_type: 'bool' }],
        configuration: [
            { key: 'i2c_address', label: 'Address', value_type: 'string', default: '0x3C' },
            { key: 'width', label: 'Width', value_type: 'int', default: '128' },
            { key: 'height', label: 'Height', value_type: 'int', default: '64' },
        ],
        code_template: 'oled_template', icon: '📟', color: '#64748b',
    },

    // ── FreeRTOS ─────────────────────────────────────────
    {
        id: 'rtos_task', name: 'FreeRTOS Task', category: 'freertos',
        description: 'Pinned task with stack & priority config',
        inputs: [{ name: 'data', data_type: 'any' }],
        outputs: [{ name: 'running', data_type: 'bool' }, { name: 'stack_watermark', data_type: 'int' }],
        configuration: [
            { key: 'task_name', label: 'Name', value_type: 'string', default: 'app_task' },
            { key: 'stack_size', label: 'Stack', value_type: 'int', default: '4096' },
            { key: 'priority', label: 'Priority', value_type: 'int', default: '5' },
            { key: 'core_id', label: 'Core (0/1)', value_type: 'int', default: '1' },
        ],
        code_template: 'rtos_task_template', icon: '🧵', color: '#ec4899',
    },
    {
        id: 'rtos_queue', name: 'FreeRTOS Queue', category: 'freertos',
        description: 'Inter-task message queue',
        inputs: [{ name: 'data_in', data_type: 'any' }],
        outputs: [{ name: 'data_out', data_type: 'any' }, { name: 'count', data_type: 'int' }],
        configuration: [
            { key: 'queue_length', label: 'Max Items', value_type: 'int', default: '10' },
            { key: 'item_size', label: 'Item Size', value_type: 'int', default: '64' },
        ],
        code_template: 'rtos_queue_template', icon: '📨', color: '#8b5cf6',
    },
    {
        id: 'rtos_semaphore', name: 'FreeRTOS Mutex', category: 'freertos',
        description: 'Mutex for shared I2C/SPI bus protection',
        inputs: [], outputs: [{ name: 'locked', data_type: 'bool' }],
        configuration: [
            { key: 'sem_name', label: 'Name', value_type: 'string', default: 'i2c_mutex' },
            { key: 'sem_type', label: 'Type', value_type: 'string', default: 'mutex' },
        ],
        code_template: 'rtos_sem_template', icon: '🔒', color: '#059669',
    },
    {
        id: 'rtos_event_group', name: 'Event Group', category: 'freertos',
        description: 'Multi-task event synchronization',
        inputs: [], outputs: [{ name: 'flags', data_type: 'int' }],
        configuration: [
            { key: 'event_names', label: 'Events', value_type: 'string', default: 'WIFI_READY,SENSOR_INIT' },
        ],
        code_template: 'rtos_evt_template', icon: '🚩', color: '#f43f5e',
    },
    {
        id: 'rtos_timer', name: 'Software Timer', category: 'freertos',
        description: 'FreeRTOS timer with callback',
        inputs: [], outputs: [{ name: 'expired', data_type: 'bool' }],
        configuration: [
            { key: 'period_ms', label: 'Period (ms)', value_type: 'int', default: '1000' },
            { key: 'auto_reload', label: 'Auto Reload', value_type: 'bool', default: 'true' },
        ],
        code_template: 'rtos_timer_template', icon: '⏱️', color: '#0d9488',
    },
];

export default function BlockLibrary() {
    const [searchQuery, setSearchQuery] = useState('');
    const [expandedCategories, setExpandedCategories] = useState<Set<string>>(
        new Set(Object.keys(BLOCK_CATEGORIES))
    );

    const filteredBlocks = LIBRARY_BLOCKS.filter(
        (b) =>
            b.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
            b.description.toLowerCase().includes(searchQuery.toLowerCase())
    );

    const blocksByCategory = Object.keys(BLOCK_CATEGORIES).reduce(
        (acc, cat) => {
            acc[cat] = filteredBlocks.filter((b) => b.category === cat);
            return acc;
        },
        {} as Record<string, Block[]>
    );

    const toggleCategory = (cat: string) => {
        const next = new Set(expandedCategories);
        if (next.has(cat)) next.delete(cat);
        else next.add(cat);
        setExpandedCategories(next);
    };

    const onDragStart = (event: DragEvent, block: Block) => {
        event.dataTransfer.setData('application/parakram-block', JSON.stringify(block));
        event.dataTransfer.effectAllowed = 'move';
    };

    return (
        <div className="block-library">
            <div className="block-library__header">
                <h2 className="block-library__title">🧩 Blocks</h2>
                <span className="block-library__count">{LIBRARY_BLOCKS.length}</span>
            </div>

            <input
                className="block-library__search"
                type="text"
                placeholder="Search blocks..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
            />

            <div className="block-library__categories">
                {Object.entries(BLOCK_CATEGORIES).map(([catKey, catMeta]) => {
                    const blocks = blocksByCategory[catKey] || [];
                    if (blocks.length === 0 && searchQuery) return null;
                    const isExpanded = expandedCategories.has(catKey);

                    return (
                        <div key={catKey} className="block-library__category">
                            <button
                                className="block-library__category-header"
                                onClick={() => toggleCategory(catKey)}
                            >
                                <span>{catMeta.icon} {catMeta.label}</span>
                                <span className="block-library__category-toggle">
                                    {isExpanded ? '▾' : '▸'} ({blocks.length})
                                </span>
                            </button>

                            {isExpanded && (
                                <div className="block-library__items">
                                    {blocks.map((block) => (
                                        <div
                                            key={block.id}
                                            className="block-library__item"
                                            draggable
                                            onDragStart={(e) => onDragStart(e, block)}
                                            style={{ '--item-color': block.color } as React.CSSProperties}
                                        >
                                            <span className="block-library__item-icon">{block.icon}</span>
                                            <div className="block-library__item-info">
                                                <span className="block-library__item-name">{block.name}</span>
                                                <span className="block-library__item-desc">{block.description}</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
