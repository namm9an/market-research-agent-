"use client";

import { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { extractUrls } from "@/lib/api";

export default function UrlExtractor() {
    const [url, setUrl] = useState("");
    const [content, setContent] = useState("");
    const [wordCount, setWordCount] = useState(0);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    async function handleExtract(e: React.FormEvent) {
        e.preventDefault();
        const trimmed = url.trim();
        if (!trimmed) return;

        setLoading(true);
        setError("");
        setContent("");

        try {
            const res = await extractUrls([trimmed]);
            if (res.results && res.results.length > 0) {
                setContent(res.results[0].raw_content);
                setWordCount(res.results[0].raw_content.split(/\s+/).length);
            } else if (res.failed_results && res.failed_results.length > 0) {
                throw new Error(`Extraction failed: ${res.failed_results[0].error}`);
            } else {
                throw new Error("No content extracted");
            }
        } catch (err) {
            setError(err instanceof Error ? err.message : "Extraction failed");
        } finally {
            setLoading(false);
        }
    }

    return (
        <section className="glass-card p-6">
            <div className="mb-4">
                <h2 className="text-lg font-semibold">Crawl &amp; Extract</h2>
                <p className="text-xs text-muted/60 mt-1">
                    Extract content from any URL using Tavily
                </p>
            </div>

            <form onSubmit={handleExtract} className="flex gap-2 mb-4">
                <input
                    type="url"
                    value={url}
                    onChange={(e) => setUrl(e.target.value)}
                    placeholder="https://example.com/article..."
                    className="flex-1 rounded-full border border-card-border bg-card-bg px-4 py-2.5 text-sm text-foreground placeholder:text-muted/40 focus:border-primary focus:outline-none"
                    disabled={loading}
                    required
                />
                <button
                    type="submit"
                    disabled={loading || !url.trim()}
                    className="rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-white transition-all hover:bg-primary-hover active:scale-95 disabled:opacity-40"
                >
                    {loading ? (
                        <span className="flex gap-1">
                            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                            <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                        </span>
                    ) : (
                        "Extract"
                    )}
                </button>
            </form>

            {error && (
                <p className="text-sm text-danger mb-3">{error}</p>
            )}

            {content && (
                <div>
                    <div className="flex items-center gap-3 mb-3">
                        <span className="rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
                            {wordCount.toLocaleString()} words
                        </span>
                        <button
                            onClick={() => navigator.clipboard.writeText(content)}
                            className="rounded-full border border-card-border bg-card-bg px-3 py-1 text-xs text-muted hover:text-foreground transition-colors"
                        >
                            Copy
                        </button>
                    </div>
                    <div className="qa-markdown max-h-96 overflow-y-auto rounded-lg border border-card-border bg-background/50 p-4 text-sm text-muted">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                            {content.length > 5000 ? content.slice(0, 5000) + "\n\n*...truncated for display...*" : content}
                        </ReactMarkdown>
                    </div>
                </div>
            )}
        </section>
    );
}
