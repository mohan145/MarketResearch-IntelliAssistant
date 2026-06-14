// Base URL: localhost:8000 in local dev (EventSource doesn't work well through proxies)
// In production: set VITE_API_BASE_URL to the Azure Container Apps backend URL
const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? (import.meta.env.DEV ? "http://localhost:8000" : "");

function authHeaders(): HeadersInit {
  const token = localStorage.getItem("token");
  return token ? { Authorization: `Bearer ${token}` } : {};
}

export interface ResearchRequest {
  competitors: string[];
  topics: string[];
  urls: string[];
}

export interface SourceRef {
  url: string;
  excerpt: string;
}

export interface Insight {
  theme: string;
  finding: string;
  sources: SourceRef[];
}

export interface CompetitorActivity {
  competitor: string;
  activity: string;
  sources: SourceRef[];
}

export interface JudgeVerdict {
  claim: string;
  supported: boolean;
  confidence: number;
  explanation: string;
  source_url: string;
}

export interface MarketSummary {
  executive_summary: string;
  key_themes: Insight[];
  competitor_activities: CompetitorActivity[];
  generated_at: string;
}

export interface PipelineResult {
  summary: MarketSummary;
  verdicts: JudgeVerdict[];
  hallucination_count: number;
  run_duration_seconds: number;
}

export interface Run {
  id: number;
  topics: string[];
  competitors: string[];
  urls: string[];
  hallucination_count: number;
  run_duration_seconds: number;
  created_at: string;
  result: PipelineResult;
}

// Opens an SSE stream for a research run.
// Caller handles 'message' events for progress and 'result' event for final output.
export function streamResearch(payload: ResearchRequest): EventSource {
  // Build query params from ResearchRequest
  const params = new URLSearchParams();
  params.append("competitors", JSON.stringify(payload.competitors));
  params.append("topics", JSON.stringify(payload.topics));
  params.append("urls", JSON.stringify(payload.urls));
  params.append("llm_provider", "google"); // Default to google; can be extended later

  const token = localStorage.getItem("token");
  let url = `${BASE_URL}/api/research/run?${params.toString()}`;
  if (token) {
    url += `&token=${token}`;
  }

  return new EventSource(url);
}

export async function getHistory(): Promise<Run[]> {
  const res = await fetch(`${BASE_URL}/api/research/history`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch history");
  return res.json();
}

export async function getRun(id: number): Promise<Run> {
  const res = await fetch(`${BASE_URL}/api/research/${id}`, {
    headers: authHeaders(),
  });
  if (!res.ok) throw new Error("Failed to fetch run");
  return res.json();
}

export async function login(
  email: string,
  password: string
): Promise<{ access_token: string }> {
  const res = await fetch(`${BASE_URL}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Invalid credentials");
  return res.json();
}

export async function register(
  email: string,
  password: string
): Promise<void> {
  const res = await fetch(`${BASE_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email, password }),
  });
  if (!res.ok) throw new Error("Registration failed");
}