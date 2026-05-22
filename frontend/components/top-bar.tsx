"use client";

import { useAuth } from "@/lib/auth";
import Link from "next/link";
import { useRouter } from "next/navigation";

export function TopBar() {
  const { user, logout } = useAuth();
  const router = useRouter();

  return (
    <header className="fixed top-0 left-0 right-0 z-50 flex items-center justify-between px-6 py-4 bg-black text-white border-b-[3px] border-white h-[60px]">
      <Link href="/" className="flex items-center gap-3 !text-white no-underline">
        <img src="/logo.png" alt="JC" className="h-[28px] w-auto" />
        <span className="font-[family-name:var(--font-heading)] text-[16px] uppercase tracking-[0.05em]">
          Job Copilot
        </span>
      </Link>

      <nav className="flex items-center gap-6">
        <Link
          href="/analysis"
          className="font-[family-name:var(--font-mono)] text-[13px] !text-white/70 hover:!text-white no-underline transition-colors"
        >
          Analysis
        </Link>
        <Link
          href="/experiences"
          className="font-[family-name:var(--font-mono)] text-[13px] !text-white/70 hover:!text-white no-underline transition-colors"
        >
          Experiences
        </Link>
        <Link
          href="/research"
          className="font-[family-name:var(--font-mono)] text-[13px] !text-white/70 hover:!text-white no-underline transition-colors"
        >
          Research
        </Link>

        {user ? (
          <>
            <Link
              href="/settings"
              className="font-[family-name:var(--font-mono)] text-[13px] !text-white/70 hover:!text-white no-underline transition-colors"
            >
              Settings
            </Link>
            <span className="font-[family-name:var(--font-mono)] text-[12px] text-white/50">
              {user.display_name || user.email}
            </span>
            <button
              onClick={() => {
                logout();
                router.push("/");
              }}
              className="btn btn-sm !border-white/50 !text-white/50 hover:!border-white hover:!text-white cursor-pointer"
              style={{ borderWidth: 2 }}
            >
              Sign Out
            </button>
          </>
        ) : (
          <Link
            href="/auth/login"
            className="btn btn-sm !border-white !text-white hover:!bg-white hover:!text-black"
            style={{ borderWidth: 2 }}
          >
            Sign In
          </Link>
        )}
      </nav>
    </header>
  );
}
