/**
 * HardwareCanvas — React Flow canvas with custom HardwareNodes.
 * Supports drag-drop, auto-layout, and AI-generated graph injection.
 */
import { useCallback, useMemo, useEffect } from 'react';
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
} from '@xyflow/react';
import '@xyflow/react/dist/style.css';
import HardwareNode from './HardwareNode';

interface Props {
  onNodeSelect: (node: Node | null) => void;
  externalNodes?: Node[];
}

export default function HardwareCanvas({ onNodeSelect, externalNodes }: Props) {
  const [nodes, setNodes, onNodesChange] = useNodesState<Node>([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState<Edge>([]);

  const nodeTypes = useMemo(() => ({ hardwareNode: HardwareNode }), []);

  // Inject AI-generated nodes
  useEffect(() => {
    if (externalNodes && externalNodes.length > 0) {
      setNodes(externalNodes);
      // Auto-create edges from each node to the ESP32 manifest
      const espNode = externalNodes.find((n) =>
        (n.data as Record<string, unknown>).blockId === 'esp32_manifest'
      );
      if (espNode) {
        const newEdges: Edge[] = externalNodes
          .filter((n) => n.id !== espNode.id)
          .map((n, i) => ({
            id: `e_auto_${i}`,
            source: espNode.id,
            target: n.id,
            animated: true,
            style: { stroke: 'var(--accent)', strokeWidth: 2 },
          }));
        setEdges(newEdges);
      }
    }
  }, [externalNodes, setNodes, setEdges]);

  const onConnect = useCallback(
    (connection: Connection) => {
      setEdges((eds) => addEdge({ ...connection, animated: true, style: { stroke: 'var(--accent)' } }, eds));
    },
    [setEdges]
  );

  const onNodeClick = useCallback(
    (_: React.MouseEvent, node: Node) => onNodeSelect(node),
    [onNodeSelect]
  );

  const onPaneClick = useCallback(() => onNodeSelect(null), [onNodeSelect]);

  return (
    <div className="w-full h-full" style={{ background: 'var(--bg-primary)' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onConnect={onConnect}
        onNodeClick={onNodeClick}
        onPaneClick={onPaneClick}
        nodeTypes={nodeTypes}
        fitView
        snapToGrid
        snapGrid={[20, 20]}
        defaultEdgeOptions={{ animated: true }}
        proOptions={{ hideAttribution: true }}
      >
        <Background variant={BackgroundVariant.Dots} gap={24} size={1} color="rgba(99, 102, 241, 0.08)" />
        <Controls className="!rounded-xl" />
        <MiniMap
          nodeColor={(n) => {
            const cat = (n.data as Record<string, unknown>).category as string;
            const colors: Record<string, string> = {
              sensor: '#ef4444', actuator: '#f59e0b', communication: '#8b5cf6',
              display: '#06b6d4', storage: '#10b981', power: '#eab308',
              security: '#ec4899', boards: '#6366f1',
            };
            return colors[cat] || '#6366f1';
          }}
          maskColor="rgba(10, 10, 20, 0.85)"
          className="!rounded-xl"
        />
      </ReactFlow>
    </div>
  );
}
