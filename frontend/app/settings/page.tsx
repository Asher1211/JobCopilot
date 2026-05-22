"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth";
import { apiGet, apiPost } from "@/lib/api";
import { API, ROUTES } from "@/lib/constants";

interface LLMConfig {
  api_key: string;
  base_url: string;
  model: string;
}

interface ConfigResponse {
  has_llm: boolean;
  llm_model: string;
  has_tavily: boolean;
}

export default function SettingsPage() {
  const { user, loading } = useAuth();
  const router = useRouter();
  const [config, setConfig] = useState<ConfigResponse | null>(null);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("");
  const [model, setModel] = useState("deepseek-chat");
  const [tavily, setTavily] = useState("");
  const [msg, setMsg] = useState("");
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (!loading && !user) { router.push(ROUTES.login); return; }
    if (user) loadConfig();
  }, [user, loading]);

  async function loadConfig() {
    try {
      const c = await apiGet<ConfigResponse>(API.user.config);
      setConfig(c);
    } catch { /* ignore */ }
  }

  function handleProviderHint(hint: string) {
    if (hint === "deepseek") {
      setModel("deepseek-chat");
      setBaseUrl("https://api.deepseek.com/v1");
    } else if (hint === "openai") {
      setModel("gpt-4o");
      setBaseUrl("");
    } else if (hint === "groq") {
      setModel("llama-3.3-70b-versatile");
      setBaseUrl("https://api.groq.com/openai/v1");
    } else if (hint === "ollama") {
      setModel("llama3");
      setBaseUrl("http://localhost:11434/v1");
    }
  }

  async function handleSave() {
    setSaving(true);
    setMsg("");
    try {
      await apiPost(API.user.config, {
        llm: {
          api_key: apiKey || undefined,
          base_url: baseUrl || undefined,
          model: model || undefined,
        },
        tavily_api_key: tavily || undefined,
      });
      setApiKey(""); setBaseUrl(""); setModel("deepseek-chat"); setTavily("");
      setMsg("Saved.");
      await loadConfig();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  if (loading || !user) return null;

  return (
    <div className="flex-1 px-6 py-12 max-w-[600px] mx-auto w-full">
      <h2 className="mb-2">Settings</h2>
      <p className="mb-12 text-lg text-[var(--color-text-secondary)]">
        Configure your own LLM provider. Supports any OpenAI-compatible API:
        DeepSeek, OpenAI, Groq, Together, Ollama, vLLM, and more.
      </p>

      <div className="card p-8 space-y-6">
        {/* Quick select */}
        <div>
          <span className="label">Quick Setup</span>
          <div className="flex flex-wrap gap-2 mt-1">
            {["deepseek", "openai", "groq", "ollama"].map((p) => (
              <button
                key={p}
                type="button"
                onClick={() => handleProviderHint(p)}
                className="chip cursor-pointer"
              >
                {p === "deepseek" ? "DeepSeek" : p === "openai" ? "OpenAI" : p === "groq" ? "Groq" : "Ollama"}
              </button>
            ))}
          </div>
        </div>

        <div>
          <label className="label">API Key</label>
          <input
            type="password"
            className="input"
            value={apiKey}
            onChange={(e) => setApiKey(e.target.value)}
            placeholder={config?.has_llm ? "•••••••• (set new to replace)" : "sk-..."}
          />
        </div>

        <div>
          <label className="label">Base URL</label>
          <input
            type="text"
            className="input"
            value={baseUrl}
            onChange={(e) => setBaseUrl(e.target.value)}
            placeholder="Leave empty for OpenAI/DeepSeek auto-detect"
          />
          <p className="helper-text">
            For custom providers: Groq, Together, Ollama, vLLM, etc.
          </p>
        </div>

        <div>
          <label className="label">Model Name</label>
          <input
            type="text"
            className="input"
            value={model}
            onChange={(e) => setModel(e.target.value)}
            placeholder="deepseek-chat"
          />
        </div>

        {/* Status */}
        {config && (
          <div className="flex gap-3 text-[11px] font-[family-name:var(--font-mono)]">
            <span className={config.has_llm ? "text-[var(--color-success)]" : "text-[var(--color-text-secondary)]"}>
              LLM: {config.has_llm ? config.llm_model : "not configured"}
            </span>
          </div>
        )}

        <hr className="divider" />

        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="label mb-0">Tavily API Key</span>
            {config?.has_tavily && (
              <span className="chip chip-active text-[10px]">Configured</span>
            )}
          </div>
          <input
            type="password"
            className="input"
            value={tavily}
            onChange={(e) => setTavily(e.target.value)}
            placeholder="tvly-... (for company research)"
          />
        </div>

        {msg && (
          <p className={`text-[13px] font-[family-name:var(--font-mono)] ${msg === "Saved." ? "text-[var(--color-success)]" : "text-[var(--color-error)]"}`}>
            {msg}
          </p>
        )}

        <button
          onClick={handleSave}
          className="btn btn-primary btn-md w-full"
          disabled={saving}
        >
          {saving ? "Saving..." : "Save"}
        </button>
      </div>
    </div>
  );
}
