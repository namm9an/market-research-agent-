import type { Trend } from "@/lib/api";

const RELEVANCE_STYLES: Record<string, string> = {
    high: "bg-red-500/15 text-red-400 border-red-500/20",
    medium: "bg-amber-500/15 text-amber-400 border-amber-500/20",
    low: "bg-zinc-500/15 text-zinc-400 border-zinc-500/20",
};

export default function TrendsList({ trends }: { trends: Trend[] }) {
    return (
        <section>
            <h2 className="mb-4 text-lg font-semibold">Market Trends</h2>
            <div className="flex flex-col gap-3">
                {trends.map((trend, i) => (
                    <div key={i} className="glass-card p-5">
                        <div className="mb-2 flex items-start justify-between gap-3">
                            <h3 className="text-sm font-semibold text-foreground">
                                {trend.title}
                            </h3>
                            <span
                                className={`shrink-0 rounded-full border px-2.5 py-0.5 text-xs font-medium uppercase tracking-wide ${RELEVANCE_STYLES[trend.relevance] || RELEVANCE_STYLES.low
                                    }`}
                            >
                                {trend.relevance}
                            </span>
                        </div>
                        <p className="text-sm leading-relaxed text-muted">
                            {trend.description}
                        </p>
                    </div>
                ))}
            </div>
        </section>
    );
}
