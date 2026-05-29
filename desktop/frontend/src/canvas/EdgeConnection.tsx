/**
 * EdgeConnection — Custom animated edge for data flow visualization.
 */

import {
    BaseEdge,
    getBezierPath,
    type EdgeProps,
} from '@xyflow/react';

export default function EdgeConnection({
    id,
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    style = {},
    markerEnd,
}: EdgeProps) {
    const [edgePath] = getBezierPath({
        sourceX,
        sourceY,
        sourcePosition,
        targetX,
        targetY,
        targetPosition,
    });

    return (
        <>
            <BaseEdge
                id={id}
                path={edgePath}
                markerEnd={markerEnd}
                style={{
                    ...style,
                    stroke: 'url(#edge-gradient)',
                    strokeWidth: 2,
                    filter: 'drop-shadow(0 0 4px rgba(99, 102, 241, 0.4))',
                }}
            />
            {/* Animated flow dot */}
            <circle r="4" fill="#818cf8" className="edge-flow-dot">
                <animateMotion dur="2s" repeatCount="indefinite" path={edgePath} />
            </circle>
            {/* SVG gradient definition */}
            <defs>
                <linearGradient id="edge-gradient" x1="0%" y1="0%" x2="100%" y2="0%">
                    <stop offset="0%" stopColor="#6366f1" />
                    <stop offset="100%" stopColor="#06b6d4" />
                </linearGradient>
            </defs>
        </>
    );
}
