import type { ICPFitAssessment } from "@/lib/api";

function tierStyles(tier: string): string {
    const normalized = (tier || "medium").toLowerCase();
    if (normalized === "high") return "bg-emerald-500/15 text-emerald-300 border-emerald-500/20";
    if (normalized === "low") return "bg-red-500/15 text-red-300 border-red-500/20";
    return "bg-amber-500/15 text-amber-300 border-amber-500/20";
}

function SectionList({ title, items }: { title: string; items: string[] }) {
    if (!items?.length) return null;
    return (
        <div>
            <h3 className="mb-2 text-sm font-semibold uppercase tracking-wide text-primary/80">{title}</h3>
            <ul className="space-y-2">
                {items.map((item, idx) => (
                    <li key={`${title}-${idx}`} className="flex items-start gap-2 text-sm text-muted">
                        <span className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary" />
                        {item}
                    </li>
                ))}
            </ul>
        </div>
    );
}

export default function IcpFitCard({ icpFit }: { icpFit: ICPFitAssessment }) {
    if (!icpFit) {
        return (
            <section className="glass-card p-6">
                <h2 className="mb-3 text-lg font-semibold">ICP Fit (E2E Networks)</h2>
                <p className="text-sm text-muted">ICP fit assessment is unavailable.</p>
            </section>
        );
    }

    const tier = (icpFit.fit_tier || "medium").toLowerCase();
    const score = Number.isFinite(icpFit.fit_score) ? icpFit.fit_score : 0;

    return (
        <section className="glass-card p-6">
            <div className="mb-4 flex flex-wrap items-center gap-3">
                <h2 className="text-lg font-semibold">ICP Fit (E2E Networks)</h2>
                <span className={`rounded-full border px-2.5 py-1 text-xs font-semibold uppercase tracking-wide ${tierStyles(tier)}`}>
                    {tier} fit
                </span>
                <span className="rounded-full border border-primary/25 bg-primary/10 px-2.5 py-1 text-xs font-semibold text-primary">
                    Score: {score}/100
                </span>
            </div>

            {icpFit.summary && (
                <p className="mb-5 text-sm leading-relaxed text-muted">{icpFit.summary}</p>
            )}

            <div className="grid grid-cols-1 gap-5 md:grid-cols-3">
                <SectionList title="Why Fit" items={icpFit.reasons || []} />
                <SectionList title="Pitch Angles" items={icpFit.recommended_pitch_angles || []} />
                <SectionList title="Concerns" items={icpFit.concerns || []} />
            </div>
        </section>
    );
}
