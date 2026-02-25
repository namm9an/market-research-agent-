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
    setProfiles([]);

    try {
      if (actionType === "research") {
        const job = await startResearch(payload);

        // Save to Sidebar History
        try {
          const historyItem = { id: job.job_id, title: payload, date: new Date().toISOString() };
          const pastRaw: unknown = JSON.parse(localStorage.getItem("mra_history") || "[]");
          const past = Array.isArray(pastRaw) ? pastRaw : [];

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
      } else if (actionType === "search") {
        const res = await executeSearch(payload, searchTopic, searchDepth, 15, searchDays);
        if (res.results && res.results.length > 0) {
          const combinedContent = res.results
            .map((r: { title: string; url: string; content: string }) => `### [${r.title}](${r.url})\n\n${r.content}`)
            .join("\n\n---\n\n");
          setResultContent(`## Search Results\n\n${combinedContent}`);
          window.dispatchEvent(new Event("mra_history_updated"));
        } else {
          throw new Error("No results found.");
        }
      } else if (actionType === "crawl") {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const res = await crawlUrl(payload) as any;
        if (res.structured_results && res.structured_results.length > 0) {
          setProfiles(res.structured_results);
          window.dispatchEvent(new Event("mra_history_updated"));
        } else if (res.failed_results && res.failed_results.length > 0) {
          throw new Error(`Tavily failed to crawl URL: ${res.failed_results[0].error || 'Protected or inaccessible'}`);
        } else {
          throw new Error("No results found. The URL may be protected from scraping.");
        }
      } else if (actionType === "extract") {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const res = await extractUrls([payload]) as any;
        if (res.structured_results && res.structured_results.length > 0) {
          setProfiles(res.structured_results);
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

  // Determine placeholder based on tab
  let placeholder = "Enter a company or industry name...";
  if (actionType === "search") placeholder = "Ask any question or search topic...";
  if (actionType === "crawl" || actionType === "extract") placeholder = "https://example.com";

  return (
    <div className="relative min-h-screen flex flex-col items-center justify-center px-4">
      {/* Background gradient orbs */}
      <div className="pointer-events-none absolute inset-0 overflow-hidden">
        <div className="absolute -top-40 -left-40 h-[500px] w-[500px] rounded-full bg-primary/10 blur-[120px]" />
        <div className="absolute -bottom-40 -right-40 h-[500px] w-[500px] rounded-full bg-primary/5 blur-[120px]" />
      </div>

      {/* Main content */}
      <main className="relative z-10 flex w-full max-w-3xl flex-col items-center gap-8 text-center mt-12 mb-20">
        {/* Logo / Title */}
        <div className="flex flex-col items-center gap-3">
          <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/15">
            <Pickaxe className="h-7 w-7 text-primary" />
          </div>
          <h1 className="text-4xl font-bold tracking-tight sm:text-5xl">
            Market Research Agent
          </h1>
          <p className="max-w-md text-muted text-lg">
            AI-powered company analysis. SWOT, trends, competitive landscape
            — generated in seconds.
          </p>
        </div>

        {/* 4-Tab Landing Page Container */}
        <div className="w-full mt-6">
          {/* Tabs Navigation */}
          <div className="flex w-full items-center justify-center gap-2 mb-6">
            <div className="flex p-1 bg-white/5 border border-white/10 rounded-2xl backdrop-blur-md">
              {tabs.map((tab) => (
                <button
                  key={tab.id}
                  type="button"
                  onClick={() => {
                    setActionType(tab.id as ActionType);
                    setResultContent("");
                    setError("");
                    setShowAdvanced(false);
                  }}
                  className={`flex items-center gap-2 px-6 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${actionType === tab.id
                    ? "bg-primary text-white shadow-lg shadow-primary/25"
                    : "text-muted hover:text-white hover:bg-white/5"
                    }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>
          </div>

          {/* Input Form */}
          <form onSubmit={handleSubmit} className="w-full flex flex-col items-center">
            <div className="w-full glass-card flex items-center p-2 transition-all duration-200 focus-within:ring-2 focus-within:ring-primary/50 focus-within:border-primary">
              <div className="pl-4 pr-2 text-primary">
                {actionType === "search" ? <Search className="w-6 h-6" /> :
                  actionType === "crawl" ? <Globe className="w-6 h-6" /> :
                    actionType === "extract" ? <FileText className="w-6 h-6" /> :
                      <Pickaxe className="w-6 h-6" />}
              </div>
              <input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                placeholder={placeholder}
                className="flex-1 bg-transparent py-4 px-2 text-lg text-foreground placeholder:text-muted/50 focus:outline-none"
                disabled={loading}
                autoFocus
              />

              <button
                type="submit"
                disabled={loading || !inputValue.trim()}
                className="flex items-center gap-2 rounded-xl bg-primary px-8 py-4 text-base font-semibold text-white transition-all duration-150 hover:bg-primary-hover active:scale-95 disabled:opacity-40 disabled:cursor-not-allowed ml-2"
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

            {/* Advanced Options Toggle */}
            {actionType === "search" && (
              <div className="w-full mt-4 flex flex-col items-end">
                <button
                  type="button"
                  onClick={() => setShowAdvanced(!showAdvanced)}
                  className="flex items-center gap-1.5 text-xs font-medium text-muted hover:text-white transition-colors"
                >
                  <Settings2 className="w-3.5 h-3.5" />
                  Advanced Options
                  {showAdvanced ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
                </button>

                {/* Advanced Drawer */}
                {showAdvanced && (
                  <div className="w-full mt-3 glass-card p-4 grid grid-cols-1 sm:grid-cols-3 gap-4 text-left animate-fade-in border border-white/10">
                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-medium text-muted uppercase tracking-wider">Search Topic</label>
                      <select
                        value={searchTopic}
                        onChange={(e) => setSearchTopic(e.target.value)}
                        className="bg-black/20 border border-white/10 rounded-lg py-2 px-3 text-sm focus:border-primary focus:outline-none font-sans"
                      >
                        <option value="general">General Web</option>
                        <option value="news">News Articles</option>
                      </select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-medium text-muted uppercase tracking-wider">Search Depth</label>
                      <select
                        value={searchDepth}
                        onChange={(e) => setSearchDepth(e.target.value)}
                        className="bg-black/20 border border-white/10 rounded-lg py-2 px-3 text-sm focus:border-primary focus:outline-none font-sans"
                      >
                        <option value="basic">Basic (Faster)</option>
                        <option value="advanced">Advanced (Deeper)</option>
                      </select>
                    </div>

                    <div className="flex flex-col gap-1.5">
                      <label className="text-xs font-medium text-muted uppercase tracking-wider">Recency (Days)</label>
                      <input
                        type="number"
                        min="1" max="365"
                        value={searchDays}
                        onChange={(e) => setSearchDays(Number(e.target.value) || 30)}
                        className="bg-black/20 border border-white/10 rounded-lg py-2 px-3 text-sm focus:border-primary focus:outline-none font-sans"
                      />
                    </div>
                  </div>
                )}
              </div>
            )}
          </form>
        </div>

        {/* Error */}
        {error && (
          <div className="glass-card w-full border-danger/30 p-4 text-left text-sm text-danger mt-4 animate-fade-in flex items-center justify-between">
            <span><strong>Error:</strong> {error}</span>
            <button onClick={() => setError("")} className="text-xs underline hover:text-white">Dismiss</button>
          </div>
        )}

        {/* Generic Search Result Area */}
        {resultContent && actionType === "search" && (
          <div className="glass-card mt-4 w-full animate-fade-in p-6 text-left overflow-hidden">
            <h2 className="text-xl font-semibold mb-4 border-b border-white/10 pb-4 flex items-center gap-2">
              <Search className="w-5 h-5 text-primary" />
              Search Results
            </h2>
            <div className="prose prose-sm prose-invert max-w-none">
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  // eslint-disable-next-line @next/next/no-img-element, @typescript-eslint/no-unused-vars
                  img: ({ node, ...props }) => {
                    if (!props.src || props.src === "") return null;
                    return <img {...props} alt={props.alt || "Markdown internal image"} />;
                  },
                  // eslint-disable-next-line @typescript-eslint/no-unused-vars
                  pre: ({ node, ...props }) => (
                    <div className="overflow-x-auto bg-black/40 rounded-lg p-4 my-4 border border-white/10 custom-scrollbar">
                      <pre {...props} className="bg-transparent p-0 m-0 text-xs" />
                    </div>
                  ),
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
