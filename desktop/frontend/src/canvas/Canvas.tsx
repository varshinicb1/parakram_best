/**
 * Canvas — Main React Flow canvas with drag-and-drop block support.
 */

import { useCallback, useMemo, type DragEvent } from 'react';
import {
    ReactFlow,
    Background,
    Controls,
    MiniMap,
    addEdge,
    useNodesState,
    useEdgesState,
    type Connection,
    type Node,
    type Edge,
    BackgroundVariant,
    Panel,
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';

import BlockNode from './BlockNode';
import EdgeConnection from './EdgeConnection';

interface CanvasProps {
    onNodeSelect: (node: Node | null) => void;
}

// Initial demo nodes
const initialNodes: Node[] = [
    {
        id: 'sensor_1',
        type: 'blockNode',
        position: { x: 100, y: 150 },
        data: {
            name: 'DHT22 Sensor',
            category: 'sensor',
            description: 'Temperature & Humidity',
            inputs: [],
            outputs: [
                { name: 'temperature', data_type: 'float' },
                { name: 'humidity', data_type: 'float' },
            ],
            configuration: { pin: 4 },
            color: '#ef4444',
        },
    },
    {
        id: 'logic_1',
        type: 'blockNode',
        position: { x: 450, y: 150 },
        data: {
            name: 'Threshold',
            category: 'logic',
            description: 'Temperature > 30°C?',
            inputs: [{ name: 'value', data_type: 'float' }],
            outputs: [{ name: 'triggered', data_type: 'bool' }],
            configuration: { threshold: 30.0 },
            color: '#f59e0b',
        },
    },
    {
        id: 'wifi_1',
        type: 'blockNode',
        position: { x: 800, y: 100 },
        data: {
            name: 'WiFi Alert',
            category: 'communication',
            description: 'Send alert via WiFi',
            inputs: [{ name: 'trigger', data_type: 'bool' }],
            outputs: [{ name: 'sent', data_type: 'bool' }],
            configuration: { ssid: 'MyNetwork' },
            color: '#8b5cf6',
        },
    },
];

const initialEdges: Edge[] = [
    {
        id: 'e1',
        source: 'sensor_1',
        target: 'logic_1',
        sourceHandle: 'temperature',
        targetHandle: 'value',
        type: 'edgeConnection',
    },
    {
        id: 'e2',
        source: 'logic_1',
        target: 'wifi_1',
        sourceHandle: 'triggered',
        targetHandle: 'trigger',
        type: 'edgeConnection',
    },
];

let nodeId = 100;
const getNextId = () => `block_${nodeId++}`;

export default function Canvas({ onNodeSelect }: CanvasProps) {
    const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
    const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);

    const nodeTypes = useMemo(() => ({ blockNode: BlockNode }), []);
    const edgeTypes = useMemo(() => ({ edgeConnection: EdgeConnection }), []);

    // Connect two blocks
    const onConnect = useCallback(
        (connection: Connection) => {
            setEdges((eds) =>
                addEdge({ ...connection, type: 'edgeConnection' }, eds)
            );
        },
        [setEdges]
    );

    // Select a node to show config panel
    const onNodeClick = useCallback(
        (_: React.MouseEvent, node: Node) => {
            onNodeSelect(node);
        },
        [onNodeSelect]
    );

    // Click on empty canvas to deselect
    const onPaneClick = useCallback(() => {
        onNodeSelect(null);
    }, [onNodeSelect]);

    // Handle drag & drop from block library
    const onDragOver = useCallback((event: DragEvent) => {
        event.preventDefault();
        event.dataTransfer.dropEffect = 'move';
    }, []);

    const onDrop = useCallback(
        (event: DragEvent) => {
            event.preventDefault();
            const blockDataStr = event.dataTransfer.getData('application/parakram-block');
            if (!blockDataStr) return;

            const blockData = JSON.parse(blockDataStr);

            const newNode: Node = {
                id: getNextId(),
                type: 'blockNode',
                position: {
                    x: event.clientX - 300,
                    y: event.clientY - 80,
                },
                data: {
                    name: blockData.name,
                    category: blockData.category,
                    description: blockData.description,
                    inputs: blockData.inputs || [],
                    outputs: blockData.outputs || [],
                    configuration: {},
                    color: blockData.color,
                },
            };

            setNodes((nds) => [...nds, newNode]);
        },
        [setNodes]
    );

    return (
        <div className="canvas-container">
            <ReactFlow
                nodes={nodes}
                edges={edges}
                onNodesChange={onNodesChange}
                onEdgesChange={onEdgesChange}
                onConnect={onConnect}
                onNodeClick={onNodeClick}
                onPaneClick={onPaneClick}
                onDragOver={onDragOver}
                onDrop={onDrop}
                nodeTypes={nodeTypes}
                edgeTypes={edgeTypes}
                fitView
                snapToGrid
                snapGrid={[20, 20]}
                defaultEdgeOptions={{
                    type: 'edgeConnection',
                    animated: true,
                }}
            >
                <Background
                    variant={BackgroundVariant.Dots}
                    gap={20}
                    size={1}
                    color="rgba(99, 102, 241, 0.15)"
                />
                <Controls className="canvas-controls" />
                <MiniMap
                    className="canvas-minimap"
                    nodeColor={(n) => {
                        const data = n.data as { color?: string };
                        return data?.color || '#6366f1';
                    }}
                    maskColor="rgba(10, 10, 20, 0.8)"
                />
                <Panel position="top-left" className="canvas-title-panel">
                    <div className="canvas-title">
                        <span className="canvas-title__icon">🔱</span>
                        <span className="canvas-title__text">Parakram AI</span>
                    </div>
                </Panel>
            </ReactFlow>
        </div>
    );
}
