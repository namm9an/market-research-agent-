"use client";

import { useState } from "react";
import { askQuestion } from "@/lib/api";

interface QAChatProps {
    jobId: string;
    history: { question: string; answer: string }[];
    remaining: number;
}

export default function QAChat({ jobId, history, remaining }: QAChatProps) {
    const [question, setQuestion] = useState("");
    const [localHistory, setLocalHistory] = useState(history);
    const [localRemaining, setLocalRemaining] = useState(remaining);
    const [suggestions, setSuggestions] = useState<string[]>([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");

    async function handleAsk(q?: string) {
        const text = (q || question).trim();
        if (!text || localRemaining <= 0) return;

        setLoading(true);
        setError("");

        try {
            const res = await askQuestion(jobId, text);
            setLocalHistory((h) => [
                ...h,
                { question: text, answer: res.answer },
            ]);
            setLocalRemaining(res.remaining_questions);
            setSuggestions(res.suggested_questions || []);
            setQuestion("");
        } catch (err) {
            setError(err instanceof Error ? err.message : "Failed to ask");
        } finally {
            setLoading(false);
        }
    }

    function handleSubmit(e: React.FormEvent) {
        e.preventDefault();
        handleAsk();
    }

    return (
        <section className="glass-card p-6">
            <div className="mb-4 flex items-center justify-between">
                <h2 className="text-lg font-semibold">Follow-up Questions</h2>
                <span className="text-xs text-muted">
                    {localRemaining} / 10 remaining
                </span>
            </div>

            {/* History */}
            {localHistory.length > 0 && (
                <div className="mb-4 space-y-4">
                    {localHistory.map((qa, i) => (
                        <div key={i} className="space-y-2">
                            <div className="flex items-start gap-2">
                                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-primary/20 text-[10px] font-bold text-primary">
                                    Q
                                </span>
                                <p className="text-sm text-foreground">{qa.question}</p>
                            </div>
                            <div className="flex items-start gap-2">
                                <span className="mt-0.5 flex h-5 w-5 shrink-0 items-center justify-center rounded-full bg-success/20 text-[10px] font-bold text-success">
                                    A
                                </span>
                                <p className="whitespace-pre-line text-sm text-muted">
                                    {qa.answer}
                                </p>
                            </div>
                        </div>
                    ))}
                </div>
            )}

            {/* Proactive suggestions */}
            {suggestions.length > 0 && localRemaining > 0 && (
                <div className="mb-4">
                    <p className="mb-2 text-xs font-medium text-muted/60 uppercase tracking-wide">
                        Suggested questions
                    </p>
                    <div className="flex flex-wrap gap-2">
                        {suggestions.map((s, i) => (
                            <button
                                key={i}
                                onClick={() => handleAsk(s)}
                                disabled={loading}
                                className="rounded-full border border-primary/20 bg-primary/5 px-3 py-1.5 text-xs text-primary transition-all hover:bg-primary/15 hover:border-primary/40 active:scale-95 disabled:opacity-40 text-left"
                            >
                                {s}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Input */}
            {localRemaining > 0 ? (
                <form onSubmit={handleSubmit} className="flex gap-2">
                    <input
                        type="text"
                        value={question}
                        onChange={(e) => setQuestion(e.target.value)}
                        placeholder="Ask about this report…"
                        className="flex-1 rounded-full border border-card-border bg-card-bg px-4 py-2.5 text-sm text-foreground placeholder:text-muted/40 focus:border-primary focus:outline-none"
                        disabled={loading}
                    />
                    <button
                        type="submit"
                        disabled={loading || !question.trim()}
                        className="rounded-full bg-primary px-5 py-2.5 text-sm font-medium text-white transition-all hover:bg-primary-hover active:scale-95 disabled:opacity-40"
                    >
                        {loading ? (
                            <span className="flex gap-1">
                                <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                                <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                                <span className="pulse-dot h-1.5 w-1.5 rounded-full bg-white" />
                            </span>
                        ) : (
                            "Ask"
                        )}
                    </button>
                </form>
            ) : (
                <p className="text-center text-sm text-muted/60">
                    Question limit reached (10 per report)
                </p>
            )}

            {error && (
                <p className="mt-2 text-sm text-danger">{error}</p>
            )}
        </section>
    );
}
