/**
 * BlocklyEditorSpace — Embedded Google Blockly visual programming editor.
 * Custom firmware block definitions + real-time C++ code generation.
 * Uses BlocklyDuino framework conventions with Parakram's golden blocks.
 */
import { useState, useRef, useEffect, useCallback } from 'react';
import {
  Code, Download, Trash2, Save, Upload, Cpu, RotateCcw,
} from 'lucide-react';

const BLOCKLY_CDN = 'https://unpkg.com/blockly/blockly.min.js';

// Custom block definitions for firmware primitives
const CUSTOM_BLOCKS = [
  {
    type: 'setup_loop',
    message0: 'Setup %1 Loop %2',
    args0: [
      { type: 'input_statement', name: 'SETUP' },
      { type: 'input_statement', name: 'LOOP' },
    ],
    colour: 160,
    tooltip: 'Arduino setup() and loop() structure',
  },
  {
    type: 'digital_write',
    message0: 'digitalWrite pin %1 value %2',
    args0: [
      { type: 'field_number', name: 'PIN', value: 13, min: 0, max: 39 },
      { type: 'field_dropdown', name: 'VALUE', options: [['HIGH', 'HIGH'], ['LOW', 'LOW']] },
    ],
    previousStatement: null, nextStatement: null, colour: 230,
    tooltip: 'Set a digital pin HIGH or LOW',
  },
  {
    type: 'digital_read',
    message0: 'digitalRead pin %1',
    args0: [{ type: 'field_number', name: 'PIN', value: 2, min: 0, max: 39 }],
    output: 'Number', colour: 230,
    tooltip: 'Read a digital pin value',
  },
  {
    type: 'analog_read',
    message0: 'analogRead pin %1',
    args0: [{ type: 'field_number', name: 'PIN', value: 36, min: 0, max: 39 }],
    output: 'Number', colour: 230,
    tooltip: 'Read analog value (0-4095)',
  },
  {
    type: 'serial_print',
    message0: 'Serial.println %1',
    args0: [{ type: 'input_value', name: 'TEXT' }],
    previousStatement: null, nextStatement: null, colour: 60,
    tooltip: 'Print text to serial monitor',
  },
  {
    type: 'delay_ms',
    message0: 'delay %1 ms',
    args0: [{ type: 'field_number', name: 'MS', value: 1000, min: 0 }],
    previousStatement: null, nextStatement: null, colour: 120,
    tooltip: 'Wait for specified milliseconds',
  },
  {
    type: 'wifi_connect',
    message0: 'WiFi connect SSID %1 Password %2',
    args0: [
      { type: 'field_input', name: 'SSID', text: 'MyNetwork' },
      { type: 'field_input', name: 'PASS', text: 'password' },
    ],
    previousStatement: null, nextStatement: null, colour: 290,
    tooltip: 'Connect to WiFi network',
  },
  {
    type: 'i2c_begin',
    message0: 'Wire.begin SDA %1 SCL %2',
    args0: [
      { type: 'field_number', name: 'SDA', value: 21, min: 0, max: 39 },
      { type: 'field_number', name: 'SCL', value: 22, min: 0, max: 39 },
    ],
    previousStatement: null, nextStatement: null, colour: 200,
    tooltip: 'Initialize I2C bus',
  },
  {
    type: 'bme280_read',
    message0: 'BME280 read %1',
    args0: [{ type: 'field_dropdown', name: 'PARAM', options: [['Temperature', 'temp'], ['Humidity', 'hum'], ['Pressure', 'pres']] }],
    output: 'Number', colour: 0,
    tooltip: 'Read BME280 sensor value',
  },
  {
    type: 'mqtt_publish',
    message0: 'MQTT publish topic %1 message %2',
    args0: [
      { type: 'field_input', name: 'TOPIC', text: 'sensor/data' },
      { type: 'input_value', name: 'MSG' },
    ],
    previousStatement: null, nextStatement: null, colour: 290,
    tooltip: 'Publish MQTT message',
  },
  {
    type: 'servo_write',
    message0: 'Servo pin %1 angle %2°',
    args0: [
      { type: 'field_number', name: 'PIN', value: 13, min: 0, max: 39 },
      { type: 'field_number', name: 'ANGLE', value: 90, min: 0, max: 180 },
    ],
    previousStatement: null, nextStatement: null, colour: 30,
    tooltip: 'Set servo angle',
  },
  {
    type: 'neopixel_set',
    message0: 'NeoPixel #%1 R %2 G %3 B %4',
    args0: [
      { type: 'field_number', name: 'IDX', value: 0, min: 0 },
      { type: 'field_number', name: 'R', value: 255, min: 0, max: 255 },
      { type: 'field_number', name: 'G', value: 0, min: 0, max: 255 },
      { type: 'field_number', name: 'B', value: 0, min: 0, max: 255 },
    ],
    previousStatement: null, nextStatement: null, colour: 330,
    tooltip: 'Set NeoPixel LED color',
  },
  {
    type: 'freertos_task',
    message0: 'Create FreeRTOS task %1 priority %2 %3',
    args0: [
      { type: 'field_input', name: 'NAME', text: 'sensorTask' },
      { type: 'field_number', name: 'PRIORITY', value: 1, min: 0, max: 10 },
      { type: 'input_statement', name: 'BODY' },
    ],
    previousStatement: null, nextStatement: null, colour: 260,
    tooltip: 'Create a FreeRTOS task',
  },
];

// C++ code generators for each block
const CODE_GENERATORS: Record<string, (block: any) => string> = {
  setup_loop: (b) => `void setup() {\n  Serial.begin(115200);\n${b.setup || '  // setup code'}\n}\n\nvoid loop() {\n${b.loop || '  // loop code'}\n}`,
  digital_write: (b) => `  digitalWrite(${b.PIN}, ${b.VALUE});`,
  digital_read: (b) => `digitalRead(${b.PIN})`,
  analog_read: (b) => `analogRead(${b.PIN})`,
  serial_print: (b) => `  Serial.println(${b.TEXT || '""'});`,
  delay_ms: (b) => `  delay(${b.MS});`,
  wifi_connect: (b) => `  WiFi.begin("${b.SSID}", "${b.PASS}");\n  while (WiFi.status() != WL_CONNECTED) { delay(500); }`,
  i2c_begin: (b) => `  Wire.begin(${b.SDA}, ${b.SCL});`,
  bme280_read: (b) => `bme.read${b.PARAM === 'temp' ? 'Temperature' : b.PARAM === 'hum' ? 'Humidity' : 'Pressure'}()`,
  mqtt_publish: (b) => `  client.publish("${b.TOPIC}", ${b.MSG || '""'});`,
  servo_write: (b) => `  servo.write(${b.ANGLE});`,
  neopixel_set: (b) => `  strip.setPixelColor(${b.IDX}, strip.Color(${b.R}, ${b.G}, ${b.B}));\n  strip.show();`,
  freertos_task: (b) => `  xTaskCreate([](void*) {\n    while(true) {\n${b.BODY || '      // task body'}\n      vTaskDelay(pdMS_TO_TICKS(100));\n    }\n  }, "${b.NAME}", 4096, NULL, ${b.PRIORITY}, NULL);`,
};

// Blockly toolbox categories
const TOOLBOX_XML = `<xml>
  <category name="Structure" colour="160">
    <block type="setup_loop"></block>
  </category>
  <category name="GPIO" colour="230">
    <block type="digital_write"></block>
    <block type="digital_read"></block>
    <block type="analog_read"></block>
  </category>
  <category name="Serial" colour="60">
    <block type="serial_print"></block>
  </category>
  <category name="Timing" colour="120">
    <block type="delay_ms"></block>
  </category>
  <category name="WiFi / MQTT" colour="290">
    <block type="wifi_connect"></block>
    <block type="mqtt_publish"></block>
  </category>
  <category name="I2C" colour="200">
    <block type="i2c_begin"></block>
  </category>
  <category name="Sensors" colour="0">
    <block type="bme280_read"></block>
  </category>
  <category name="Actuators" colour="30">
    <block type="servo_write"></block>
    <block type="neopixel_set"></block>
  </category>
  <category name="RTOS" colour="260">
    <block type="freertos_task"></block>
  </category>
  <sep></sep>
  <category name="Logic" colour="%{BKY_LOGIC_HUE}">
    <block type="controls_if"></block>
    <block type="logic_compare"></block>
    <block type="logic_operation"></block>
    <block type="logic_boolean"></block>
  </category>
  <category name="Loops" colour="%{BKY_LOOPS_HUE}">
    <block type="controls_repeat_ext"></block>
    <block type="controls_whileUntil"></block>
    <block type="controls_for"></block>
  </category>
  <category name="Math" colour="%{BKY_MATH_HUE}">
    <block type="math_number"></block>
    <block type="math_arithmetic"></block>
    <block type="math_random_int"></block>
  </category>
  <category name="Text" colour="%{BKY_TEXTS_HUE}">
    <block type="text"></block>
    <block type="text_join"></block>
  </category>
  <category name="Variables" colour="%{BKY_VARIABLES_HUE}" custom="VARIABLE"></category>
  <category name="Functions" colour="%{BKY_PROCEDURES_HUE}" custom="PROCEDURE"></category>
</xml>`;

export default function BlocklyEditorSpace() {
  const containerRef = useRef<HTMLDivElement>(null);
  const [generatedCode, setGeneratedCode] = useState('// Drag blocks to generate C++ firmware code');
  const [showCode, setShowCode] = useState(true);
  const [blocklyLoaded, setBlocklyLoaded] = useState(false);
  const [blockCount, setBlockCount] = useState(0);
  const workspaceRef = useRef<any>(null);

  // Load Blockly from CDN
  useEffect(() => {
    if ((window as any).Blockly) {
      setBlocklyLoaded(true);
      return;
    }

    const script = document.createElement('script');
    script.src = BLOCKLY_CDN;
    script.async = true;
    script.onload = () => setBlocklyLoaded(true);
    script.onerror = () => console.error('Failed to load Blockly');
    document.head.appendChild(script);
  }, []);

  // Initialize workspace once Blockly is loaded
  useEffect(() => {
    if (!blocklyLoaded || !containerRef.current) return;
    const Blockly = (window as any).Blockly;
    if (!Blockly) return;

    // Register custom blocks
    CUSTOM_BLOCKS.forEach(def => {
      if (!Blockly.Blocks[def.type]) {
        Blockly.Blocks[def.type] = {
          init: function() { this.jsonInit(def); },
        };
      }
    });

    // Create workspace
    const workspace = Blockly.inject(containerRef.current, {
      toolbox: TOOLBOX_XML,
      grid: { spacing: 25, length: 3, colour: '#1a1a2e', snap: true },
      zoom: { controls: true, wheel: true, startScale: 0.9, maxScale: 2, minScale: 0.3 },
      trashcan: true,
      sounds: false,
      renderer: 'zelos',
      theme: {
        base: Blockly.Themes.Classic,
        componentStyles: {
          workspaceBackgroundColour: 'var(--bg-primary)',
          toolboxBackgroundColour: 'var(--bg-secondary)',
          flyoutBackgroundColour: '#1a1a2e',
          scrollbarColour: '#333',
        },
      },
    });

    workspaceRef.current = workspace;

    // Listen for changes
    workspace.addChangeListener(() => {
      const blocks = workspace.getAllBlocks(false);
      setBlockCount(blocks.length);
      generateCodeFromWorkspace(workspace);
    });

    return () => workspace.dispose();
  }, [blocklyLoaded]);

  const generateCodeFromWorkspace = useCallback((workspace: any) => {
    const Blockly = (window as any).Blockly;
    if (!Blockly || !workspace) return;

    const blocks = workspace.getAllBlocks(true);
    if (blocks.length === 0) {
      setGeneratedCode('// Drag blocks to generate C++ firmware code');
      return;
    }

    // Simple code generation from block fields
    let code = '#include <Arduino.h>\n\n';
    const includes = new Set<string>();
    const setupLines: string[] = [];
    const loopLines: string[] = [];

    blocks.forEach((block: any) => {
      const type = block.type;
      const gen = CODE_GENERATORS[type];
      if (!gen) return;

      // Extract field values
      const fields: Record<string, any> = {};
      block.inputList?.forEach((input: any) => {
        input.fieldRow?.forEach((field: any) => {
          if (field.name) fields[field.name] = field.getValue?.() || '';
        });
      });

      const line = gen(fields);

      // Route to setup or loop based on block type
      if (['wifi_connect', 'i2c_begin'].includes(type)) {
        setupLines.push(line);
        if (type === 'wifi_connect') includes.add('#include <WiFi.h>');
        if (type === 'i2c_begin') includes.add('#include <Wire.h>');
      } else if (type === 'setup_loop') {
        // Skip — handled specially
      } else {
        loopLines.push(line);
      }

      // Auto-detect includes
      if (type === 'bme280_read') includes.add('#include <Adafruit_BME280.h>');
      if (type === 'mqtt_publish') includes.add('#include <PubSubClient.h>');
      if (type === 'servo_write') includes.add('#include <ESP32Servo.h>');
      if (type === 'neopixel_set') includes.add('#include <Adafruit_NeoPixel.h>');
      if (type === 'freertos_task') includes.add('#include <freertos/FreeRTOS.h>');
    });

    // Build final code
    code += [...includes].join('\n') + (includes.size > 0 ? '\n\n' : '');
    code += 'void setup() {\n  Serial.begin(115200);\n';
    code += setupLines.map(l => '  ' + l.trim()).join('\n') + '\n';
    code += '}\n\nvoid loop() {\n';
    code += loopLines.map(l => '  ' + l.trim()).join('\n') + '\n';
    code += '  delay(100);\n}\n';

    setGeneratedCode(code);
  }, []);

  const clearWorkspace = () => {
    workspaceRef.current?.clear();
    setGeneratedCode('// Drag blocks to generate C++ firmware code');
    setBlockCount(0);
  };

  const downloadCode = () => {
    const blob = new Blob([generatedCode], { type: 'text/x-c++src' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'main.cpp'; a.click();
    URL.revokeObjectURL(url);
  };

  const saveWorkspace = () => {
    const Blockly = (window as any).Blockly;
    if (!Blockly || !workspaceRef.current) return;
    const xml = Blockly.Xml.workspaceToDom(workspaceRef.current);
    const xmlText = Blockly.Xml.domToText(xml);
    localStorage.setItem('parakram_blockly_workspace', xmlText);
  };

  const loadWorkspace = () => {
    const Blockly = (window as any).Blockly;
    if (!Blockly || !workspaceRef.current) return;
    const xmlText = localStorage.getItem('parakram_blockly_workspace');
    if (xmlText) {
      workspaceRef.current.clear();
      const xml = Blockly.utils.xml.textToDom(xmlText);
      Blockly.Xml.domToWorkspace(xml, workspaceRef.current);
    }
  };

  return (
    <div className="flex-1 flex overflow-hidden" style={{ background: 'var(--bg-primary)' }}>
      {/* Blockly Canvas */}
      <div className="flex-1 relative flex flex-col">
        {/* Toolbar */}
        <div className="flex items-center justify-between px-4 py-2 border-b bg-[var(--bg-secondary)]"
          style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center gap-3">
            <Cpu size={16} style={{ color: 'var(--accent)' }} />
            <span className="text-sm font-bold" style={{ color: 'var(--text-primary)' }}>
              Visual Block Editor
            </span>
            <span className="text-xs font-mono px-2 py-0.5 rounded bg-[var(--bg-primary)] border"
              style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
              {blockCount} blocks
            </span>
          </div>
          <div className="flex items-center gap-2">
            <button onClick={saveWorkspace} className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] transition-colors"
              style={{ color: 'var(--text-muted)' }} title="Save Workspace"><Save size={16} /></button>
            <button onClick={loadWorkspace} className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] transition-colors"
              style={{ color: 'var(--text-muted)' }} title="Load Workspace"><Upload size={16} /></button>
            <div className="w-px h-5" style={{ background: 'var(--border)' }} />
            <button onClick={clearWorkspace} className="p-1.5 rounded hover:bg-[var(--bg-tertiary)] transition-colors"
              style={{ color: 'var(--text-muted)' }} title="Clear"><Trash2 size={16} /></button>
            <button onClick={() => setShowCode(!showCode)}
              className="p-1.5 rounded transition-colors hover:bg-[var(--bg-tertiary)]"
              style={{ color: showCode ? 'var(--accent)' : 'var(--text-muted)' }} title="Toggle Code">
              <Code size={16} />
            </button>
          </div>
        </div>

        {/* Blockly container */}
        <div ref={containerRef} className="flex-1" style={{ minHeight: 0 }}>
          {!blocklyLoaded && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center space-y-3">
                <RotateCcw size={24} className="animate-spin mx-auto" style={{ color: 'var(--text-muted)' }} />
                <p className="text-sm font-medium" style={{ color: 'var(--text-muted)' }}>
                  Loading Blockly Editor...
                </p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Code Preview Panel */}
      {showCode && (
        <div className="w-96 border-l flex flex-col bg-[var(--bg-secondary)]" style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between px-4 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-center gap-2">
              <Code size={14} style={{ color: 'var(--accent)' }} />
              <span className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Generated C++</span>
            </div>
            <button onClick={downloadCode}
              className="flex items-center gap-1 px-2.5 py-1 rounded text-[10px] font-semibold border hover:bg-[var(--bg-tertiary)] transition-colors"
              style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
              <Download size={12} /> Download
            </button>
          </div>
          <pre className="flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed"
            style={{ color: 'var(--text-secondary)', background: 'var(--bg-primary)' }}>
            {generatedCode}
          </pre>
        </div>
      )}
    </div>
  );
}
