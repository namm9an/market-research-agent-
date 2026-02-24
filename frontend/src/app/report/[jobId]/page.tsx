"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { getJob, type ResearchJob, type JobStatus } from "@/lib/api";
import StatusStepper from "@/components/StatusStepper";
import ReportHeader from "@/components/ReportHeader";
import SwotCard from "@/components/SwotCard";
import TrendsList from "@/components/TrendsList";
import FindingsList from "@/components/FindingsList";
import SourcesList from "@/components/SourcesList";
import ExportButtons from "@/components/ExportButtons";
import QAChat from "@/components/QAChat";
import Link from "next/link";

const POLL_INTERVAL = 3000;

export default function ReportPage() {
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

        poll();
        return () => clearTimeout(timer);
    }, [fetchJob]);

    const isLoading =
        job &&
        job.status !== "completed" &&
        job.status !== "failed";
    const isComplete = job?.status === "completed" && job.report;
    const isFailed = job?.status === "failed" || error;

    return (
        <div className="min-h-screen px-4 py-8">
            {/* Nav */}
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
                    New Research
                </Link>
                {isComplete && <ExportButtons jobId={jobId} query={job!.query} />}
            </nav>

            <div className="mx-auto max-w-4xl">
                {/* Title */}
                {job && (
                    <h1 className="mb-8 text-3xl font-bold tracking-tight sm:text-4xl">
                        {job.query}
                    </h1>
                )}

                {/* Status stepper (during loading) */}
                {isLoading && <StatusStepper status={job.status} />}

                {/* Error */}
                {isFailed && (
                    <div className="glass-card border-danger/30 p-6">
                        <h2 className="mb-2 text-lg font-semibold text-danger">
                            Research Failed
                        </h2>
                        <p className="text-sm text-muted">
                            {error || job?.error || "An unknown error occurred."}
                        </p>
                        <Link
                            href="/"
                            className="mt-4 inline-flex items-center gap-2 rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-white transition-all hover:bg-primary-hover active:scale-95"
                        >
                            Try Again
                        </Link>
                    </div>
                )}

                {/* Completed report */}
                {isComplete && job.report && (
                    <div className="flex flex-col gap-8">
                        <ReportHeader job={job} />

                        {/* Company Overview */}
                        <section className="glass-card p-6">
                            <h2 className="mb-4 text-lg font-semibold">Company Overview</h2>
                            <p className="whitespace-pre-line text-sm leading-relaxed text-muted">
                                {job.report.company_overview}
                            </p>
                        </section>

                        <SwotCard swot={job.report.swot} />

                        <TrendsList trends={job.report.trends} />

                        {/* Competitive Landscape */}
                        <section className="glass-card p-6">
                            <h2 className="mb-4 text-lg font-semibold">
                                Competitive Landscape
                            </h2>
                            <p className="whitespace-pre-line text-sm leading-relaxed text-muted">
                                {job.report.competitive_landscape}
                            </p>
                        </section>

                        <FindingsList findings={job.report.key_findings} />

                        <SourcesList sources={job.report.sources} />

                        {/* Q&A */}
                        <QAChat
                            jobId={jobId}
                            history={job.qa_history}
                            remaining={job.qa_remaining}
                        />
                    </div>
                )}
            </div>
        </div>
    );
}
