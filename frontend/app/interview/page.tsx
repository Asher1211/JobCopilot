"use client";

import { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { fetchSSE } from "@/lib/sse";
import { API, BACKEND_URL, ROUTES } from "@/lib/constants";

interface Message { role: "interviewer" | "candidate" | "system"; content: string; meta?: string; }

export default function InterviewPage() {
  const { user, loading } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [qCount, setQCount] = useState(0);
  const [status, setStatus] = useState<"idle" | "starting" | "active" | "evaluating" | "done" | "no_context">("idle");
  const [context, setContext] = useState<{ jd_text: string; resume_text: string; match_score: number; strengths: string[]; missing_skills: string[]; } | null>(null);
  const chatEnd = useRef<HTMLDivElement>(null);

  useEffect(() => { if (!loading && !user) window.location.href = ROUTES.login; }, [user, loading]);
  useEffect(() => {
    const raw = sessionStorage.getItem("interview_context");
    if (raw) { try { setContext(JSON.parse(raw)); } catch { /* ignore */ } }
    if (!raw) setStatus("no_context");
  }, []);
  useEffect(() => { chatEnd.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  if (loading) return null;

  async function handleStart() {
    if (!context) return;
    setStatus("starting"); setMessages([]); setQCount(1);
    try {
      await fetchSSE(`${BACKEND_URL}${API.interview.start}`, {
        jd_text: context.jd_text, resume_text: context.resume_text,
        match_score: context.match_score, strengths: context.strengths, missing_skills: context.missing_skills,
      }, (event, data) => {
        const d = data as Record<string, string>;
        if (event === "started") {
          setSessionId(d.session_id);
          setMessages([{ role: "interviewer", content: d.question, meta: `${d.topic} · ${d.difficulty}` }]);
          setStatus("active");
        }
      }, localStorage.getItem("token"));
    } catch (err) {
      setMessages([{ role: "system", content: "Failed: " + (err instanceof Error ? err.message : "Error") }]);
      setStatus("idle");
    }
  }

  async function handleSend() {
    if (!input.trim() || !sessionId) return;
    const answer = input.trim(); setInput("");
    setMessages((p) => [...p, { role: "candidate", content: answer }]);
    setStatus("evaluating");
    try {
      await fetchSSE(`${BACKEND_URL}${API.interview.chat}/${sessionId}`, { answer }, (event, data) => {
        const d = data as Record<string, string | number>;
        if (event === "feedback") {
          const parts: Message[] = [];
          if (d.feedback) parts.push({ role: "system", content: `Score: ${d.score}/10 — ${d.feedback}` });
          if (d.next_question && d.next_question !== "END") {
            parts.push({ role: "interviewer", content: d.next_question as string, meta: (d.topic as string) || "" });
            setQCount((c) => c + 1); setStatus("active");
          } else { parts.push({ role: "system", content: "Interview complete!" }); setStatus("done"); }
          setMessages((p) => [...p, ...parts]);
        }
      }, localStorage.getItem("token"));
    } catch (err) {
      setMessages((p) => [...p, { role: "system", content: "Error: " + (err instanceof Error ? err.message : "Unknown") }]);
      setStatus("active");
    }
  }

  if (status === "no_context") {
    return (
      <div className="flex min-h-[80vh] items-center justify-center px-6">
        <div className="card p-10 max-w-[440px] w-full text-center">
          <h4 className="mb-4">Complete Analysis First</h4>
          <p className="mb-8 text-[var(--color-text-secondary)]">Run a resume × JD match analysis first.</p>
          <Link href={ROUTES.analysis} className="btn btn-primary btn-md">Go to Analysis</Link>
        </div>
      </div>
    );
  }

  if (status === "idle" && context) {
    return (
      <div className="flex-1 px-6 py-12 max-w-[720px] mx-auto w-full">
        <h2 className="mb-2">Mock Interview</h2>
        <p className="mb-8 text-lg text-[var(--color-text-secondary)]">Personalized interview based on your resume analysis.</p>
        <div className="card p-8 space-y-4 mb-8">
          <div><span className="label">Match Score</span><span className="font-[family-name:var(--font-heading)] text-[32px] ml-2">{context.match_score}/100</span></div>
          {context.strengths.length > 0 && <div><span className="label">Strengths</span><div className="flex flex-wrap gap-1 mt-1">{context.strengths.map((s, i) => <span key={i} className="chip chip-active text-[10px]">{s}</span>)}</div></div>}
          {context.missing_skills.length > 0 && <div><span className="label">Areas to Probe</span><div className="flex flex-wrap gap-1 mt-1">{context.missing_skills.map((s, i) => <span key={i} className="chip" style={{ borderColor: "var(--color-error)", color: "var(--color-error)", fontSize: "10px" }}>{s}</span>)}</div></div>}
        </div>
        <button onClick={handleStart} className="btn btn-primary btn-lg w-full">Start Interview</button>
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col max-w-[800px] mx-auto w-full px-6 py-6">
      <h2 className="mb-4">Mock Interview</h2>
      <div className="card flex-1 flex flex-col min-h-[60vh] max-h-[70vh]">
        <div className="border-b-[3px] border-black px-6 py-3 flex items-center justify-between">
          <span className="font-[family-name:var(--font-heading)] text-[13px] uppercase tracking-[0.05em]">Question {qCount}/10</span>
          <button onClick={() => setStatus("done")} className="text-[11px] font-[family-name:var(--font-heading)] uppercase tracking-[0.05em] text-[var(--color-error)] hover:underline cursor-pointer">End Interview</button>
        </div>
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {status === "starting" && (
            <div className="flex items-center gap-3"><div className="w-4 h-4 border-[3px] border-black animate-pulse" /><span className="label">Generating first question...</span></div>
          )}
          {messages.map((msg, i) => (
            <div key={i} className={msg.role === "interviewer" ? "border-l-[3px] border-black pl-4" : msg.role === "candidate" ? "border-r-[3px] border-black pr-4 text-right" : "bg-[var(--color-surface-sunken)] p-3 text-[13px] font-[family-name:var(--font-mono)]"}>
              <div className="text-[11px] uppercase tracking-[0.1em] text-[var(--color-text-secondary)] mb-1 font-[family-name:var(--font-heading)]">{msg.role === "interviewer" ? "Interviewer" : msg.role === "candidate" ? "You" : "Feedback"}</div>
              <p className="text-[15px] leading-relaxed">{msg.content}</p>
              {msg.meta && <span className="text-[11px] text-[var(--color-text-secondary)] mt-1 inline-block">{msg.meta}</span>}
            </div>
          ))}
          <div ref={chatEnd} />
        </div>
        {(status === "active" || status === "evaluating") && (
          <div className="border-t-[3px] border-black p-4 flex gap-3">
            <input type="text" className="input flex-1" value={input} onChange={(e) => setInput(e.target.value)} onKeyDown={(e) => e.key === "Enter" && handleSend()} placeholder={status === "evaluating" ? "Evaluating..." : "Type your answer..."} disabled={status === "evaluating"} />
            <button onClick={handleSend} className="btn btn-primary btn-md shrink-0" disabled={status === "evaluating" || !input.trim()}>Send</button>
          </div>
        )}
        {status === "done" && (
          <div className="border-t-[3px] border-black p-6 text-center">
            <h4 className="mb-3">Interview Complete</h4>
            <p className="text-[var(--color-text-secondary)] mb-4">Review your feedback above. Start a new session to practice again.</p>
            <button onClick={() => { setStatus("idle"); setSessionId(null); setMessages([]); }} className="btn btn-secondary btn-md">New Interview</button>
          </div>
        )}
      </div>
    </div>
  );
}
