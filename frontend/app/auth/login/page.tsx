"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { ROUTES } from "@/lib/constants";
import { FormField } from "@/components/form-field";
import { PasswordInput } from "@/components/password-input";

export default function LoginPage() {
  const { login, user, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    if (!loading && user) router.push(ROUTES.analysis);
  }, [user, loading, router]);

  if (loading || user) return null;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Login failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-6">
      <div className="card w-full max-w-[440px] p-10">
        <h3 className="mb-2">Sign In</h3>
        <p className="mb-8 text-[var(--color-text-secondary)]">
          Sign in to view analysis history and interview reports
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          <FormField label="Email" htmlFor="email">
            <input
              id="email"
              type="email"
              className="input"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              placeholder="your@email.com"
            />
          </FormField>

          <FormField label="Password" htmlFor="password" error={error}>
            <PasswordInput
              value={password}
              onChange={setPassword}
              required
              autoComplete="current-password"
            />
          </FormField>

          <button
            type="submit"
            className="btn btn-primary btn-md w-full"
            disabled={submitting}
          >
            {submitting ? "Signing in..." : "Sign In"}
          </button>
        </form>

        <p className="mt-6 text-center text-[14px] text-[var(--color-text-secondary)]">
          Don&apos;t have an account?{" "}
          <Link href={ROUTES.register}>Register</Link>
        </p>
      </div>
    </div>
  );
}
