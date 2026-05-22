"use client";

import { useState } from "react";

interface Props {
  id?: string;
  value: string;
  onChange: (value: string) => void;
  required?: boolean;
  placeholder?: string;
  autoComplete?: string;
  minLength?: number;
}

export function PasswordInput({
  id = "password",
  value,
  onChange,
  required,
  placeholder = "••••••••",
  autoComplete,
  minLength,
}: Props) {
  const [show, setShow] = useState(false);

  return (
    <div className="password-wrap">
      <input
        id={id}
        type="text"
        className={`input pr-[72px] ${show ? "" : "password-masked"}`}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        required={required}
        placeholder={placeholder}
        autoComplete={autoComplete}
        minLength={minLength}
      />
      <button
        type="button"
        className="password-toggle"
        onClick={() => setShow(!show)}
        tabIndex={-1}
      >
        {show ? "Hide" : "Show"}
      </button>
    </div>
  );
}
