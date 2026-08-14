"use client";

import { Fragment, useCallback, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export type Scenario = {
  id: number;
  type: string;
  tone: string;
  urgency_level: number;
  created_at: string;
};

export type GeneratedEmail = {
  id: number;
  scenario_id: number;
  subject: string;
  body: string;
  model_used: string;
  created_at: string;
};

export type TacticLabel = {
  id: number;
  email_id: number;
  email_source: string;
  tactic_type: string;
  confidence: number;
  created_at: string;
};

const SCENARIO_TYPES = [
  { value: "password_reset", label: "Password Reset" },
  { value: "invoice", label: "Invoice" },
  { value: "it_alert", label: "IT Alert" },
];

const TONES = ["Formal", "Casual", "Alarming"];

export default function ScenariosPage() {
  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [type, setType] = useState("password_reset");
  const [tone, setTone] = useState("Formal");
  const [urgency, setUrgency] = useState(3);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [generatingId, setGeneratingId] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [generated, setGenerated] = useState<Record<number, GeneratedEmail>>({});
  const [labelingId, setLabelingId] = useState<number | null>(null);
  const [tactics, setTactics] = useState<Record<number, TacticLabel[]>>({});

  const fetchScenarios = useCallback(async () => {
    try {
      const res = await fetch(`${API_URL}/scenarios`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setScenarios(await res.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load scenarios");
    }
  }, []);

  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setMessage(null);
    try {
      const res = await fetch(`${API_URL}/scenarios`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ type, tone, urgency_level: urgency }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${res.status}`);
      }
      setMessage("✅ Scenario created successfully!");
      setType("password_reset");
      setTone("Formal");
      setUrgency(3);
      fetchScenarios();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to create scenario");
    }
  }

  async function handleGenerate(id: number) {
    setGeneratingId(id);
    setError(null);
    try {
      const res = await fetch(`${API_URL}/scenarios/${id}/generate`, {
        method: "POST",
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${res.status}`);
      }
      const email: GeneratedEmail = await res.json();
      setGenerated((prev) => ({ ...prev, [id]: email }));
      setExpanded(id);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate email");
    } finally {
      setGeneratingId(null);
    }
  }

  async function handleLabel(emailId: number) {
    setLabelingId(emailId);
    setError(null);
    try {
      const res = await fetch(
        `${API_URL}/emails/generated/${emailId}/label`,
        { method: "POST" }
      );
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${res.status}`);
      }
      const labels: TacticLabel[] = await res.json();
      setTactics((prev) => ({ ...prev, [emailId]: labels }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to label email");
    } finally {
      setLabelingId(null);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="text-3xl font-bold text-gray-900">Scenario Builder</h1>
      <p className="mt-1 text-gray-600">
        Create phishing scenarios and generate synthetic emails for testing.
      </p>

      {message && (
        <div className="mt-4 rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {message}
        </div>
      )}
      {error && (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      {/* Create form */}
      <form
        onSubmit={handleSubmit}
        className="mt-6 space-y-4 rounded-xl border border-gray-200 bg-white p-6"
      >
        <div className="grid gap-4 sm:grid-cols-3">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Scenario Type
            </label>
            <select
              value={type}
              onChange={(e) => setType(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              {SCENARIO_TYPES.map((t) => (
                <option key={t.value} value={t.value}>
                  {t.label}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Tone
            </label>
            <select
              value={tone}
              onChange={(e) => setTone(e.target.value)}
              className="mt-1 w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              {TONES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Urgency Level: {urgency}
            </label>
            <input
              type="range"
              min={1}
              max={5}
              value={urgency}
              onChange={(e) => setUrgency(Number(e.target.value))}
              className="mt-2 w-full"
            />
            <div className="flex justify-between text-xs text-gray-500">
              <span>1 (low)</span>
              <span>5 (high)</span>
            </div>
          </div>
        </div>
        <button
          type="submit"
          className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
        >
          Create Scenario
        </button>
      </form>

      {/* Scenarios table */}
      <div className="mt-8 overflow-hidden rounded-xl border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">ID</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Type</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Tone</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Urgency</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Created</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {scenarios.map((s) => (
              <Fragment key={s.id}>
                <tr>
                  <td className="px-4 py-3 text-gray-900">{s.id}</td>
                  <td className="px-4 py-3 capitalize text-gray-900">
                    {s.type.replace("_", " ")}
                  </td>
                  <td className="px-4 py-3 text-gray-900">{s.tone}</td>
                  <td className="px-4 py-3 text-gray-900">{s.urgency_level}</td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(s.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleGenerate(s.id)}
                      disabled={generatingId === s.id}
                      className="rounded-md bg-emerald-600 px-3 py-1.5 text-xs font-medium text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      {generatingId === s.id ? "Generating..." : "Generate Email"}
                    </button>
                  </td>
                </tr>
                {expanded === s.id && generated[s.id] && (
                  <tr>
                    <td colSpan={6} className="bg-gray-50 px-6 py-4">
                      <div className="space-y-3">
                        <p className="text-xs text-gray-500">
                          Model: {generated[s.id].model_used} · Email #{generated[s.id].id}
                        </p>
                        <p className="font-medium text-gray-900">
                          Subject: {generated[s.id].subject}
                        </p>
                        <pre className="whitespace-pre-wrap rounded-md bg-white p-4 text-sm text-gray-700 ring-1 ring-gray-200">
                          {generated[s.id].body}
                        </pre>
                        <div className="flex flex-wrap items-center gap-3">
                          <button
                            onClick={() => handleLabel(generated[s.id].id)}
                            disabled={labelingId === generated[s.id].id}
                            className="rounded-md border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
                          >
                            {labelingId === generated[s.id].id
                              ? "Labeling..."
                              : "Label Tactics"}
                          </button>
                          {tactics[generated[s.id].id]?.map((t) => (
                            <span
                              key={t.id}
                              className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800"
                            >
                              {t.tactic_type} · {(t.confidence * 100).toFixed(0)}%
                            </span>
                          ))}
                        </div>
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {scenarios.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  No scenarios yet. Create your first one above.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </main>
  );
}
