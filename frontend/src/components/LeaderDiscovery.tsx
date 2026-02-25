import type { LeaderProfile } from "@/lib/api";

const CONFIDENCE_CLASS: Record<string, string> = {
    high: "bg-emerald-500/15 text-emerald-300 border-emerald-500/20",
    medium: "bg-amber-500/15 text-amber-300 border-amber-500/20",
    low: "bg-red-500/15 text-red-300 border-red-500/20",
};

export default function LeaderDiscovery({ leaders }: { leaders: LeaderProfile[] }) {
    if (!leaders?.length) {
        return (
            <section className="glass-card p-6">
                <h2 className="mb-3 text-lg font-semibold">Leader Discovery</h2>
                <p className="text-sm text-muted">
                    No reliable leaders were extracted from the available sources.
                </p>
            </section>
        );
    }

    return (
        <section className="glass-card p-6">
            <h2 className="mb-4 text-lg font-semibold">Leader Discovery</h2>
            <div className="space-y-4">
                {leaders.map((leader, idx) => {
                    const confidence = (leader.confidence || "medium").toLowerCase();
                    const confidenceClass = CONFIDENCE_CLASS[confidence] || CONFIDENCE_CLASS.medium;

                    return (
                        <article key={`${leader.name}-${leader.title}-${idx}`} className="rounded-xl border border-white/10 bg-white/5 p-4">
                            <div className="flex flex-wrap items-center gap-2">
                                <h3 className="text-sm font-semibold text-foreground">{leader.name || "Unknown"}</h3>
                                <span className="text-sm text-muted">- {leader.title || "Role unavailable"}</span>
                                <span className={`rounded-full border px-2 py-0.5 text-[11px] font-semibold uppercase tracking-wide ${confidenceClass}`}>
                                    {confidence}
                                </span>
                            </div>
                            {leader.function && (
                                <p className="mt-2 text-xs uppercase tracking-wide text-primary/80">{leader.function}</p>
                            )}
                            {leader.evidence && (
                                <p className="mt-2 text-sm leading-relaxed text-muted">{leader.evidence}</p>
                            )}
                            {leader.source_url && (
                                <a
                                    href={leader.source_url}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="mt-2 inline-block text-xs text-primary underline-offset-2 hover:underline"
                                >
                                    Source
                                </a>
                            )}
                        </article>
                    );
                })}
            </div>
        </section>
    );
}
