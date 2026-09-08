// frontend/src/App.tsx
// Top-level layout/router. Currently just renders the Dashboard;
// add routes here as more pages (repo upload, chat) are built.

import Dashboard from "./pages/Dashboard";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Dashboard />
    </div>
  );
}