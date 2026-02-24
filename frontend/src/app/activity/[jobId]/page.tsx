"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useParams } from "next/navigation";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { getJob, type JobStatus, type ResearchJob } from "@/lib/api";

const POLL_INTERVAL = 3000;

interface TavilyResultItem {
    url: string;
    title: string;
    raw_content: string;
    content: string;
}

function normalizeResults(operationResult: Record<string, unknown> | null): TavilyResultItem[] {
    if (!operationResult || typeof operationResult !== "object") return [];

    const rawResults = operationResult.results;
    if (!Array.isArray(rawResults)) return [];

    const results: TavilyResultItem[] = [];
    for (const entry of rawResults) {
        if (!entry || typeof entry !== "object") continue;
        const item = entry as Record<string, unknown>;

        results.push({
            url: typeof item.url === "string" ? item.url : "",
            title: typeof item.title === "string" ? item.title : "",
            raw_content: typeof item.raw_content === "string" ? item.raw_content : "",
            content: typeof item.content === "string" ? item.content : "",
        });
    }

    return results;
}

function toMarkdown(results: TavilyResultItem[]): string {
    if (results.length === 0) return "No stored output found for this job.";

    return results
        .map((result) => {
            const header = result.url
                ? `## Source: [${result.url}](${result.url})`
                : "## Source";
            const body = result.raw_content || result.content || "No content extracted.";
            return `${header}\n\n${body}`;
        })
        .join("\n\n---\n\n");
}

export default function ActivityJobPage() {
    const params = useParams();
    const jobId = params.jobId as string;

    const [job, setJob] = useState<ResearchJob | null>(null);
    const [error, setError] = useState("");

    const fetchJob = useCallback(async () => {
        try {
            const data = await getJob(jobId);
            setJob(data);
            return data.status;
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to load job");
            return "failed" as JobStatus;
        }
    }, [jobId]);

    useEffect(() => {
        let timer: NodeJS.Timeout;

        async function poll() {
            const status = await fetchJob();
            if (status !== "completed" && status !== "failed") {
                timer = setTimeout(poll, POLL_INTERVAL);
            }
        }

        void poll();
        return () => clearTimeout(timer);
    }, [fetchJob]);

    const isLoading = !job || (job.status !== "completed" && job.status !== "failed");
    const isFailed = job?.status === "failed" || !!error;
    const isResearch = job?.job_kind === "research";
    const results = useMemo(() => normalizeResults(job?.operation_result ?? null), [job]);
    const markdown = useMemo(() => toMarkdown(results), [results]);

    return (
        <div className="min-h-screen px-4 py-8">
            <nav className="mx-auto mb-12 flex max-w-4xl items-center justify-between">
                <Link
                    href="/"
                    className="flex items-center gap-2 text-sm text-muted transition-colors hover:text-foreground"
                >
                    <svg
                        className="h-4 w-4"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={1.5}
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M10.5 19.5 3 12m0 0 7.5-7.5M3 12h18"
                        />
                    </svg>
                    New Search
                </Link>
            </nav>

            <div className="mx-auto max-w-4xl">
                {isLoading && (
                    <div className="glass-card p-6">
                        <p className="text-sm text-muted">Loading activity...</p>
                    </div>
                )}

                {isFailed && (
                    <div className="glass-card border-danger/30 p-6">
                        <h2 className="mb-2 text-lg font-semibold text-danger">Job Failed</h2>
                        <p className="text-sm text-muted">{error || job?.error || "Unknown error"}</p>
                    </div>
                )}

                {job && job.status === "completed" && isResearch && (
                    <div className="glass-card p-6">
                        <h2 className="mb-3 text-xl font-semibold">Research Report</h2>
                        <p className="text-sm text-muted mb-4">
                            This history entry is a research report.
                        </p>
                        <Link
                            href={`/report/${job.job_id}`}
                            className="inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-white transition-all hover:bg-primary-hover active:scale-95"
                        >
                            Open Report
                        </Link>
                    </div>
                )}

                {job && job.status === "completed" && !isResearch && (
                    <div className="glass-card p-6">
                        <div className="mb-4 flex items-center gap-2">
                            <h2 className="text-xl font-semibold capitalize">{job.job_kind} Result</h2>
                            <span className="rounded border border-white/10 px-2 py-0.5 text-[10px] uppercase tracking-wide text-muted/70">
                                {job.job_kind}
                            </span>
                        </div>
                        <p className="mb-5 text-sm text-muted break-all">{job.query}</p>
                        <div className="prose prose-sm prose-invert max-w-none break-all">
                            <ReactMarkdown remarkPlugins={[remarkGfm]}>
                                {markdown}
                            </ReactMarkdown>
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
}
