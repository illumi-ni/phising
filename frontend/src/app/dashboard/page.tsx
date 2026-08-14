"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

type ScoreSummary = {
  readability_score: number;
  sentiment_score: number;
  persuasion_score: number;
  similarity_score: number;
};

type SummaryResponse = {
  scores: Record<string, ScoreSummary>;
  tactics: Record<string, Record<string, number>>;
  detection: {
    email_source: string;
    total: number;
    detected: number;
    detection_rate: number;
  }[];
  emails: {
    id: number;
    source: string;
    scenario_type: string | null;
    subject: string;
    readability_score: number | null;
    sentiment_score: number | null;
    persuasion_score: number | null;
    similarity_score: number | null;
  }[];
};

type SortKey =
  | "id"
  | "source"
  | "scenario_type"
  | "subject"
  | "readability_score"
  | "sentiment_score"
  | "persuasion_score"
  | "similarity_score";

const SCORE_COLUMNS: { key: SortKey; label: string }[] = [
  { key: "id", label: "ID" },
  { key: "source", label: "Source" },
  { key: "scenario_type", label: "Scenario" },
  { key: "subject", label: "Subject" },
  { key: "readability_score", label: "Readability" },
  { key: "sentiment_score", label: "Sentiment" },
  { key: "persuasion_score", label: "Persuasion" },
  { key: "similarity_score", label: "Similarity" },
];

export default function DashboardPage() {
  const [data, setData] = useState<SummaryResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [sortKey, setSortKey] = useState<SortKey>("id");
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [sourceFilter, setSourceFilter] = useState<string>("all");
  const [scenarioFilter, setScenarioFilter] = useState<string>("all");

  const fetchSummary = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/dashboard/summary`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setData(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load dashboard");
    }
  }, []);

  useEffect(() => {
    fetchSummary();
  }, [fetchSummary]);

  const scoreChartData = useMemo(() => {
    if (!data) return [];
    const metrics: { key: keyof ScoreSummary; label: string }[] = [
      { key: "readability_score", label: "Readability" },
      { key: "sentiment_score", label: "Sentiment" },
      { key: "persuasion_score", label: "Persuasion" },
      { key: "similarity_score", label: "Similarity" },
    ];
    return metrics.map((m) => ({
      metric: m.label,
      Generated: data.scores.generated?.[m.key] ?? 0,
      Human: data.scores.human?.[m.key] ?? 0,
    }));
  }, [data]);

  const tacticChartData = useMemo(() => {
    if (!data) return [];
    const allTactics = new Set<string>();
    Object.values(data.tactics).forEach((t) =>
      Object.keys(t).forEach((k) => allTactics.add(k))
    );
    return Array.from(allTactics).map((tactic) => ({
      tactic,
      Generated: data.tactics.generated?.[tactic] ?? 0,
      Human: data.tactics.human?.[tactic] ?? 0,
    }));
  }, [data]);

  const detectionChartData = useMemo(() => {
    if (!data) return [];
    return data.detection.map((d) => ({
      source: d.email_source === "generated" ? "LLM Generated" : "Human",
      "Detection Rate (%)": d.detection_rate,
    }));
  }, [data]);

  const filteredEmails = useMemo(() => {
    if (!data) return [];
    return data.emails
      .filter((e) => sourceFilter === "all" || e.source === sourceFilter)
      .filter(
        (e) =>
          scenarioFilter === "all" ||
          (e.scenario_type ?? "") === scenarioFilter
      )
      .sort((a, b) => {
        const av = a[sortKey] ?? "";
        const bv = b[sortKey] ?? "";
        const cmp =
          typeof av === "number" && typeof bv === "number"
            ? av - bv
            : String(av).localeCompare(String(bv));
        return sortDir === "asc" ? cmp : -cmp;
      });
  }, [data, sortKey, sortDir, sourceFilter, scenarioFilter]);

  const scenarioTypes = useMemo(() => {
    if (!data) return [];
    return Array.from(
      new Set(
        data.emails
          .map((e) => e.scenario_type)
          .filter((t): t is string => !!t)
      )
    );
  }, [data]);

  function toggleSort(key: SortKey) {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("asc");
    }
  }

  function exportCsv() {
    window.location.href = `${API_URL}/export/csv`;
  }

  function exportPdf() {
    window.location.href = `${API_URL}/export/pdf`;
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Analytics Dashboard</h1>
          <p className="mt-1 text-gray-600">
            Evaluation scores, tactic usage, and detection rates.
          </p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={exportCsv}
            className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
          >
            Export CSV
          </button>
          <button
            onClick={exportPdf}
            className="rounded-md bg-gray-800 px-4 py-2 text-sm font-medium text-white hover:bg-gray-900"
          >
            Export PDF
          </button>
        </div>
      </div>

      {error && (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {!data && !error && (
        <p className="mt-8 text-gray-500">Loading dashboard...</p>
      )}

      {data && (
        <>
          {/* Charts */}
          <div className="mt-8 grid gap-6 lg:grid-cols-2">
            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-gray-900">
                Average Evaluation Scores
              </h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={scoreChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="metric" />
                  <YAxis domain={[0, 100]} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="Generated" fill="#6366f1" />
                  <Bar dataKey="Human" fill="#10b981" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-gray-900">
                Tactic Frequency
              </h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={tacticChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="tactic" />
                  <YAxis allowDecimals={false} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="Generated" fill="#6366f1" />
                  <Bar dataKey="Human" fill="#10b981" />
                </BarChart>
              </ResponsiveContainer>
            </div>

            <div className="rounded-xl border border-gray-200 bg-white p-6">
              <h2 className="text-lg font-semibold text-gray-900">
                Detection Rate (% flagged as phishing)
              </h2>
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={detectionChartData}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="source" />
                  <YAxis domain={[0, 100]} unit="%" />
                  <Tooltip />
                  <Bar dataKey="Detection Rate (%)" fill="#ef4444" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Emails table */}
          <div className="mt-8 overflow-hidden rounded-xl border border-gray-200 bg-white">
            <div className="flex flex-wrap items-center gap-4 border-b border-gray-200 bg-gray-50 px-4 py-3">
              <div className="flex items-center gap-2">
                <label className="text-xs font-medium text-gray-700">
                  Source:
                </label>
                <select
                  value={sourceFilter}
                  onChange={(e) => setSourceFilter(e.target.value)}
                  className="rounded-md border border-gray-300 px-2 py-1 text-xs"
                >
                  <option value="all">All</option>
                  <option value="generated">Generated</option>
                  <option value="human">Human</option>
                </select>
              </div>
              <div className="flex items-center gap-2">
                <label className="text-xs font-medium text-gray-700">
                  Scenario:
                </label>
                <select
                  value={scenarioFilter}
                  onChange={(e) => setScenarioFilter(e.target.value)}
                  className="rounded-md border border-gray-300 px-2 py-1 text-xs"
                >
                  <option value="all">All</option>
                  {scenarioTypes.map((t) => (
                    <option key={t} value={t}>
                      {t}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <table className="min-w-full divide-y divide-gray-200 text-sm">
              <thead className="bg-gray-50">
                <tr>
                  {SCORE_COLUMNS.map((c) => (
                    <th
                      key={c.key}
                      onClick={() => toggleSort(c.key)}
                      className="cursor-pointer select-none px-4 py-3 text-left font-medium text-gray-700 hover:text-gray-900"
                    >
                      {c.label}
                      {sortKey === c.key && (
                        <span className="ml-1 text-xs">
                          {sortDir === "asc" ? "▲" : "▼"}
                        </span>
                      )}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-200">
                {filteredEmails.map((e) => (
                  <tr key={`${e.source}-${e.id}`}>
                    <td className="px-4 py-3 text-gray-900">{e.id}</td>
                    <td className="px-4 py-3 text-gray-900">{e.source}</td>
                    <td className="px-4 py-3 capitalize text-gray-900">
                      {e.scenario_type ?? "—"}
                    </td>
                    <td className="max-w-xs truncate px-4 py-3 text-gray-900">
                      {e.subject}
                    </td>
                    <td className="px-4 py-3 text-gray-900">
                      {e.readability_score?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-900">
                      {e.sentiment_score?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-900">
                      {e.persuasion_score?.toFixed(2) ?? "—"}
                    </td>
                    <td className="px-4 py-3 text-gray-900">
                      {e.similarity_score?.toFixed(2) ?? "—"}
                    </td>
                  </tr>
                ))}
                {filteredEmails.length === 0 && (
                  <tr>
                    <td colSpan={8} className="px-4 py-8 text-center text-gray-500">
                      No emails match the current filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
    </main>
  );
}
