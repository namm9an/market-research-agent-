"use client";

import { useState } from "react";
import { exportReport } from "@/lib/api";

function download(blob: Blob, filename: string) {
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}

export default function ExportButtons({
    jobId,
    query,
}: {
    jobId: string;
    query: string;
}) {
    const [error, setError] = useState("");

    async function handleExport(format: "pdf" | "md") {
        setError("");
        try {
            const blob = await exportReport(jobId, format);
            const ext = format === "pdf" ? "pdf" : "md";
            download(blob, `${query}_report.${ext}`);
        } catch (err) {
            setError(err instanceof Error ? err.message : "Export failed");
        }
    }

    return (
        <div className="flex items-center gap-2">
            <button
                onClick={() => handleExport("pdf")}
                className="flex items-center gap-1.5 rounded-full border border-card-border bg-card-bg px-4 py-2 text-xs font-medium text-muted transition-all hover:bg-card-bg-hover hover:text-foreground active:scale-95"
            >
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
                        d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3"
                    />
                </svg>
                PDF
            </button>
            <button
                onClick={() => handleExport("md")}
                className="flex items-center gap-1.5 rounded-full border border-card-border bg-card-bg px-4 py-2 text-xs font-medium text-muted transition-all hover:bg-card-bg-hover hover:text-foreground active:scale-95"
            >
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
                        d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z"
                    />
                </svg>
                Markdown
            </button>
            {error && (
                <span className="text-xs text-danger">{error}</span>
            )}
        </div>
    );
}
