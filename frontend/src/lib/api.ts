// Since we now use Next.js rewrites to proxy /api to the backend,
// all fetch requests should just use relative paths (e.g. /api/research).
const API_BASE = "";

// ── Types ──────────────────────────────────────────────

export type JobStatus =
    | "queued"
    | "searching"
    | "analyzing"
    | "compiling"
    | "completed"
    | "failed";

export type JobKind = "research" | "crawl" | "extract" | "search";

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

export interface LeaderProfile {
    name: string;
    title: string;
    function: string;
    source_url: string;
    evidence: string;
    confidence: "high" | "medium" | "low" | string;
}

export interface ICPFitAssessment {
    fit_score: number;
    fit_tier: "high" | "medium" | "low" | string;
    summary: string;
    reasons: string[];
    recommended_pitch_angles: string[];
    concerns: string[];
}

export interface RevenueYear {
    year: string;
    amount: string;
}

export interface CompanyFinancials {
    core_business_summary: string;
    market_cap: string;
    funding_stage: string;
    revenue_history: RevenueYear[];
}

export interface FundingMilestone {
    date_or_round: string;
    amount: string;
    investors: string[];
}

export interface FundingIntelligence {
    investor_types: string[];
    funding_timeline: FundingMilestone[];
    capital_allocation_purpose: string;
    e2e_compute_lead_status: string;
    compute_spending_evidence: string;
}

export interface ResearchReport {
    company_overview: string;
    financials: CompanyFinancials;
    funding_intelligence: FundingIntelligence;
    swot: SWOT;
    trends: Trend[];
    competitive_landscape: string;
    key_findings: string[];
    leaders: LeaderProfile[];
    icp_fit: ICPFitAssessment;
    sources: Source[];
}

export interface ResearchJob {
    job_id: string;
    job_kind: JobKind;
    status: JobStatus;
    query: string;
    type: string;
    created_at: string;
    completed_at: string | null;
    duration_seconds: number | null;
    report: ResearchReport | null;
    operation_result: Record<string, unknown> | null;
    error: string | null;
    qa_history: { question: string; answer: string }[];
    qa_remaining: number;
}

export interface JobListItem {
    job_id: string;
    job_kind: JobKind;
    query: string;
    status: JobStatus;
    created_at: string;
    duration_seconds: number | null;
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
    return apiFetch<JobListItem[]>("/api/jobs");
}

/** Delete a job from history */
export async function deleteJob(jobId: string) {
    return apiFetch<{ success: boolean; job_id: string }>(`/api/jobs/${jobId}`, {
        method: "DELETE",
    });
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
export async function extractUrls(urls: string[]) {
    return apiFetch<unknown>("/api/extract", {
        method: "POST",
        body: JSON.stringify({ urls }),
    });
}

export async function crawlUrl(url: string) {
    return apiFetch<unknown>("/api/crawl", {
        method: "POST",
        body: JSON.stringify({ url }),
    });
}

export async function executeSearch(
    query: string,
    topic = "general",
    search_depth = "basic",
    max_results = 10,
    days = 30
) {
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    return apiFetch<any>("/api/search", {
        method: "POST",
        body: JSON.stringify({
            query,
            topic,
            search_depth,
            max_results,
            days,
        }),
    });
}
