"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startResearch, executeSearch, crawlUrl, extractUrls } from "@/lib/api";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Search, Globe, FileText, Pickaxe, Settings2, ChevronDown, ChevronUp } from "lucide-react";
import ProfileDisplay, { ProfileData } from "@/components/ProfileDisplay";

type ActionType = "research" | "search" | "extract" | "crawl";

export default function Home() {
  const [inputValue, setInputValue] = useState("");
  const [actionType, setActionType] = useState<ActionType>("research");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [resultContent, setResultContent] = useState("");
  const [profiles, setProfiles] = useState<{ profile: ProfileData; raw_text: string; url: string }[]>([]);

  // Advanced options state
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [searchTopic, setSearchTopic] = useState("general");
  const [searchDepth, setSearchDepth] = useState("basic");
  const [searchDays, setSearchDays] = useState(30);

  const router = useRouter();

  const tabs = [
    { id: "research", label: "Research", icon: <Pickaxe className="w-4 h-4" /> },
    { id: "search", label: "Search", icon: <Search className="w-4 h-4" /> },
    { id: "extract", label: "Extract", icon: <FileText className="w-4 h-4" /> },
    { id: "crawl", label: "Crawl", icon: <Globe className="w-4 h-4" /> },
  ];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const payload = inputValue.trim();
    if (!payload) return;

    setLoading(true);
    setError("");
    setResultContent("");

    try {
      if (actionType === "research") {
        const job = await startResearch(payload);

        // Save to Sidebar History
        try {
          const historyItem = { id: job.job_id, title: payload, date: new Date().toISOString() };
          const pastRaw: unknown = JSON.parse(localStorage.getItem("mra_history") || "[]");
          const past = Array.isArray(pastRaw) ? pastRaw : [];

          // Prevent duplicates and ignore malformed entries.
          const filtered = past
            .filter((item): item is { id: string; title?: string; date?: string } => {
              return !!item && typeof item === "object" && typeof (item as { id?: unknown }).id === "string";
            })
            .filter((item) => item.id !== job.job_id)
            .slice(0, 19);

          localStorage.setItem("mra_history", JSON.stringify([historyItem, ...filtered]));
          window.dispatchEvent(new Event("mra_history_updated"));
        } catch (e) {
          console.error("Failed to save history", e);
        }

        router.push(`/report/${job.job_id}`);
      } else if (actionType === "crawl") {
        const { crawlUrl } = await import("@/lib/api");
        const res = await crawlUrl(payload);

        if (res.results && res.results.length > 0) {
          // Combine content from all crawled sub-pages
          const combinedContent = res.results
            .map((r: any) => `## Source: [${r.url}](${r.url})\n\n${r.raw_content}`)
            .join("\n\n---\n\n");
          setResultContent(combinedContent || "No content found on this domain.");
          window.dispatchEvent(new Event("mra_history_updated"));
        } else if (res.failed_results && res.failed_results.length > 0) {
          throw new Error(`Tavily failed to crawl URL: ${res.failed_results[0].error || 'Protected or inaccessible'}`);
        } else {
          throw new Error("No results found. The URL may be protected from scraping.");
        }
      } else if (actionType === "extract") {
        const { extractUrls } = await import("@/lib/api");
        const res = await extractUrls([payload]);

        if (res.results && res.results.length > 0) {
          // Extract content from the specific URL
          setResultContent(`## Source: [${res.results[0].url}](${res.results[0].url})\n\n${res.results[0].raw_content}`);
          window.dispatchEvent(new Event("mra_history_updated"));
        } else if (res.failed_results && res.failed_results.length > 0) {
          throw new Error(`Tavily failed to extract URL: ${res.failed_results[0].error || 'Protected or inaccessible'}`);
        } else {
          throw new Error("No results found. The URL may be protected from scraping.");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : `${actionType} failed`);
    } finally {
      if (actionType !== "research") setLoading(false);
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

        {/* Unified Input with Action Selector */}
        <form onSubmit={handleSubmit} className="w-full">
          <div className="glass-card flex items-center gap-2 p-2 transition-all duration-200">
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
              value={inputValue}
              onChange={(e) => setInputValue(e.target.value)}
              placeholder={
                actionType === "research"
                  ? "Enter a company name — e.g. Zomato, Stripe, AWS…"
                  : "Enter a URL — e.g. https://example.com"
              }
              className="flex-1 bg-transparent py-3 px-2 text-lg text-foreground placeholder:text-muted/60 focus:outline-none"
              disabled={loading}
              autoFocus
            />

            {/* Action Selector */}
            <div className="relative flex items-center">
              <select
                value={actionType}
                onChange={(e) => setActionType(e.target.value as ActionType)}
                className="appearance-none bg-white/5 border border-white/10 rounded-lg py-3 pl-4 pr-10 text-sm font-medium text-foreground focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary disabled:opacity-50 cursor-pointer"
                disabled={loading}
              >
                <option value="research">Research</option>
                <option value="crawl">Crawl</option>
                <option value="extract">Extract</option>
              </select>
              <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2 text-muted">
                <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7"></path>
                </svg>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading || !inputValue.trim()}
              className="flex items-center gap-2 rounded-xl bg-primary px-6 py-3 text-sm font-semibold text-white transition-all duration-150 hover:bg-primary-hover active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed ml-2"
            >
              {loading ? (
                <>
                  <span className="flex gap-1">
                    <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                    <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                    <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                  </span>
                  Processing…
                </>
              ) : (
                "Run"
              )}
            </button>
          </div>
        </form>

        {/* Error */}
        {error && (
          <div className="glass-card w-full border-danger/30 p-4 text-left text-sm text-danger mt-4 animate-fade-in">
            <strong>Error:</strong> {error}
          </div>
        )}

        {/* Generic Result Area */}
        {resultContent && actionType !== "research" && (
          <div className="glass-card mt-4 w-full animate-fade-in p-6 text-left">
            <h2 className="text-xl font-semibold mb-4 border-b border-white/10 pb-4">
              {actionType === "crawl" ? "Crawl Result" : "Extraction Result"}
            </h2>
            <div className="prose prose-sm prose-invert max-w-none break-all">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  img: ({ node, ...props }) => {
                    if (!props.src || props.src === "") return null;
                    return <img {...props} />;
                  },
                }}
              >
                {resultContent}
              </ReactMarkdown>
            </div>
          </div>
        )}

        {/* Subtle footer info */}
        <p className="mt-8 text-xs text-muted/40">
          Powered by NVIDIA Nemotron Nano on E2E Networks — reports in ~30 seconds
        </p>
      </main>
    </div>
  );
}
