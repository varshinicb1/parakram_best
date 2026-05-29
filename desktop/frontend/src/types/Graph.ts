/**
 * Graph type definitions — canvas state (nodes + edges).
 */

import type { BlockPort } from './Block';

export interface GraphNode {
    id: string;
    block_id: string;
    name: string;
    category: string;
    description: string;
    position: { x: number; y: number };
    configuration: Record<string, unknown>;
    inputs: BlockPort[];
    outputs: BlockPort[];
}

export interface GraphEdge {
    id: string;
    source: string;
    source_handle: string;
    target: string;
    target_handle: string;
    data_type: string;
}

export interface CanvasGraph {
    nodes: GraphNode[];
    edges: GraphEdge[];
}

export interface Project {
    id: string;
    name: string;
    description: string;
    target_board: string;
    framework: string;
    created_at: string;
    updated_at: string;
    version: number;
}
