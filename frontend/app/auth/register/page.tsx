"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { useAuth } from "@/lib/auth";
import { PASSWORD_MIN_LENGTH, ROUTES } from "@/lib/constants";
import { FormField } from "@/components/form-field";
import { PasswordInput } from "@/components/password-input";

export default function RegisterPage() {
  const { register, user, loading } = useAuth();
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [displayName, setDisplayName] = useState("");
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
      await register(email, password, displayName || undefined);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Registration failed");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="flex min-h-[80vh] items-center justify-center px-6">
      <div className="card w-full max-w-[440px] p-10">
        <h3 className="mb-2">Register</h3>
        <p className="mb-8 text-[var(--color-text-secondary)]">
          Create an account to start your AI-powered job prep
        </p>

        <form onSubmit={handleSubmit} className="flex flex-col gap-6">
          <FormField label="Name (optional)" htmlFor="displayName">
            <input
              id="displayName"
              type="text"
              className="input"
              value={displayName}
              onChange={(e) => setDisplayName(e.target.value)}
              placeholder="Your name"
            />
          </FormField>

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
              placeholder={`Min ${PASSWORD_MIN_LENGTH} characters`}
              minLength={PASSWORD_MIN_LENGTH}
              autoComplete="new-password"
            />
          </FormField>

          <button
            type="submit"
            className="btn btn-primary btn-md w-full"
            disabled={submitting}
          >
            {submitting ? "Signing up..." : "Sign Up"}
          </button>
        </form>

        <p className="mt-6 text-center text-[14px] text-[var(--color-text-secondary)]">
          Already have an account?{" "}
          <Link href={ROUTES.login}>Sign In</Link>
        </p>
      </div>
    </div>
  );
}
