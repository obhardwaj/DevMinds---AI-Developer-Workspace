// frontend/tailwind.config.js
// Tells Tailwind which files to scan for class names so it knows what
// CSS to generate — without this, Dashboard.tsx's className="..." styles
// (bg-blue-600, rounded-lg, etc.) wouldn't render even once the page loads.

/** @type {import('tailwindcss').Config} */
export default {
    content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
    theme: { extend: {} },
    plugins: [],
  };