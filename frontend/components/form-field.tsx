import type { ReactNode } from "react";

interface Props {
  label: string;
  htmlFor?: string;
  children: ReactNode;
  error?: string;
  hint?: string;
}

export function FormField({ label, htmlFor, children, error, hint }: Props) {
  return (
    <div>
      <label htmlFor={htmlFor} className="label">
        {label}
      </label>
      {children}
      {hint && !error && <p className="helper-text">{hint}</p>}
      {error && <p className="error-text animate-slide-up">{error}</p>}
    </div>
  );
}
