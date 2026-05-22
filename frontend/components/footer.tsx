export function Footer() {
  return (
    <footer className="fixed bottom-0 left-0 right-0 z-50 bg-black text-white px-6 py-5 border-t-[3px] border-white">
      <div className="mx-auto max-w-[960px] flex flex-col md:flex-row justify-between items-center gap-3">
        <span className="flex items-center gap-3">
          <img src="/logo.png" alt="JC" className="h-[20px] w-auto" />
          <span className="font-[family-name:var(--font-heading)] text-[12px] uppercase tracking-[0.1em]">
            Job Copilot
          </span>
          <span className="hidden md:inline text-[11px] text-white/40 font-[family-name:var(--font-body)]">
            AI-Powered Career Companion
          </span>
        </span>
        <span className="flex items-center gap-4 text-[11px] font-[family-name:var(--font-mono)] text-white/50">
          <span>Resume Analysis</span>
          <span>Mock Interview</span>
          <span>Company Research</span>
          <span>&copy; 2026</span>
        </span>
      </div>
    </footer>
  );
}
