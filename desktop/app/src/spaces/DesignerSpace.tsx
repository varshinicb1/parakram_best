/**
 * FirmwareDesigner — Visual firmware design workspace.
 * Combines: block palette (left) + XY Flow canvas (center) + code preview (right).
 * Drag blocks from palette → canvas, connect them, then generate firmware.
 */
import { useState, useCallback, useMemo, useRef } from 'react';
import {
  ReactFlow, Background, Controls, MiniMap, Panel,
  addEdge, useNodesState, useEdgesState,
  type Connection, type Node, type Edge,
  BackgroundVariant,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import HardwareNode from '../canvas/HardwareNode';
import {
  Cpu, Sun, Radio, Monitor, Database, Zap, Lock, Volume2, Settings,
  Play, Download, Code, Layers, Trash2, RotateCcw, Maximize2,
} from 'lucide-react';

// Block category definitions
const CATEGORIES = [
  { id: 'sensors', label: 'Sensors', icon: Sun, color: '#ef4444' },
  { id: 'actuators', label: 'Actuators', icon: Settings, color: '#f59e0b' },
  { id: 'communication', label: 'Comms', icon: Radio, color: '#8b5cf6' },
  { id: 'display', label: 'Display', icon: Monitor, color: '#06b6d4' },
  { id: 'storage', label: 'Storage', icon: Database, color: '#10b981' },
  { id: 'power', label: 'Power', icon: Zap, color: '#eab308' },
  { id: 'security', label: 'Security', icon: Lock, color: '#ec4899' },
  { id: 'audio', label: 'Audio', icon: Volume2, color: '#14b8a6' },
  { id: 'control_blocks', label: 'Logic', icon: Cpu, color: '#6366f1' },
];

const API = 'http://localhost:8000/api/agent';

export default function FirmwareDesigner() {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [blocks, setBlocks] = useState<any[]>([]);
  const [activeCategory, setActiveCategory] = useState('sensors');
  const [showCode, setShowCode] = useState(false);
  const [generatedCode, setGeneratedCode] = useState('');
  const [generating, setGenerating] = useState(false);
  const [selectedNode, setSelectedNode] = useState<Node | null>(null);
  const [fullscreen, setFullscreen] = useState(false);
  const nodeCounter = useRef(0);

  const nodeTypes = useMemo(() => ({ hardwareNode: HardwareNode }), []);

  // Fetch blocks from backend
  useState(() => {
    fetch(`${API}/blocks/golden`)
      .then(r => r.json())
      .then(data => setBlocks(data.blocks || []))
      .catch(() => {});
  });

  const filteredBlocks = blocks.filter(b => b.category === activeCategory);

  // Add block to canvas
  const addBlockToCanvas = useCallback((block: any) => {
    const id = `node_${nodeCounter.current++}`;
    const newNode: Node = {
      id,
      type: 'hardwareNode',
      position: { x: 250 + Math.random() * 300, y: 100 + Math.random() * 200 },
      data: {
        blockId: block.id,
        name: block.name,
        category: block.category,
        bus: block.bus,
        calibratable: block.calibratable,
      },
    };
    setNodes(nds => [...nds, newNode]);

    // Auto-connect to ESP32 manifest if it exists
    const espNode = nodes.find(n => (n.data as any).blockId === 'esp32_manifest');
    if (espNode) {
      setEdges(eds => addEdge({
        id: `e_auto_${id}`,
        source: espNode.id,
        target: id,
        animated: true,
        style: { stroke: 'var(--accent)', strokeWidth: 2 },
      }, eds));
    }
  }, [nodes, setNodes, setEdges]);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges(eds => addEdge({
        ...connection,
        animated: true,
        style: { stroke: 'var(--accent)', strokeWidth: 2 },
      }, eds));
    },
    [setEdges]
  );

  const clearCanvas = useCallback(() => {
    setNodes([]);
    setEdges([]);
    setSelectedNode(null);
    setGeneratedCode('');
  }, [setNodes, setEdges]);

  // Generate firmware from canvas blocks
  const generateFirmware = useCallback(async () => {
    const blockIds = nodes.map(n => (n.data as any).blockId).filter(Boolean);
    if (blockIds.length === 0) return;

    setGenerating(true);
    try {
      const res = await fetch(`${API}/firmware/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ block_ids: blockIds, board: 'esp32dev' }),
      });
      const data = await res.json();
      setGeneratedCode(data.firmware?.main_cpp || data.code || '// Generation in progress...');
      setShowCode(true);
    } catch {
      setGeneratedCode('// Backend offline — connect to generate firmware');
      setShowCode(true);
    }
    setGenerating(false);
  }, [nodes]);

  const downloadCode = useCallback(() => {
    if (!generatedCode) return;
    const blob = new Blob([generatedCode], { type: 'text/x-c++src' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = 'main.cpp'; a.click();
    URL.revokeObjectURL(url);
  }, [generatedCode]);

  return (
    <div className={`flex-1 flex overflow-hidden ${fullscreen ? 'fixed inset-0 z-50' : ''}`}
      style={{ background: 'var(--bg-primary)' }}>

      {/* Left: Block Palette */}
      <div className="w-56 border-r flex flex-col shrink-0 bg-[var(--bg-secondary)]"
        style={{ borderColor: 'var(--border)' }}>
        <div className="px-3 py-3 border-b flex items-center gap-2" style={{ borderColor: 'var(--border)' }}>
          <Layers size={16} style={{ color: 'var(--text-secondary)' }} />
          <span className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Block Palette</span>
          <span className="ml-auto text-[10px] font-mono px-1.5 py-0.5 rounded bg-[var(--bg-primary)] border"
            style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
            {blocks.length}
          </span>
        </div>

        {/* Category tabs */}
        <div className="flex flex-wrap gap-1 px-2 py-2 border-b" style={{ borderColor: 'var(--border)' }}>
          {CATEGORIES.map(cat => (
            <button key={cat.id} onClick={() => setActiveCategory(cat.id)}
              className="text-[10px] font-semibold px-2 py-1 rounded-md transition-colors"
              style={{
                background: activeCategory === cat.id ? `${cat.color}20` : 'transparent',
                color: activeCategory === cat.id ? cat.color : 'var(--text-muted)',
                border: activeCategory === cat.id ? `1px solid ${cat.color}40` : '1px solid transparent',
              }}>
              {cat.label}
            </button>
          ))}
        </div>

        {/* Block list */}
        <div className="flex-1 overflow-y-auto py-1">
          {filteredBlocks.map(block => (
            <button key={block.id}
              onClick={() => addBlockToCanvas(block)}
              className="w-full text-left flex items-center gap-2 px-3 py-2 text-xs transition-colors hover:bg-[var(--bg-tertiary)] group"
              style={{ color: 'var(--text-secondary)' }}>
              <div className="w-2 h-2 rounded-sm shrink-0"
                style={{ background: CATEGORIES.find(c => c.id === activeCategory)?.color || '#6366f1' }} />
              <span className="truncate flex-1 font-medium group-hover:text-[var(--text-primary)]">
                {block.name}
              </span>
              {block.calibratable && (
                <span className="text-[8px] font-bold px-1 rounded bg-[#f59e0b20]" style={{ color: '#f59e0b' }}>CAL</span>
              )}
            </button>
          ))}
          {filteredBlocks.length === 0 && (
            <div className="text-center text-xs py-8" style={{ color: 'var(--text-muted)' }}>
              Loading blocks...
            </div>
          )}
        </div>

        {/* Canvas stats */}
        <div className="px-3 py-2 border-t text-[10px] font-medium"
          style={{ borderColor: 'var(--border)', color: 'var(--text-muted)' }}>
          {nodes.length} blocks · {edges.length} connections
        </div>
      </div>

      {/* Center: XY Flow Canvas */}
      <div className="flex-1 relative">
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          onNodeClick={(_, node) => setSelectedNode(node)}
          onPaneClick={() => setSelectedNode(null)}
          nodeTypes={nodeTypes}
          fitView
          snapToGrid
          snapGrid={[20, 20]}
          defaultEdgeOptions={{ animated: true }}
          proOptions={{ hideAttribution: true }}
        >
          <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="rgba(99, 102, 241, 0.06)" />
          <Controls className="!rounded-xl" />
          <MiniMap
            nodeColor={n => {
              const cat = (n.data as any).category;
              const colors: Record<string, string> = {
                sensors: '#ef4444', actuators: '#f59e0b', communication: '#8b5cf6',
                display: '#06b6d4', storage: '#10b981', power: '#eab308',
                security: '#ec4899', audio: '#14b8a6', control_blocks: '#6366f1',
              };
              return colors[cat] || '#6366f1';
            }}
            maskColor="rgba(10, 10, 20, 0.85)"
            className="!rounded-xl"
          />

          {/* Toolbar */}
          <Panel position="top-right">
            <div className="flex items-center gap-2 px-3 py-2 rounded-xl border bg-[var(--bg-secondary)] shadow-md"
              style={{ borderColor: 'var(--border)' }}>
              <button onClick={generateFirmware} disabled={generating || nodes.length === 0}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-bold transition-colors disabled:opacity-40"
                style={{ background: 'var(--accent)', color: 'white' }}>
                <Play size={12} /> {generating ? 'Generating...' : 'Generate'}
              </button>
              <button onClick={() => setShowCode(!showCode)}
                className="p-1.5 rounded-lg transition-colors hover:bg-[var(--bg-tertiary)]"
                style={{ color: showCode ? 'var(--accent)' : 'var(--text-muted)' }}
                title="Toggle Code Preview">
                <Code size={16} />
              </button>
              <div className="w-px h-5" style={{ background: 'var(--border)' }} />
              <button onClick={clearCanvas} className="p-1.5 rounded-lg transition-colors hover:bg-[var(--bg-tertiary)]"
                style={{ color: 'var(--text-muted)' }} title="Clear Canvas">
                <Trash2 size={16} />
              </button>
              <button onClick={() => { setNodes([]); setEdges([]); }}
                className="p-1.5 rounded-lg transition-colors hover:bg-[var(--bg-tertiary)]"
                style={{ color: 'var(--text-muted)' }} title="Reset">
                <RotateCcw size={16} />
              </button>
              <button onClick={() => setFullscreen(!fullscreen)}
                className="p-1.5 rounded-lg transition-colors hover:bg-[var(--bg-tertiary)]"
                style={{ color: 'var(--text-muted)' }} title="Fullscreen">
                <Maximize2 size={16} />
              </button>
            </div>
          </Panel>

          {/* Empty state */}
          {nodes.length === 0 && (
            <Panel position="top-center">
              <div className="mt-32 text-center px-8 py-6 rounded-xl border bg-[var(--bg-secondary)] shadow-sm"
                style={{ borderColor: 'var(--border)' }}>
                <Layers size={32} style={{ color: 'var(--text-muted)', margin: '0 auto 12px', opacity: 0.4 }} />
                <p className="text-sm font-semibold mb-1" style={{ color: 'var(--text-primary)' }}>
                  Visual Firmware Designer
                </p>
                <p className="text-xs" style={{ color: 'var(--text-muted)' }}>
                  Click blocks from the palette to add them to the canvas. Connect blocks to define data flow.
                </p>
              </div>
            </Panel>
          )}
        </ReactFlow>
      </div>

      {/* Right: Code Preview */}
      {showCode && (
        <div className="w-96 border-l flex flex-col shrink-0 bg-[var(--bg-secondary)]"
          style={{ borderColor: 'var(--border)' }}>
          <div className="flex items-center justify-between px-4 py-3 border-b" style={{ borderColor: 'var(--border)' }}>
            <div className="flex items-center gap-2">
              <Code size={14} style={{ color: 'var(--text-secondary)' }} />
              <span className="text-xs font-bold" style={{ color: 'var(--text-primary)' }}>Generated Firmware</span>
            </div>
            <button onClick={downloadCode} disabled={!generatedCode}
              className="flex items-center gap-1.5 px-2.5 py-1 rounded-md text-[10px] font-semibold border transition-colors disabled:opacity-40 hover:bg-[var(--bg-tertiary)]"
              style={{ borderColor: 'var(--border)', color: 'var(--text-secondary)' }}>
              <Download size={12} /> Download
            </button>
          </div>
          <pre className="flex-1 overflow-auto p-4 font-mono text-xs leading-relaxed"
            style={{ color: 'var(--text-secondary)', background: 'var(--bg-primary)' }}>
            {generatedCode || '// Click "Generate" to create firmware from your block design'}
          </pre>

          {/* Node Inspector */}
          {selectedNode && (
            <div className="border-t px-4 py-3 space-y-2" style={{ borderColor: 'var(--border)' }}>
              <span className="text-xs font-bold" style={{ color: 'var(--text-muted)' }}>INSPECTOR</span>
              <div className="text-sm font-semibold" style={{ color: 'var(--text-primary)' }}>
                {(selectedNode.data as any).name}
              </div>
              <div className="text-xs" style={{ color: 'var(--text-secondary)' }}>
                Category: {(selectedNode.data as any).category}
                {(selectedNode.data as any).bus && ` · Bus: ${(selectedNode.data as any).bus}`}
                {(selectedNode.data as any).calibratable && ' · Calibratable'}
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
