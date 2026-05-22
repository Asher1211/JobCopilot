"use client";

import { useCallback, useRef, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiStream } from "@/lib/api";
import { readSSE } from "@/lib/sse";
import { API, ROUTES, SCORE_THRESHOLDS } from "@/lib/constants";
import { FileInput } from "@/components/file-input";
import { LoadingIndicator } from "@/components/loading-indicator";

interface AnalysisResult {
  match_score: number;
  missing_skills: string[];
  strengths: string[];
  suggestions: string;
  route: string;
  resume_text: string;
  prep_advice?: string;
  optimized_html?: string;
  changes_summary?: string;
  optimize_error?: string;
}

type Status = "idle" | "parsing" | "analyzing" | "done" | "error";

export default function AnalysisPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [file, setFile] = useState<File | null>(null);
  const [jdText, setJdText] = useState("");
  const [status, setStatus] = useState<Status>("idle");
  const [result, setResult] = useState<AnalysisResult | null>(null);
  const [streamTokens, setStreamTokens] = useState("");
  const [error, setError] = useState("");
  const hasResult = useRef(false);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !jdText.trim()) return;
    setStatus("parsing");
    setResult(null);
    hasResult.current = false;
    setStreamTokens("");
    setError("");

    const formData = new FormData();
    formData.append("file", file);
    formData.append("jd_text", jdText.trim());

    try {
      const stream = await apiStream(API.analysis.match, formData);
      await readSSE(stream, (event, data) => {
        const d = data as Record<string, string>;
        switch (event) {
          case "node_start":
            if (d.node === "match_analysis") setStatus("analyzing");
            setStreamTokens("");
            break;
          case "stream": setStreamTokens((p) => p + d.token); break;
          case "result":
            if (!hasResult.current) { hasResult.current = true; setResult(data as unknown as AnalysisResult); setStatus("done"); }
            else {
              if (d.advice) setResult((p) => p ? { ...p, prep_advice: d.advice } : p);
              if (d.html) setResult((p) => p ? { ...p, optimized_html: d.html, changes_summary: d.changes_summary || "" } : p);
              if (d.error && !d.html && !d.advice) setResult((p) => p ? { ...p, optimize_error: d.error } : p);
            }
            break;
          case "error": setError(d.message); setStatus("error"); break;
        }
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unknown error");
      setStatus("error");
    }
  }, [file, jdText]);

  if (loading) return null;
  if (!user) {
    return (
      <div className="flex min-h-[80vh] items-center justify-center px-6">
        <div className="card p-10 max-w-[440px] w-full text-center">
          <h4 className="mb-4">Please Sign In</h4>
          <p className="mb-8 text-[var(--color-text-secondary)]">Sign in to upload your resume for AI matching.</p>
          <Link href={ROUTES.login} className="btn btn-primary btn-md">Go to Sign In</Link>
        </div>
      </div>
    );
  }

  return (
    <div className="flex-1 px-6 py-12 md:px-12 max-w-[1200px] mx-auto w-full">
      <h2 className="mb-2">Resume &times; JD Matching</h2>
      <p className="mb-12 text-lg text-[var(--color-text-secondary)]">
        Upload your resume (.docx / .pdf) and paste the target job description. AI analyzes your match score and delivers actionable suggestions.
      </p>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
        <div className="card border-r-0 max-lg:border-r-[3px] max-lg:border-b-0 p-8">
          <form onSubmit={handleSubmit} className="flex flex-col gap-6">
            <div>
              <label className="label">Upload Resume</label>
              <FileInput accept=".docx,.pdf" label="Choose File (.docx / .pdf)" onChange={setFile} />
              <p className="helper-text">Supports .docx (Word) and .pdf formats</p>
            </div>
            <div>
              <label htmlFor="jd" className="label">Job Description (JD)</label>
              <textarea id="jd" className="input min-h-[280px] resize-y" value={jdText} onChange={(e) => setJdText(e.target.value)} required placeholder="Paste the job description here..." />
            </div>
            <button type="submit" disabled={status === "parsing" || status === "analyzing"} className="btn btn-primary btn-md w-full">
              {status === "parsing" ? "Parsing..." : status === "analyzing" ? "Analyzing..." : "Start Analysis"}
            </button>
          </form>
        </div>

        <div className="card p-8 min-h-[500px]">
          {status === "idle" && <IdlePlaceholder />}
          {(status === "parsing" || status === "analyzing") && (
            <div>
              <LoadingIndicator text={status === "parsing" ? "Parsing resume..." : "AI analyzing match..."} />
              {streamTokens && (
                <div className="mt-6 font-[family-name:var(--font-mono)] text-[13px] leading-relaxed whitespace-pre-wrap p-4 bg-[var(--color-surface-sunken)]">
                  {streamTokens}<span className="animate-pulse">_</span>
                </div>
              )}
            </div>
          )}
          {status === "done" && result && <ResultView result={result} jdText={jdText} onStartInterview={() => {
            sessionStorage.setItem("interview_context", JSON.stringify({
              jd_text: jdText, resume_text: result.resume_text || "",
              match_score: result.match_score, strengths: result.strengths, missing_skills: result.missing_skills,
            }));
            router.push(ROUTES.interview);
          }} />}
          {status === "error" && <ErrorState message={error} />}
        </div>
      </div>
    </div>
  );
}

function OptimizedResumePreview({ html, summary }: { html: string; summary: string }) {
  const handleExport = () => {
    const w = window.open("", "_blank");
    if (w) { w.document.write(html); w.document.close(); }
  };

  return (
    <div className="border-t-[3px] border-black pt-6 mt-6">
      <div className="flex items-center justify-between mb-3">
        <h4>Optimized Resume</h4>
        <button onClick={handleExport} className="btn btn-primary btn-sm">Export PDF (Ctrl+P)</button>
      </div>
      {summary && <p className="text-[13px] text-[var(--color-text-secondary)] mb-4 font-[family-name:var(--font-mono)]">{summary}</p>}
      <div className="border-[2px] border-black max-h-[400px] overflow-y-auto bg-white">
        <iframe srcDoc={html} className="w-full h-[400px] border-0" title="Optimized Resume Preview" />
      </div>
    </div>
  );
}

function IdlePlaceholder() {
  return <div className="flex items-center justify-center h-full min-h-[400px]"><p className="text-[var(--color-text-secondary)]">Results will appear here in real-time</p></div>;
}

function ErrorState({ message }: { message: string }) {
  return <div className="flex flex-col items-center justify-center h-full min-h-[400px] text-center"><p className="text-[var(--color-error)] mb-4 font-[family-name:var(--font-heading)] uppercase tracking-wider">Analysis Failed</p><p className="text-[var(--color-text-secondary)]">{message}</p></div>;
}

function ResultView({ result, jdText, onStartInterview }: { result: AnalysisResult; jdText: string; onStartInterview: () => void }) {
  return (
    <div>
      <button onClick={onStartInterview} className="btn btn-primary btn-md w-full mb-8">Start Mock Interview</button>
      <div className="flex items-end gap-4 mb-8 border-b-[3px] border-black pb-6">
        <span className="font-[family-name:var(--font-heading)] text-[80px] leading-none" style={{ color: result.match_score >= 70 ? "var(--color-success)" : result.match_score >= 50 ? "var(--color-warning)" : "var(--color-error)" }}>{result.match_score}</span>
        <div className="mb-2"><span className="label block">{result.match_score >= 90 ? "Excellent Match" : result.match_score >= 70 ? "Good Match" : result.match_score >= 50 ? "Partial Match" : result.match_score >= 30 ? "Low Match" : "Poor Match"}</span><span className="text-[13px] text-[var(--color-text-secondary)]">/ 100</span></div>
      </div>
      <div className="mb-6">{result.route === "interview_prep" ? <span className="chip chip-active">Ready for interview prep</span> : <span className="chip" style={{ borderColor: "var(--color-warning)", color: "var(--color-warning)" }}>Consider resume optimization first</span>}</div>
      <div className="mb-6"><h4 className="mb-3">Strengths</h4><ul className="space-y-2">{result.strengths.map((s, i) => <li key={i} className="flex items-start gap-2 text-[15px]"><span className="text-[var(--color-success)] mt-1">+</span>{s}</li>)}</ul></div>
      <div className="mb-6"><h4 className="mb-3">Missing Skills</h4><div className="flex flex-wrap gap-2">{result.missing_skills.map((s, i) => <span key={i} className="chip" style={{ borderColor: "var(--color-error)", color: "var(--color-error)" }}>{s}</span>)}</div></div>
      <div className="mb-6"><h4 className="mb-3">Suggestions</h4><p className="text-[14px] leading-relaxed text-[var(--color-text-secondary)] bg-[var(--color-surface-sunken)] p-4">{result.suggestions}</p></div>
      {result.prep_advice && <div className="border-t-[3px] border-black pt-6 mt-6"><h4 className="mb-3">Preparation Guide</h4><p className="text-[14px] leading-relaxed text-[var(--color-text-secondary)] bg-[var(--color-surface-sunken)] p-4 whitespace-pre-line">{result.prep_advice}</p></div>}
      {result.optimize_error && <div className="border-t-[3px] border-black pt-6 mt-6"><h4 className="mb-2 text-[var(--color-error)]">Optimization Failed</h4><p className="text-[13px] text-[var(--color-text-secondary)] font-[family-name:var(--font-mono)]">{result.optimize_error}</p></div>}
      {result.optimized_html && <OptimizedResumePreview html={result.optimized_html} summary={result.changes_summary || ""} />}
    </div>
  );
}
