import type { CompanyFinancials } from "@/lib/api";

export default function FinancialsCard({ financials }: { financials: CompanyFinancials }) {
    if (!financials) {
        return null;
    }

    return (
        <section className="glass-card p-6 border-emerald-500/20 bg-gradient-to-br from-emerald-500/5 to-transparent">
            <h2 className="mb-4 text-lg font-semibold text-emerald-100 flex items-center gap-2">
                <svg className="w-5 h-5 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 6v12m-3-2.818.879.659c1.171.879 3.07.879 4.242 0 1.172-.879 1.172-2.303 0-3.182C13.536 12.219 12.768 12 12 12c-.725 0-1.45-.22-2.003-.659-1.106-.879-1.106-2.303 0-3.182s2.9-.879 4.006 0l.415.33M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Z" />
                </svg>
                Core Business & Financials
            </h2>

            {financials.core_business_summary && (
                <p className="mb-5 text-sm leading-relaxed text-emerald-100/80">
                    {financials.core_business_summary}
                </p>
            )}

            <div className="flex flex-wrap items-center gap-4 mb-6">
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 min-w-[140px]">
                    <p className="text-xs font-medium uppercase tracking-wider text-emerald-500/70 mb-1">Market Cap</p>
                    <p className="text-sm font-bold text-emerald-50">{financials.market_cap || "Unknown"}</p>
                </div>
                <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 min-w-[140px]">
                    <p className="text-xs font-medium uppercase tracking-wider text-emerald-500/70 mb-1">Funding Stage</p>
                    <p className="text-sm font-bold text-emerald-50">{financials.funding_stage || "Unknown"}</p>
                </div>
            </div>

            {financials.revenue_history && financials.revenue_history.length > 0 && (
                <div>
                    <h3 className="mb-3 text-xs font-semibold uppercase tracking-wider text-emerald-500/80">Revenue History</h3>
                    <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
                        {financials.revenue_history.map((rev, i) => (
                            <div key={i} className="flex items-center justify-between rounded-lg bg-black/20 px-3 py-2 border border-white/5">
                                <span className="text-xs font-medium text-muted">{rev.year}</span>
                                <span className="text-sm font-bold text-emerald-300">{rev.amount}</span>
                            </div>
                        ))}
                    </div>
                </div>
            )}
        </section>
    );
}
