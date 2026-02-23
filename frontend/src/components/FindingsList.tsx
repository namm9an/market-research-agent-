export default function FindingsList({ findings }: { findings: string[] }) {
    return (
        <section className="glass-card p-6">
            <h2 className="mb-4 text-lg font-semibold">Key Findings</h2>
            <ol className="space-y-3">
                {findings.map((finding, i) => (
                    <li key={i} className="flex items-start gap-3 text-sm leading-relaxed">
                        <span className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-primary/15 text-xs font-bold text-primary">
                            {i + 1}
                        </span>
                        <span className="text-muted">{finding}</span>
                    </li>
                ))}
            </ol>
        </section>
    );
}
