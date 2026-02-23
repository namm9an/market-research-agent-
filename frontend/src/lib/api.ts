// Typed API client for the Market Research Agent backend

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";

// ── Types ──────────────────────────────────────────────

export type JobStatus =
    | "queued"
    | "searching"
    | "analyzing"
    | "compiling"
    | "completed"
    | "failed";

export interface Source {
    url: string;
    title: string;
}

export interface Trend {
    title: string;
    description: string;
    relevance: "high" | "medium" | "low";
}

export interface SWOT {
    strengths: string[];
    weaknesses: string[];
    opportunities: string[];
    threats: string[];
}

export interface ResearchReport {
    company_overview: string;
    swot: SWOT;
    trends: Trend[];
    competitive_landscape: string;
    key_findings: string[];
    sources: Source[];
}

export interface ResearchJob {
    job_id: string;
    status: JobStatus;
    query: string;
    type: string;
    created_at: string;
    completed_at: string | null;
    duration_seconds: number | null;
    report: ResearchReport | null;
    error: string | null;
    qa_history: { question: string; answer: string }[];
    qa_remaining: number;
}

export interface AskResponse {
    answer: string;
    question: string;
    remaining_questions: number;
    suggested_questions: string[];
}

export interface HealthResponse {
    status: string;
    model: string;
    vllm_connected: boolean;
    tavily_configured: boolean;
}

// ── API Functions ──────────────────────────────────────

async function apiFetch<T>(
    path: string,
    options?: RequestInit
): Promise<T> {
    const res = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers: {
            "Content-Type": "application/json",
            ...options?.headers,
        },
    });

    if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: res.statusText }));
        throw new Error(err.detail || `API error: ${res.status}`);
    }

    return res.json();
}

/** Start a new research job */
export async function startResearch(query: string, type = "company") {
    return apiFetch<ResearchJob>("/api/research", {
        method: "POST",
        body: JSON.stringify({ query, type }),
    });
}

/** Get the status / results of a research job */
export async function getJob(jobId: string) {
    return apiFetch<ResearchJob>(`/api/research/${jobId}`);
}

/** List all jobs */
export async function listJobs() {
    return apiFetch<ResearchJob[]>("/api/jobs");
}

/** Ask a follow-up question about a report */
export async function askQuestion(jobId: string, question: string) {
    return apiFetch<AskResponse>(`/api/research/${jobId}/ask`, {
        method: "POST",
        body: JSON.stringify({ question }),
    });
}

/** Download report as blob (PDF or Markdown) */
export async function exportReport(
    jobId: string,
    format: "pdf" | "md" | "json" = "pdf"
): Promise<Blob> {
    const res = await fetch(
        `${API_BASE}/api/research/${jobId}/export?format=${format}`
    );
    if (!res.ok) {
        if (res.status === 404) {
            throw new Error("Report not found — the backend may have restarted. Please re-run the research.");
        }
        throw new Error("Export failed");
    }
    return res.blob();
}

/** Health check */
export async function healthCheck() {
    return apiFetch<HealthResponse>("/api/health");
}

/** Extract content from a URL */
export interface ExtractResponse {
    url: string;
    content: string;
    word_count: number;
}

export async function extractUrl(url: string) {
    return apiFetch<ExtractResponse>("/api/extract", {
        method: "POST",
        body: JSON.stringify({ url }),
    });
}

