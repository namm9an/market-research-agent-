import type { Source } from "@/lib/api";

export default function SourcesList({ sources }: { sources: Source[] }) {
    return (
        <section className="glass-card p-6">
            <h2 className="mb-4 text-lg font-semibold">
                Sources
                <span className="ml-2 text-sm font-normal text-muted">
                    ({sources.length})
                </span>
            </h2>
            <ul className="space-y-2">
                {sources.map((source, i) => (
                    <li key={i} className="flex items-start gap-2 text-sm">
                        <span className="mt-0.5 text-muted/40">{i + 1}.</span>
                        <div className="min-w-0">
                            <a
                                href={source.url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="font-medium text-primary transition-colors hover:text-primary-hover hover:underline"
                            >
                                {source.title || source.url}
                            </a>
                            <p className="truncate text-xs text-muted/40">{source.url}</p>
                        </div>
                    </li>
                ))}
            </ul>
        </section>
    );
}
