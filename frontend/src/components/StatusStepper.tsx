"use client";

import type { JobStatus } from "@/lib/api";

const STEPS: { key: JobStatus; label: string }[] = [
    { key: "queued", label: "Queued" },
    { key: "searching", label: "Searching the web" },
    { key: "analyzing", label: "Analyzing data" },
    { key: "compiling", label: "Compiling report" },
    { key: "completed", label: "Done" },
];

const STATUS_ORDER: Record<JobStatus, number> = {
    queued: 0,
    searching: 1,
    analyzing: 2,
    compiling: 3,
    completed: 4,
    failed: -1,
};

export default function StatusStepper({ status }: { status: JobStatus }) {
    const current = STATUS_ORDER[status] ?? 0;

    return (
        <div className="glass-card mx-auto max-w-lg p-8">
            <div className="mb-6 text-center">
                <h2 className="text-lg font-semibold">Generating your report…</h2>
                <p className="mt-1 text-sm text-muted">This typically takes 30–60 seconds</p>
            </div>

            <div className="flex flex-col gap-1">
                {STEPS.map((step, i) => {
                    const isActive = i === current;
                    const isDone = i < current;

                    return (
                        <div key={step.key} className="flex items-center gap-4 py-2.5">
                            {/* Dot */}
                            <div className="relative flex h-8 w-8 shrink-0 items-center justify-center">
                                {isActive ? (
                                    <>
                                        <div className="absolute h-8 w-8 animate-ping rounded-full bg-primary/30" />
                                        <div className="h-3 w-3 rounded-full bg-primary" />
                                    </>
                                ) : isDone ? (
                                    <div className="flex h-6 w-6 items-center justify-center rounded-full bg-success/20">
                                        <svg
                                            className="h-3.5 w-3.5 text-success"
                                            fill="none"
                                            viewBox="0 0 24 24"
                                            stroke="currentColor"
                                            strokeWidth={3}
                                        >
                                            <path
                                                strokeLinecap="round"
                                                strokeLinejoin="round"
                                                d="m4.5 12.75 6 6 9-13.5"
                                            />
                                        </svg>
                                    </div>
                                ) : (
                                    <div className="h-2 w-2 rounded-full bg-muted/30" />
                                )}
                            </div>

                            {/* Label */}
                            <span
                                className={`text-sm font-medium transition-colors ${isActive
                                        ? "text-foreground"
                                        : isDone
                                            ? "text-success"
                                            : "text-muted/40"
                                    }`}
                            >
                                {step.label}
                            </span>
                        </div>
                    );
                })}
            </div>
        </div>
    );
}
