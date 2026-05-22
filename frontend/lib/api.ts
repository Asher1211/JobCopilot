import { BACKEND_URL } from "./constants";

class ApiError extends Error {
  constructor(
    public status: number,
    detail: string,
  ) {
    super(detail);
    this.name = "ApiError";
  }
}

async function request<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${BACKEND_URL}${path}`, options);

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || "Request failed");
  }

  return res.json();
}

export function apiGet<T = unknown>(path: string): Promise<T> {
  const token = getToken();
  return request<T>(path, {
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
}

export function apiPost<T = unknown>(
  path: string,
  body: unknown,
): Promise<T> {
  const token = getToken();
  return request<T>(path, {
    method: "POST",
    headers: {
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      "Content-Type": "application/json",
    },
    body: JSON.stringify(body),
  });
}

export function apiUpload<T = unknown>(
  path: string,
  formData: FormData,
): Promise<T> {
  const token = getToken();
  // Do NOT set Content-Type — browser auto-sets multipart/form-data boundary
  return request<T>(path, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });
}

export async function apiStream(
  path: string,
  formData: FormData,
): Promise<ReadableStream<Uint8Array>> {
  const token = getToken();
  const res = await fetch(`${BACKEND_URL}${path}`, {
    method: "POST",
    headers: token ? { Authorization: `Bearer ${token}` } : {},
    body: formData,
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    throw new ApiError(res.status, body.detail || "Request failed");
  }

  const stream = res.body;
  if (!stream) throw new Error("No response stream");
  return stream;
}

function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return localStorage.getItem("token");
}

export { ApiError };
export { BACKEND_URL };
