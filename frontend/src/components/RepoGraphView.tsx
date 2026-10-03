// frontend/src/components/RepoGraphView.tsx
// Renders the file-level dependency graph as a clean, top-to-bottom
// flowchart (via dagre for layout + React Flow for rendering) instead of
// force-directed physics — labels live INSIDE each node box, so they
// can't overlap the way floating canvas text did. Files with no
// import/call/includes relationship to anything are pulled out into a
// separate list below the diagram rather than scattered across it.

import { useEffect, useMemo, useState } from "react";
import ReactFlow, { Node, Edge, MarkerType, Position } from "reactflow";
import dagre from "dagre";
import "reactflow/dist/style.css";
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

const NODE_WIDTH = 160;
const NODE_HEIGHT = 40;

/** Last path segment is the filename; the one before it disambiguates
 * files that share a name (e.g. two different urls.py). */
function buildLabels(nodes: GraphNode[]): Map<string, string> {
  const nameCounts = new Map<string, number>();
  nodes.forEach((n) => nameCounts.set(n.name, (nameCounts.get(n.name) || 0) + 1));

  const labels = new Map<string, string>();
  for (const n of nodes) {
    if ((nameCounts.get(n.name) || 0) > 1) {
      const parts = n.id.replace(/\\/g, "/").split("/");
      const parent = parts[parts.length - 2] || "";
      labels.set(n.id, `${parent}/${n.name}`);
    } else {
      labels.set(n.id, n.name);
    }
  }
  return labels;
}

function layoutWithDagre(nodes: GraphNode[], edges: GraphEdge[], labels: Map<string, string>) {
  const g = new dagre.graphlib.Graph();
  g.setGraph({ rankdir: "TB", nodesep: 40, ranksep: 70 });
  g.setDefaultEdgeLabel(() => ({}));

  nodes.forEach((n) => g.setNode(n.id, { width: NODE_WIDTH, height: NODE_HEIGHT }));
  edges.forEach((e) => g.setEdge(e.source, e.target));
  dagre.layout(g);

  const rfNodes: Node[] = nodes.map((n) => {
    const pos = g.node(n.id);
    return {
      id: n.id,
      data: { label: labels.get(n.id) },
      position: { x: pos.x - NODE_WIDTH / 2, y: pos.y - NODE_HEIGHT / 2 },
      sourcePosition: Position.Bottom,
      targetPosition: Position.Top,
      style: {
        width: NODE_WIDTH,
        fontSize: 11,
        textAlign: "center",
        border: "1px solid #1e3a8a",
        borderRadius: 6,
        background: "#eef2ff",
      },
    };
  });

  const rfEdges: Edge[] = edges.map((e, i) => ({
    id: `e${i}`,
    source: e.source,
    target: e.target,
    animated: false,
    style: { stroke: RELATION_COLORS[e.relation] || "#999" },
    markerEnd: { type: MarkerType.ArrowClosed, color: RELATION_COLORS[e.relation] || "#999" },
  }));

  return { rfNodes, rfEdges };
}

export default function RepoGraphView({ repoPath }: { repoPath: string }) {
  const [data, setData] = useState<GraphData | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!repoPath) return;
    setLoading(true);
    apiPost<GraphData>("/repositories/graph", { repo_path: repoPath })
      .then(setData)
      .finally(() => setLoading(false));
  }, [repoPath]);

  const { rfNodes, rfEdges, isolatedLabels } = useMemo(() => {
    if (!data) return { rfNodes: [], rfEdges: [], isolatedLabels: [] as string[] };

    const connectedIds = new Set<string>();
    data.edges.forEach((e) => {
      connectedIds.add(e.source);
      connectedIds.add(e.target);
    });

    const connectedNodes = data.nodes.filter((n) => connectedIds.has(n.id));
    const isolated = data.nodes.filter((n) => !connectedIds.has(n.id));
    const labels = buildLabels(data.nodes);

    const { rfNodes, rfEdges } = layoutWithDagre(connectedNodes, data.edges, labels);
    return {
      rfNodes,
      rfEdges,
      isolatedLabels: isolated.map((n) => labels.get(n.id)!),
    };
  }, [data]);

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

      {rfNodes.length > 0 ? (
        <div style={{ height: 420 }} className="border rounded">
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            nodesDraggable={false}
            nodesConnectable={false}
            elementsSelectable={false}
          />
        </div>
      ) : (
        <p className="text-sm text-gray-500">No dependency relationships detected between files.</p>
      )}

      {isolatedLabels.length > 0 && (
        <div className="mt-4">
          <p className="text-sm font-medium mb-1">
            Not connected to anything ({isolatedLabels.length})
          </p>
          <p className="text-xs text-gray-400 mb-2">
            No import, call, or framework-include edge was detected linking these files to the rest of the repo.
          </p>
          <div className="flex flex-wrap gap-1">
            {isolatedLabels.map((label) => (
              <span key={label} className="text-xs bg-gray-100 border rounded px-2 py-1 text-gray-700">
                {label}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}