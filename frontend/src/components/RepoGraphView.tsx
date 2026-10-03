// frontend/src/components/RepoGraphView.tsx
// Renders the file-level dependency graph as an interactive force-directed
// diagram — nodes are files (always labeled with their filename), edges
// are import/includes/calls relationships. Fetches from /repositories/graph.

import { useEffect, useRef, useState } from "react";
import ForceGraph2D, { ForceGraphMethods } from "react-force-graph-2d";
import { apiPost } from "../api/client";

interface GraphNode {
  id: string;
  name: string;
}
interface GraphEdge {
  source: string;
  target: string;
  relation: string;
}
interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

const RELATION_COLORS: Record<string, string> = {
  imports: "#2563eb",
  calls: "#16a34a",
  includes: "#d97706",
};

const NODE_COLOR = "#1e3a8a";
const NODE_RADIUS = 5;

export default function RepoGraphView({ repoPath }: { repoPath: string }) {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);
  const fgRef = useRef<ForceGraphMethods>();

  useEffect(() => {
    if (!repoPath) return;
    setLoading(true);
    apiPost<GraphData>("/repositories/graph", { repo_path: repoPath })
      .then(setData)
      .finally(() => setLoading(false));
  }, [repoPath]);

  if (loading) return <p className="text-sm text-gray-500">Loading graph...</p>;
  if (!data) return null;

  return (
    <div className="rounded-lg border p-4">
      <h2 className="font-semibold mb-1">Repository Graph (files only)</h2>
      <p className="text-xs text-gray-500 mb-3">
        {data.nodes.length} files &middot; {data.edges.length} dependency edges
        &middot; <span style={{ color: RELATION_COLORS.imports }}>■</span> imports{" "}
        <span style={{ color: RELATION_COLORS.calls }}>■</span> calls{" "}
        <span style={{ color: RELATION_COLORS.includes }}>■</span> includes
      </p>
      <div ref={containerRef} style={{ height: 500 }}>
        <ForceGraph2D
          ref={fgRef}
          graphData={{
            nodes: data.nodes.map((n) => ({ id: n.id, name: n.name })),
            links: data.edges.map((e) => ({ ...e, color: RELATION_COLORS[e.relation] || "#999" })),
          }}
          width={containerRef.current?.clientWidth || 600}
          height={500}
          linkColor={(l: any) => l.color}
          linkWidth={1.5}
          linkDirectionalArrowLength={5}
          linkDirectionalArrowRelPos={1}
          // Spreads nodes out instead of letting them clump together —
          // negative charge = nodes repel each other.
          d3VelocityDecay={0.25}
          cooldownTime={4000}
          onEngineStop={() => fgRef.current?.zoomToFit(400, 60)}
          // Custom draw: a colored dot PLUS a permanent text label next to
          // it, so file names are always visible, not just on hover.
          nodeCanvasObject={(node: any, ctx, globalScale) => {
            ctx.beginPath();
            ctx.arc(node.x, node.y, NODE_RADIUS, 0, 2 * Math.PI);
            ctx.fillStyle = NODE_COLOR;
            ctx.fill();

            const fontSize = Math.max(11 / globalScale, 3);
            ctx.font = `${fontSize}px Sans-Serif`;
            ctx.textAlign = "left";
            ctx.textBaseline = "middle";
            ctx.fillStyle = "#111827";
            ctx.fillText(node.name, node.x + NODE_RADIUS + 3, node.y);
          }}
          nodePointerAreaPaint={(node: any, color, ctx) => {
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.arc(node.x, node.y, NODE_RADIUS + 2, 0, 2 * Math.PI);
            ctx.fill();
          }}
        />
      </div>
    </div>
  );
}