"use client";

import { useEffect, useState } from "react";

type HealthResponse = {
  status: string;
};

export default function Home() {
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const controller = new AbortController();

    async function fetchHealth() {
      try {
        const res = await fetch(
          `${process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"}/health`,
          { signal: controller.signal }
        );
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        const data: HealthResponse = await res.json();
        setHealth(data);
      } catch (err) {
        if (err instanceof DOMException && err.name === "AbortError") return;
        setError(
          err instanceof Error ? err.message : "Failed to reach backend"
        );
      } finally {
        setLoading(false);
      }
    }

    fetchHealth();
    return () => controller.abort();
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8">
      <div className="max-w-2xl mx-auto text-center space-y-8">
        <h1 className="text-4xl font-bold tracking-tight text-gray-900 sm:text-5xl">
          Phishing Simulation &amp; Benchmarking
        </h1>
        <p className="text-lg text-gray-600">
          A platform for simulating phishing attacks and benchmarking detection
          models.
        </p>

        <div className="rounded-xl border border-gray-200 bg-white p-8 shadow-sm">
          <h2 className="text-xl font-semibold text-gray-800 mb-4">
            Backend Status
          </h2>

          {loading && (
            <div className="flex items-center justify-center gap-2">
              <div className="h-5 w-5 animate-spin rounded-full border-2 border-indigo-600 border-t-transparent" />
              <span className="text-gray-500">Connecting to backend...</span>
            </div>
          )}

          {error && (
            <div className="flex items-center justify-center gap-2 text-red-600">
              <span className="inline-block h-3 w-3 rounded-full bg-red-500" />
              <span className="font-medium">Error:</span> {error}
            </div>
          )}

          {health && (
            <div className="flex items-center justify-center gap-2 text-green-600">
              <span className="inline-block h-3 w-3 rounded-full bg-green-500" />
              <span className="font-medium">Status:</span> {health.status}
            </div>
          )}
        </div>
      </div>
    </main>
  );
}
