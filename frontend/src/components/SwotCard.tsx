import type { SWOT } from "@/lib/api";

const QUADRANTS: {
    key: keyof SWOT;
    label: string;
    color: string;
    bgColor: string;
    borderColor: string;
}[] = [
        {
            key: "strengths",
            label: "Strengths",
            color: "text-emerald-400",
            bgColor: "bg-emerald-500/10",
            borderColor: "border-emerald-500/20",
        },
        {
            key: "weaknesses",
            label: "Weaknesses",
            color: "text-red-400",
            bgColor: "bg-red-500/10",
            borderColor: "border-red-500/20",
        },
        {
            key: "opportunities",
            label: "Opportunities",
            color: "text-blue-400",
            bgColor: "bg-blue-500/10",
            borderColor: "border-blue-500/20",
        },
        {
            key: "threats",
            label: "Threats",
            color: "text-amber-400",
            bgColor: "bg-amber-500/10",
            borderColor: "border-amber-500/20",
        },
    ];

export default function SwotCard({ swot }: { swot: SWOT }) {
    return (
        <section>
            <h2 className="mb-4 text-lg font-semibold">SWOT Analysis</h2>
            <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
                {QUADRANTS.map((q) => (
                    <div
                        key={q.key}
                        className={`rounded-2xl border p-5 ${q.bgColor} ${q.borderColor}`}
                    >
                        <h3 className={`mb-3 text-sm font-semibold uppercase tracking-wide ${q.color}`}>
                            {q.label}
                            <span className="ml-2 text-xs font-normal opacity-60">
                                {swot[q.key].length}
                            </span>
                        </h3>
                        <ul className="space-y-2">
                            {swot[q.key].map((item, i) => (
                                <li
                                    key={i}
                                    className="flex items-start gap-2 text-sm leading-relaxed text-foreground/80"
                                >
                                    <span className={`mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full ${q.color.replace("text-", "bg-")}`} />
                                    {item}
                                </li>
                            ))}
                        </ul>
                    </div>
                ))}
            </div>
        </section>
    );
}
