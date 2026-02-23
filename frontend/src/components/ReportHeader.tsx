import type { ResearchJob } from "@/lib/api";

export default function ReportHeader({ job }: { job: ResearchJob }) {
    const completedAt = job.completed_at
        ? new Date(job.completed_at).toLocaleDateString("en-US", {
            year: "numeric",
            month: "long",
            day: "numeric",
            hour: "2-digit",
            minute: "2-digit",
        })
        : null;

    return (
        <div className="flex flex-wrap items-center gap-3 text-sm text-muted">
            {completedAt && (
                <span className="glass-card inline-flex items-center gap-1.5 px-3 py-1.5">
                    <svg
                        className="h-3.5 w-3.5"
                        fill="none"
                        viewBox="0 0 24 24"
                        stroke="currentColor"
                        strokeWidth={1.5}
                    >
                        <path
                            strokeLinecap="round"
                            strokeLinejoin="round"
                            d="M12 6v6h4.5m4.5 0a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z"
                        />
                    </svg>
                    {completedAt}
                </span>
            )}
            {job.duration_seconds != null && (
                <span className="glass-card inline-flex items-center gap-1.5 px-3 py-1.5">
                    ⚡ {job.duration_seconds.toFixed(1)}s
                </span>
            )}
            {job.report?.sources && (
                <span className="glass-card inline-flex items-center gap-1.5 px-3 py-1.5">
                    📄 {job.report.sources.length} sources
                </span>
            )}
        </div>
    );
}
