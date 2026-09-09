// frontend/src/pages/Dashboard.tsx
// The "Unified Developer Dashboard" from the synopsis — brings the
// Health Index, patterns, dead code, impact, and similarity results
// (plus optional AI chat) together in one view.

import { useEffect, useState } from "react";
import { apiGet } from "../api/client";

export default function Dashboard() {
  const [health, setHealth] = useState<{ score: number } | null>(null);

  useEffect(() => {
    // TODO: replace "demo-repo" with the actual repository_id once
    // the upload flow is built.
    apiGet<{ score: number }>("/repositories/demo-repo/health-index")
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold">AI Developer Workspace</h1>
      <div className="mt-4 rounded-lg border p-4">
        <h2 className="font-semibold">Repository Health Index</h2>
        <p>{health ? `${health.score}/100` : "No data yet"}</p>
      </div>
      {/* TODO: add cards for Pattern Detector, Dead Code, Impact Analyzer,
          Similarity, and the optional AI chat panel. */}
    </div>
  );
}
