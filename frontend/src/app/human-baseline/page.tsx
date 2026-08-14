"use client";

import { Fragment, useCallback, useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
const PAGE_SIZE = 20;

export type HumanEmail = {
  id: number;
  subject: string;
  body: string;
  source: string;
  label: string;
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

export default function HumanBaselinePage() {
  const [emails, setEmails] = useState<HumanEmail[]>([]);
  const [page, setPage] = useState(0);
  const [uploadMsg, setUploadMsg] = useState<string | null>(null);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [manualMsg, setManualMsg] = useState<string | null>(null);
  const [uploading, setUploading] = useState(false);
  const [labelingId, setLabelingId] = useState<number | null>(null);
  const [expanded, setExpanded] = useState<number | null>(null);
  const [tactics, setTactics] = useState<Record<number, TacticLabel[]>>({});

  // Manual form
  const [subject, setSubject] = useState("");
  const [body, setBody] = useState("");
  const [source, setSource] = useState("");
  const [label, setLabel] = useState("phishing");

  const fetchEmails = useCallback(async () => {
    try {
      const res = await fetch(
        `${API_URL}/human-emails?limit=${PAGE_SIZE}&offset=${page * PAGE_SIZE}`
      );
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      setEmails(await res.json());
    } catch (err) {
      setUploadError(
        err instanceof Error ? err.message : "Failed to load emails"
      );
    }
  }, [page]);

  useEffect(() => {
    fetchEmails();
  }, [fetchEmails]);

  async function handleUpload(e: React.FormEvent<HTMLFormElement>) {
    e.preventDefault();
    setUploading(true);
    setUploadMsg(null);
    setUploadError(null);
    const form = e.currentTarget;
    const fileInput = form.elements.namedItem("csv") as HTMLInputElement;
    const file = fileInput.files?.[0];
    if (!file) {
      setUploadError("Please choose a CSV file.");
      setUploading(false);
      return;
    }
    const fd = new FormData();
    fd.append("file", file);
    try {
      const res = await fetch(`${API_URL}/human-emails/upload`, {
        method: "POST",
        body: fd,
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${res.status}`);
      }
      const result = await res.json();
      setUploadMsg(
        `✅ Uploaded: ${result.inserted} inserted, ${result.skipped.length} skipped.`
      );
      setPage(0);
      fetchEmails();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      fileInput.value = "";
    }
  }

  async function handleLabel(id: number) {
    setLabelingId(id);
    setUploadError(null);
    try {
      const res = await fetch(`${API_URL}/emails/human/${id}/label`, {
        method: "POST",
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${res.status}`);
      }
      const labels: TacticLabel[] = await res.json();
      setTactics((prev) => ({ ...prev, [id]: labels }));
      setExpanded(id);
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Failed to label email");
    } finally {
      setLabelingId(null);
    }
  }

  async function handleManual(e: React.FormEvent) {
    e.preventDefault();
    setManualMsg(null);
    setUploadError(null);
    try {
      const res = await fetch(`${API_URL}/human-emails/manual`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ subject, body, source, label }),
      });
      if (!res.ok) {
        const detail = await res.json().catch(() => ({}));
        throw new Error(detail.detail || `HTTP ${res.status}`);
      }
      setManualMsg("✅ Email added successfully!");
      setSubject("");
      setBody("");
      setSource("");
      setLabel("phishing");
      setPage(0);
      fetchEmails();
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : "Failed to add email");
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-8">
      <h1 className="text-3xl font-bold text-gray-900">Human Baseline</h1>
      <p className="mt-1 text-gray-600">
        Upload or manually add real human-written emails as the baseline
        dataset.
      </p>

      {uploadMsg && (
        <div className="mt-4 rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {uploadMsg}
        </div>
      )}
      {manualMsg && (
        <div className="mt-4 rounded-md border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700">
          {manualMsg}
        </div>
      )}
      {uploadError && (
        <div className="mt-4 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {uploadError}
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-2">
        {/* CSV upload */}
        <form
          onSubmit={handleUpload}
          className="rounded-xl border border-gray-200 bg-white p-6"
        >
          <h2 className="text-lg font-semibold text-gray-900">Upload CSV</h2>
          <p className="mt-1 text-xs text-gray-500">
            Columns: subject, body, source, label (phishing|legitimate)
          </p>
          <input
            type="file"
            name="csv"
            accept=".csv"
            className="mt-4 block w-full text-sm text-gray-700 file:mr-3 file:rounded-md file:border-0 file:bg-indigo-50 file:px-3 file:py-2 file:text-sm file:font-medium file:text-indigo-700"
          />
          <button
            type="submit"
            disabled={uploading}
            className="mt-4 rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700 disabled:opacity-50"
          >
            {uploading ? "Uploading..." : "Upload CSV"}
          </button>
        </form>

        {/* Manual entry */}
        <form
          onSubmit={handleManual}
          className="rounded-xl border border-gray-200 bg-white p-6"
        >
          <h2 className="text-lg font-semibold text-gray-900">Manual Entry</h2>
          <div className="mt-4 space-y-3">
            <input
              type="text"
              value={subject}
              onChange={(e) => setSubject(e.target.value)}
              placeholder="Subject"
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
            <textarea
              value={body}
              onChange={(e) => setBody(e.target.value)}
              placeholder="Body"
              required
              rows={4}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
            <input
              type="text"
              value={source}
              onChange={(e) => setSource(e.target.value)}
              placeholder="Source (e.g. public_dataset, internal)"
              required
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            />
            <select
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm"
            >
              <option value="phishing">Phishing</option>
              <option value="legitimate">Legitimate</option>
            </select>
            <button
              type="submit"
              className="rounded-md bg-indigo-600 px-4 py-2 text-sm font-medium text-white hover:bg-indigo-700"
            >
              Add Email
            </button>
          </div>
        </form>
      </div>

      {/* Emails table */}
      <div className="mt-8 overflow-hidden rounded-xl border border-gray-200 bg-white">
        <table className="min-w-full divide-y divide-gray-200 text-sm">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-4 py-3 text-left font-medium text-gray-700">ID</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Subject</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Source</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Label</th>
              <th className="px-4 py-3 text-left font-medium text-gray-700">Created</th>
              <th className="px-4 py-3 text-right font-medium text-gray-700">Actions</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-200">
            {emails.map((e) => (
              <Fragment key={e.id}>
                <tr>
                  <td className="px-4 py-3 text-gray-900">{e.id}</td>
                  <td className="max-w-xs truncate px-4 py-3 text-gray-900">
                    {e.subject}
                  </td>
                  <td className="px-4 py-3 text-gray-900">{e.source}</td>
                  <td className="px-4 py-3">
                    <span
                      className={
                        e.label === "phishing"
                          ? "rounded-full bg-red-100 px-2 py-0.5 text-xs font-medium text-red-700"
                          : "rounded-full bg-green-100 px-2 py-0.5 text-xs font-medium text-green-700"
                      }
                    >
                      {e.label}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-gray-500">
                    {new Date(e.created_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleLabel(e.id)}
                      disabled={labelingId === e.id}
                      className="rounded-md border border-indigo-300 bg-indigo-50 px-3 py-1.5 text-xs font-medium text-indigo-700 hover:bg-indigo-100 disabled:opacity-50"
                    >
                      {labelingId === e.id ? "Labeling..." : "Label Tactics"}
                    </button>
                  </td>
                </tr>
                {expanded === e.id && tactics[e.id] && (
                  <tr>
                    <td colSpan={6} className="bg-gray-50 px-6 py-3">
                      <div className="flex flex-wrap items-center gap-2">
                        <span className="text-xs font-medium text-gray-500">
                          Detected tactics:
                        </span>
                        {tactics[e.id].map((t) => (
                          <span
                            key={t.id}
                            className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-medium text-amber-800"
                          >
                            {t.tactic_type} · {(t.confidence * 100).toFixed(0)}%
                          </span>
                        ))}
                      </div>
                    </td>
                  </tr>
                )}
              </Fragment>
            ))}
            {emails.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                  No human emails yet.
                </td>
              </tr>
            )}
          </tbody>
        </table>
        <div className="flex items-center justify-between border-t border-gray-200 bg-gray-50 px-4 py-3">
          <button
            onClick={() => setPage((p) => Math.max(0, p - 1))}
            disabled={page === 0}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 disabled:opacity-50"
          >
            ← Prev
          </button>
          <span className="text-xs text-gray-500">
            Page {page + 1} · {PAGE_SIZE} per page
          </span>
          <button
            onClick={() => setPage((p) => p + 1)}
            disabled={emails.length < PAGE_SIZE}
            className="rounded-md border border-gray-300 bg-white px-3 py-1.5 text-xs font-medium text-gray-700 disabled:opacity-50"
          >
            Next →
          </button>
        </div>
      </div>
    </main>
  );
}
