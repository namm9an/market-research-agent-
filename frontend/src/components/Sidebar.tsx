"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";

interface HistoryItem {
    id: string;
    title: string;
    date: string;
}

export default function Sidebar() {
    const [history, setHistory] = useState<HistoryItem[]>([]);
    const pathname = usePathname();

    const loadHistory = () => {
        try {
            const stored = localStorage.getItem("mra_history");
            if (stored) {
                setHistory(JSON.parse(stored));
            }
        } catch (e) {
            console.error("Failed to load history", e);
        }
    };

    useEffect(() => {
        loadHistory();

        // Listen to custom event when a new job is created
        const handleUpdate = () => loadHistory();
        window.addEventListener("mra_history_updated", handleUpdate);
        return () => window.removeEventListener("mra_history_updated", handleUpdate);
    }, []);

    return (
        <div className="w-64 shrink-0 bg-[#0A0A0B] border-r border-[#1F1F22] h-full flex flex-col hidden md:flex overflow-hidden">
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
                        const isActive = pathname.includes(item.id);
                        return (
                            <Link
                                key={item.id}
                                href={`/report/${item.id}`}
                                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm transition-colors duration-200 group ${isActive
                                        ? "bg-primary/20 text-primary font-medium"
                                        : "text-muted hover:bg-white/5 hover:text-foreground"
                                    }`}
                            >
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
                            </Link>
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
