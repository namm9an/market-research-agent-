"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startResearch } from "@/lib/api";

export default function Home() {
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;

    setLoading(true);
    setError("");

    try {
      const job = await startResearch(query.trim());
      router.push(`/report/${job.job_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
      setLoading(false);
    }
  }

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center px-4">
      {/* Background gradient orbs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-[500px] w-[500px] rounded-full bg-primary/10 blur-[120px]" />
        <div className="absolute -bottom-40 -right-40 h-[500px] w-[500px] rounded-full bg-primary/5 blur-[120px]" />
      </div>

      {/* Main content */}
      <main className="relative z-10 flex w-full max-w-2xl flex-col items-center gap-8 text-center">
        {/* Logo / Title */}
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15">
            <svg
              className="h-7 w-7 text-primary"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M9.75 3.104v5.714a2.25 2.25 0 0 1-.659 1.591L5 14.5M9.75 3.104c-.251.023-.501.05-.75.082m.75-.082a24.301 24.301 0 0 1 4.5 0m0 0v5.714c0 .597.237 1.17.659 1.591L19.8 15.3M14.25 3.104c.251.023.501.05.75.082M19.8 15.3l-1.57.393A9.065 9.065 0 0 1 12 15a9.065 9.065 0 0 0-6.23.693L5 14.5m14.8.8 1.402 1.402c1.232 1.232.65 3.318-1.067 3.611A48.309 48.309 0 0 1 12 21c-2.773 0-5.491-.235-8.135-.687-1.718-.293-2.3-2.379-1.067-3.61L5 14.5"
              />
            </svg>
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Market Research Agent
          </h1>
          <p className="max-w-md text-muted text-lg">
            AI-powered company analysis. SWOT, trends, competitive landscape
            — generated in seconds.
          </p>
        </div>

        {/* Search form */}
        <form onSubmit={handleSubmit} className="w-full">
          <div className="glass-card flex items-center gap-3 p-2 transition-all duration-200">
            <svg
              className="ml-3 h-5 w-5 shrink-0 text-muted"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={1.5}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z"
              />
            </svg>
            <input
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Enter a company name — e.g. Zomato, Stripe, AWS…"
              className="flex-1 bg-transparent py-3 text-lg text-foreground placeholder:text-muted/60 focus:outline-none"
              disabled={loading}
              autoFocus
            />
            <button
              type="submit"
              disabled={loading || !query.trim()}
              className="flex items-center gap-2 rounded-full bg-primary px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-hover active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <span className="flex gap-1">
                    <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                    <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                    <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                  </span>
                  Starting…
                </>
              ) : (
                "Research"
              )}
            </button>
          </div>
        </form>

        {/* Error */}
        {error && (
          <div className="glass-card w-full border-danger/30 p-4 text-left text-sm text-danger">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Subtle footer info */}
        <p className="mt-4 text-xs text-muted/40">
          Powered by NVIDIA Nemotron Nano on E2E Networks — reports in ~30 seconds
        </p>
      </main>
    </div>
  );
}
