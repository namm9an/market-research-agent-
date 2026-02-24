"use client";

import { useCallback, useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { listJobs } from "@/lib/api";

type JobKind = "research" | "crawl" | "extract";

interface HistoryItem {
    id: string;
    title: string;
    date: string;
    kind: JobKind;
}

const HISTORY_KEY = "mra_history";
const MAX_HISTORY_ITEMS = 20;

interface JobHistoryItem {
    job_id: string;
    query: string;
    created_at: string;
    job_kind?: string;
}

function parseJobKind(value: unknown): JobKind {
    if (value === "crawl" || value === "extract" || value === "research") {
        return value;
    }
    return "research";
}

function readLocalHistory(): HistoryItem[] {
    try {
        const raw = localStorage.getItem(HISTORY_KEY);
        if (!raw) return [];

        const parsed: unknown = JSON.parse(raw);
        if (!Array.isArray(parsed)) return [];

        const normalized: HistoryItem[] = [];
        for (const entry of parsed) {
            if (!entry || typeof entry !== "object") continue;
            const item = entry as Record<string, unknown>;
            const id = typeof item.id === "string" ? item.id : "";
            if (!id) continue;

            normalized.push({
                id,
                title:
                    typeof item.title === "string" && item.title.trim()
                        ? item.title
                        : "Untitled research",
                date:
                    typeof item.date === "string" && item.date.trim()
                        ? item.date
                        : new Date(0).toISOString(),
                kind: parseJobKind(item.kind),
            });
        }

        return normalized.slice(0, MAX_HISTORY_ITEMS);
    } catch (e) {
        console.error("Failed to parse local history", e);
        return [];
    }
}

function mapJobsToHistory(jobs: JobHistoryItem[]): HistoryItem[] {
    return jobs
        .map((job) => ({
            id: job.job_id,
            title: job.query?.trim() || "Untitled research",
            date: job.created_at || new Date(0).toISOString(),
            kind: parseJobKind(job.job_kind),
        }))
        .slice(0, MAX_HISTORY_ITEMS);
}

function mergeHistory(primary: HistoryItem[], fallback: HistoryItem[]): HistoryItem[] {
    const merged = [...primary, ...fallback];
    const seen = new Set<string>();
    const deduped: HistoryItem[] = [];

    for (const item of merged) {
        if (!item.id || seen.has(item.id)) continue;
        seen.add(item.id);
        deduped.push(item);
        if (deduped.length >= MAX_HISTORY_ITEMS) break;
    }

    return deduped;
}

export default function Sidebar() {
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const pathname = usePathname();

    const loadHistory = useCallback(async () => {
        const localHistory = readLocalHistory();

        try {
            const jobs = await listJobs();
            const apiHistory = mapJobsToHistory(jobs as JobHistoryItem[]);
            const merged = mergeHistory(apiHistory, localHistory);
            setHistory(merged);
            localStorage.setItem(HISTORY_KEY, JSON.stringify(merged));
        } catch (e) {
            // Keep sidebar functional even if API is temporarily unavailable.
            setHistory(localHistory);
            console.error("Failed to load history from API", e);
        }
    }, []);

    useEffect(() => {
        const initialLoadTimer = window.setTimeout(() => {
            void loadHistory();
        }, 0);

        // Listen for new research submissions from the home page.
        const handleUpdate = () => {
            void loadHistory();
        };
        const handleStorage = (event: StorageEvent) => {
            if (event.key === HISTORY_KEY) {
                void loadHistory();
            }
        };

        window.addEventListener("mra_history_updated", handleUpdate);
        window.addEventListener("storage", handleStorage);
        return () => {
            window.clearTimeout(initialLoadTimer);
            window.removeEventListener("mra_history_updated", handleUpdate);
            window.removeEventListener("storage", handleStorage);
        };
    }, [loadHistory]);

    return (
        <div className="w-64 shrink-0 bg-[#0A0A0B] border-r border-[#1F1F22] h-full flex flex-col overflow-hidden">
            <div className="p-4 flex items-center justify-between">
                <h2 className="text-sm font-semibold text-muted font-inter tracking-wide uppercase">
                    Recent Research
                </h2>
                {/* New chat icon */}
                <Link
                    href="/"
                    className="text-muted hover:text-white transition-colors p-1"
                    title="New Research"
                >
                    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
                    </svg>
                </Link>
            </div>

            <div className="flex-1 overflow-y-auto px-2 pb-4 space-y-1">
                {history.length === 0 ? (
                    <div className="text-xs text-muted/50 p-2 italic text-center mt-4">
                        No recent research
                    </div>
                ) : (
                    history.map((item) => {
                        const isResearchItem = item.kind === "research";
                        const isActive = isResearchItem && pathname.includes(item.id);
                        const containerClass = `flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors duration-200 group ${isActive
                            ? "bg-primary/20 text-primary font-medium"
                            : "text-muted hover:bg-white/5 hover:text-foreground"
                            }`;
                        const content = (
                            <>
                                <svg
                                    className={`h-4 w-4 shrink-0 ${isActive ? "text-primary/70" : "text-muted/50 group-hover:text-muted"}`}
                                    fill="none"
                                    viewBox="0 0 24 24"
                                    stroke="currentColor"
                                    strokeWidth={2}
                                >
                                    <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m3.75 9v6m3-3H9m1.5-12H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                                </svg>
                                <span className="truncate flex-1">{item.title}</span>
                                <span className="rounded border border-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wide text-muted/70">
                                    {item.kind}
                                </span>
                            </>
                        );

                        if (isResearchItem) {
                            return (
                                <Link
                                    key={item.id}
                                    href={`/report/${item.id}`}
                                    className={containerClass}
                                >
                                    {content}
                                </Link>
                            );
                        }

                        return (
                            <div
                                key={item.id}
                                className={containerClass}
                            >
                                {content}
                            </div>
                        );
                    })
                )}
            </div>

            <div className="p-4 border-t border-[#1F1F22]">
                <div className="flex items-center gap-2 text-xs text-muted/60">
                    <div className="h-6 w-6 rounded bg-primary/20 flex items-center justify-center">
                        <span className="text-[10px] font-bold text-primary">N</span>
                    </div>
                    <span>NVIDIA Nemotron Nano</span>
                </div>
            </div>
        </div>
    );
}
