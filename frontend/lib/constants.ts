export const BACKEND_URL =
  process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export const ROUTES = {
  home: "/",
  login: "/auth/login",
  register: "/auth/register",
  analysis: "/analysis",
  research: "/research",
  interview: "/interview",
  settings: "/settings",
} as const;

export const API = {
  auth: {
    login: "/api/auth/login",
    register: "/api/auth/register",
    me: "/api/auth/me",
  },
  analysis: {
    match: "/api/analysis/match",
  },
  research: {
    search: "/api/research/search",
  },
  interview: {
    start: "/api/interview/start",
    chat: "/api/interview/chat",
  },
  health: "/api/health",
  experiences: {
    upload: "/api/experiences/upload",
    list: "/api/experiences/list",
    search: "/api/experiences/search",
  },
  user: {
    config: "/api/user/config",
  },
} as const;

export const SCORE_THRESHOLDS = {
  excellent: 90,
  good: 70,
  partial: 50,
  low: 30,
  routeToInterview: 60,
} as const;

export const PASSWORD_MIN_LENGTH = 6;
