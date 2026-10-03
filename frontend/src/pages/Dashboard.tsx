// frontend/src/pages/Dashboard.tsx
// Demo dashboard: takes a local repo path, runs it through the backend's
// /repositories/analyze endpoint, and displays the real Health Index
// breakdown and Dead Code Detection results. This is wired for a quick
// progress demo — the real flow (GitHub URL / ZIP upload) still needs
// building; see the TODO on the backend's upload_repository endpoint.

import { useState } from "react";
import { apiPost } from "../api/client";
import RepoGraphView from "../components/RepoGraphView";  

interface HealthBreakdown {
  complexity: number;
  documentation: number;
  test_coverage: number;
  security: number;
  duplication: number;
}

interface AnalyzeResult {
  node_count: number;
  edge_count: number;
  health_index: {
    score: number;
    breakdown: HealthBreakdown;
    details: { flagged_files: string[]; duplicate_groups: string[][] };
  };
  dead_code: {
    orphaned_files: string[];
    dead_private_functions: string[];
    detected_frameworks: string[];
    note: string;
  };
}

export default function Dashboard() {
  const [repoPath, setRepoPath] = useState("");
  const [result, setResult] = useState<AnalyzeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAnalyze() {
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const data = await apiPost<AnalyzeResult>("/repositories/analyze", { repo_path: repoPath });
      setResult(data);
    } catch {
      setError("Analysis failed — check the path is correct and the backend is running.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="p-6 max-w-3xl mx-auto">
      <h1 className="text-2xl font-bold mb-1">AI Developer Workspace</h1>
      <p className="text-sm text-gray-500 mb-4">Repository Intelligence Engine — live demo</p>

      <div className="flex gap-2 mb-6">
        <input
          className="flex-1 border rounded px-3 py-2 text-sm"
          placeholder={String.raw`Local repo path, e.g. C:\Users\...\shopsync-main`}
          value={repoPath}
          onChange={(e) => setRepoPath(e.target.value)}
        />
        <button
          className="bg-blue-600 text-white px-4 py-2 rounded text-sm disabled:opacity-50"
          onClick={handleAnalyze}
          disabled={loading || !repoPath}
        >
          {loading ? "Analyzing..." : "Analyze"}
        </button>
      </div>

      {error && <p className="text-red-600 text-sm mb-4">{error}</p>}

      {result && (
        <div className="space-y-6">
          <div className="rounded-lg border p-4">
            <h2 className="font-semibold mb-1">Repository Graph</h2>
            <p className="text-sm text-gray-600">
              {result.node_count} nodes &middot; {result.edge_count} edges
              <RepoGraphView repoPath={repoPath} />
            </p>
          </div>

          <div className="rounded-lg border p-4">
            <h2 className="font-semibold mb-3">
              Repository Health Index — {result.health_index.score}/100
            </h2>
            {Object.entries(result.health_index.breakdown).map(([key, value]) => (
              <div key={key} className="mb-2">
                <div className="flex justify-between text-xs mb-1">
                  <span className="capitalize">{key.replace("_", " ")}</span>
                  <span>{value}</span>
                </div>
                <div className="w-full bg-gray-200 rounded h-2">
                  <div className="bg-blue-600 h-2 rounded" style={{ width: `${value}%` }} />
                </div>
              </div>
            ))}
          </div>

          <div className="rounded-lg border p-4">
            <h2 className="font-semibold mb-2">Dead Code Detection</h2>
            <p className="text-xs text-gray-500 mb-3">
              Detected frameworks: {result.dead_code.detected_frameworks.join(", ") || "none"}
            </p>

            <p className="text-sm font-medium">
              Orphaned files ({result.dead_code.orphaned_files.length})
            </p>
            <ul className="text-sm list-disc list-inside text-gray-700 mb-3">
              {result.dead_code.orphaned_files.map((f) => (
                <li key={f}>{f.split(/[\\/]/).pop()}</li>
              ))}
            </ul>

            <p className="text-sm font-medium">
              Dead private functions ({result.dead_code.dead_private_functions.length})
            </p>
            <ul className="text-sm list-disc list-inside text-gray-700 mb-3">
              {result.dead_code.dead_private_functions.map((f) => (
                <li key={f}>{f.split("::").pop()}</li>
              ))}
            </ul>

            <p className="text-xs text-gray-400 italic">{result.dead_code.note}</p>
          </div>
        </div>
      )}
    </div>
  );
}