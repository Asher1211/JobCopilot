"use client";

import { useCallback, useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchSSE } from "@/lib/sse";
import { API, BACKEND_URL, ROUTES } from "@/lib/constants";
import { FileInput } from "@/components/file-input";

interface ExperienceChunk {
  id: number; chunk_id: string; chunk_type: string; question: string; answer: string;
  raw_text: string; search_text: string; company: string; position: string;
  round: string; date: string; source_file: string; score?: number;
}

export default function ExperiencesPage() {
  const { user, loading } = useAuth();
  const [file, setFile] = useState<File | null>(null);
  const [msg, setMsg] = useState("");
  const [uploading, setUploading] = useState(false);
  const [chunks, setChunks] = useState<ExperienceChunk[]>([]);
  const [loadingChunks, setLoadingChunks] = useState(false);
  const [expanded, setExpanded] = useState<Set<number>>(new Set());
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<ExperienceChunk[]>([]);
  const [searching, setSearching] = useState(false);

  useEffect(() => { if (!loading && !user) window.location.href = ROUTES.login; }, [user, loading]);

  const loadChunks = useCallback(async () => {
    setLoadingChunks(true);
    try {
      const token = localStorage.getItem("token");
      const r = await fetch(`${BACKEND_URL}${API.experiences.list}`, { headers: { Authorization: `Bearer ${token}` } });
      if (r.ok) { const data = await r.json(); setChunks(data.chunks || []); }
    } catch { /* ignore */ } finally { setLoadingChunks(false); }
  }, []);

  useEffect(() => { if (user) loadChunks(); }, [user, loadChunks]);

  async function handleUpload(mode: "sw" | "llm") {
    if (!file) return; setUploading(true); setMsg("");
    try {
      const token = localStorage.getItem("token");
      const formData = new FormData(); formData.append("file", file);
      const r = await fetch(`${BACKEND_URL}${API.experiences.upload}?mode=${mode}`, { method: "POST", headers: { Authorization: `Bearer ${token}` }, body: formData });
      if (!r.ok) throw new Error((await r.json()).detail || "Upload failed");
      const data = await r.json(); setMsg(`Done: ${data.chunks} chunks (${data.mode})`); setFile(null); loadChunks();
    } catch (e) { setMsg(e instanceof Error ? e.message : "Upload failed"); } finally { setUploading(false); }
  }

  async function handleDelete(id: number) {
    const token = localStorage.getItem("token");
    await fetch(`${BACKEND_URL}/api/experiences/chunks/${id}`, { method: "DELETE", headers: { Authorization: `Bearer ${token}` } });
    setChunks((p) => p.filter((c) => c.id !== id));
  }

  async function handleSearch() {
    setSearching(true); setResults([]);
    try {
      await fetchSSE(`${BACKEND_URL}${API.experiences.search}`, { query: query.trim() }, (event, data) => {
        const d = data as Record<string, unknown>;
        if (event === "result" && d.results) setResults(d.results as ExperienceChunk[]);
      }, localStorage.getItem("token"));
    } catch { /* ignore */ } finally { setSearching(false); }
  }

  if (loading || !user) return null;

  return (
    <div className="flex-1 px-6 py-12 max-w-[960px] mx-auto w-full">
      <h2 className="mb-2">Interview Experiences</h2>
      <p className="mb-12 text-lg text-[var(--color-text-secondary)]">Upload interview experience files. LLM preprocessing extracts Q&A pairs; sliding window is the fallback.</p>

      <div className="card p-8 mb-8">
        <h4 className="mb-4">Upload Experience File</h4>
        <div className="flex gap-4 items-end flex-wrap">
          <div className="flex-1 min-w-[200px]">
            <label className="label">File (.docx / .pdf / .txt)</label>
            <FileInput accept=".docx,.pdf,.txt" label="Choose File" onChange={setFile} />
          </div>
          <button onClick={() => handleUpload("llm")} className="btn btn-secondary btn-md" disabled={!file || uploading}>{uploading ? "..." : "Upload (LLM Preprocess)"}</button>
          <button onClick={() => handleUpload("sw")} className="btn btn-secondary btn-md" disabled={!file || uploading}>{uploading ? "..." : "Upload (Sliding Window)"}</button>
        </div>
        {msg && <p className={`mt-3 text-[13px] font-[family-name:var(--font-mono)] ${msg.startsWith("Done") ? "text-[var(--color-success)]" : "text-[var(--color-error)]"}`}>{msg}</p>}
      </div>

      <div className="mb-8">
        <div className="flex items-center justify-between mb-4"><h4>Stored Chunks ({chunks.length})</h4><button onClick={loadChunks} className="btn btn-ghost btn-sm">{loadingChunks ? "Loading..." : "Refresh"}</button></div>
        {chunks.length === 0 && <div className="card p-8 text-center text-[var(--color-text-secondary)]">No experiences yet. Upload a file above.</div>}
        <div className="space-y-3">
          {chunks.map((c) => (
            <div key={c.id} className="card border-l-[5px] border-l-black p-4 flex items-start gap-4 group">
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  <span className="chip text-[10px] font-[family-name:var(--font-mono)]">ID:{c.id}</span>
                  {c.chunk_type === "qa_pair" ? <span className="chip chip-active text-[10px]">Q&A</span> : <span className="text-[10px] text-[var(--color-text-secondary)] font-[family-name:var(--font-mono)]">SW</span>}
                  {c.company && <span className="chip text-[10px]">{c.company}</span>}
                  {c.position && <span className="text-[11px] text-[var(--color-text-secondary)]">{c.position}</span>}
                  {c.round && <span className="text-[11px] text-[var(--color-text-secondary)]">{c.round}</span>}
                  <span className="text-[10px] text-[var(--color-text-secondary)] font-[family-name:var(--font-mono)]">{c.source_file}</span>
                </div>
                {c.chunk_type === "qa_pair" ? (
                  <div><p className="text-[13px] font-bold">Q: {c.question}</p><p className="text-[13px] text-[var(--color-text-secondary)]">A: {c.answer.slice(0, 200)}</p></div>
                ) : (
                  <div><p className={`text-[13px] leading-relaxed text-[var(--color-text-secondary)] ${expanded.has(c.id) ? "" : "line-clamp-3"}`} onClick={() => { const n = new Set(expanded); n.has(c.id) ? n.delete(c.id) : n.add(c.id); setExpanded(n); }} style={{ cursor: "pointer" }}>{c.raw_text || c.search_text}</p></div>
                )}
              </div>
              <button onClick={() => handleDelete(c.id)} className="shrink-0 text-[11px] font-[family-name:var(--font-heading)] uppercase tracking-[0.05em] text-[var(--color-error)] hover:underline opacity-0 group-hover:opacity-100 transition-opacity cursor-pointer">Delete</button>
            </div>
          ))}
        </div>
      </div>

      <div className="card p-8">
        <h4 className="mb-4">Search Experiences</h4>
        <div className="flex gap-4">
          <input type="text" className="input flex-1" value={query} onChange={(e) => setQuery(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSearch()} placeholder="e.g. 字节跳动 后端, Python system design..." />
          <button onClick={handleSearch} className="btn btn-primary btn-md shrink-0" disabled={searching || !query.trim()}>{searching ? "..." : "Search"}</button>
        </div>
        {results.length > 0 && (
          <div className="mt-6 space-y-3">
            {results.map((r, i) => (
              <div key={i} className="border-l-[3px] border-black pl-4">
                <div className="flex flex-wrap items-center gap-2 mb-1">
                  {r.company && <span className="chip chip-active text-[10px]">{r.company}</span>}
                  {r.round && <span className="text-[11px] text-[var(--color-text-secondary)]">{r.round}</span>}
                  <span className="text-[10px] font-[family-name:var(--font-mono)]">score:{r.score}</span>
                </div>
                {r.question ? <div><p className="text-[13px] font-bold">Q: {r.question}</p><p className="text-[13px] text-[var(--color-text-secondary)]">A: {(r.answer || "").slice(0, 200)}</p></div> : <p className="text-[13px] text-[var(--color-text-secondary)]">{(r.raw_text || r.search_text || "").slice(0, 200)}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
