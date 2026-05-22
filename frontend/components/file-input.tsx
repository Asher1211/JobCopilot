"use client";

import { useState } from "react";

interface Props {
  accept: string;
  label?: string;
  onChange: (file: File | null) => void;
}

export function FileInput({ accept, label, onChange }: Props) {
  const [fileName, setFileName] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] || null;
    setFileName(f ? f.name : "");
    onChange(f);
  };

  return (
    <div>
      <label className="btn btn-secondary btn-md cursor-pointer inline-flex max-w-[260px] truncate">
        {fileName ? (fileName.length > 25 ? fileName.slice(0, 12) + "..." + fileName.slice(-8) : fileName) : (label || `Choose File (${accept})`)}
        <input
          type="file"
          accept={accept}
          onChange={handleChange}
          className="hidden"
        />
      </label>
    </div>
  );
}
