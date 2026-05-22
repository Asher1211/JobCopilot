"use client";

import { useEffect, useState } from "react";
import { useAuth } from "@/lib/auth";
import { fetchSSE } from "@/lib/sse";
import { API, BACKEND_URL, ROUTES } from "@/lib/constants";

interface ResearchResult {
  company_overview: string; tech_stack: string[]; interview_style: string;
  culture: string; salary_range: string; preparation_tips: string | string[];
  sources: string[]; error?: string;
}

export default function ResearchPage() {
  const { user, loading } = useAuth();
  const [company, setCompany] = useState("");
  const [status, setStatus] = useState<"idle" | "loading" | "done" | "error">("idle");
  const [result, setResult] = useState<ResearchResult | null>(null);
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { if (!loading && !user) window.location.href = ROUTES.login; }, [user, loading]);

  if (loading) return null;
  if (!user) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault(); if (!company.trim()) return;
    setStatus("loading"); setResult(null); setError(""); setSubmitting(true);
    try {
      await fetchSSE(`${BACKEND_URL}${API.research.search}`, { company_name: company.trim() }, (event, data) => {
        const d = data as Record<string, unknown>;
        if (event === "result") { setResult(d as unknown as ResearchResult); setStatus("done"); }
        else if (event === "error") { setError(typeof d === "string" ? d : (d as Record<string,string>).message); setStatus("error"); }
      }, localStorage.getItem("token"));
    } catch (err) { setError(err instanceof Error ? err.message : "Research failed"); setStatus("error"); } finally { setSubmitting(false); }
  }

  return (
    <div className="flex-1 px-6 py-12 md:px-12 max-w-[960px] mx-auto w-full">
      <h2 className="mb-2">Company Research</h2>
      <p className="mb-12 text-lg text-[var(--color-text-secondary)]">Enter a company name. AI searches the web for tech stack, interview style, and preparation tips.</p>
      <form onSubmit={handleSubmit} className="flex gap-4 mb-12">
        <input type="text" className="input flex-1" value={company} onChange={(e) => setCompany(e.target.value)} required placeholder="Company name (e.g. Google, Stripe)" />
        <button type="submit" className="btn btn-primary btn-md shrink-0" disabled={submitting}>{submitting ? "Researching..." : "Search"}</button>
      </form>
      {status === "loading" && <div className="card p-8"><div className="flex items-center gap-3"><div className="w-4 h-4 border-[3px] border-black animate-pulse" /><span className="label">Searching and analyzing...</span></div></div>}
      {status === "done" && result && <ResultCard result={result} />}
      {status === "error" && <div className="card p-8 text-center"><p className="text-[var(--color-error)] font-[family-name:var(--font-heading)] uppercase mb-2">Research Failed</p><p className="text-[var(--color-text-secondary)]">{error}</p></div>}
    </div>
  );
}

function ResultCard({ result }: { result: ResearchResult }) {
  return (
    <div className="card p-8 space-y-6">
      <Section title="Overview" content={result.company_overview} />
      {result.tech_stack.length > 0 && <div><h4 className="mb-3">Tech Stack</h4><div className="flex flex-wrap gap-2">{result.tech_stack.map((t, i) => <span key={i} className="chip">{t}</span>)}</div></div>}
      <Section title="Interview Style" content={result.interview_style} />
      <Section title="Culture" content={result.culture} />
      <Section title="Salary Range" content={result.salary_range} />
      {Array.isArray(result.preparation_tips) ? <div><h4 className="mb-3">Preparation Tips</h4><ul className="space-y-2">{result.preparation_tips.map((tip: string, i: number) => <li key={i} className="flex items-start gap-2 text-[15px]"><span className="text-[var(--color-success)] mt-1">+</span>{tip}</li>)}</ul></div> : <Section title="Preparation Tips" content={String(result.preparation_tips)} />}
      {result.sources.length > 0 && <div className="border-t-[2px] border-black pt-4 mt-4"><h4 className="mb-2">Sources</h4><ul className="space-y-1">{result.sources.map((url, i) => <li key={i}><a href={url} target="_blank" rel="noopener noreferrer" className="text-[13px]">{url}</a></li>)}</ul></div>}
      {result.error && <p className="text-[var(--color-warning)] text-[13px] font-[family-name:var(--font-mono)]">Note: {result.error}</p>}
    </div>
  );
}

function Section({ title, content }: { title: string; content: string }) {
  if (!content || content === "Not publicly available") return null;
  return <div><h4 className="mb-2">{title}</h4><p className="text-[15px] leading-relaxed text-[var(--color-text-secondary)]">{content}</p></div>;
}
