"use client";

import { HandCoins, TrendingUp, Cpu, Calendar, CheckCircle2, AlertCircle, XCircle } from "lucide-react";
import type { FundingIntelligence, FundingMilestone } from "@/lib/api";

export default function FundingIntelligenceCard({ data }: { data: FundingIntelligence }) {
    if (!data) return null;

    // Determine badge styling based on lead status
    let badgeColor = "bg-card-bg/50 text-muted";
    let Icon = AlertCircle;

    if (data.e2e_compute_lead_status === "Hot") {
        badgeColor = "bg-danger/20 text-danger border-danger/30"; // Red/Hot
        Icon = Cpu;
    } else if (data.e2e_compute_lead_status === "Warm") {
        badgeColor = "bg-warning/20 text-warning border-warning/30"; // Orange/Warm
        Icon = CheckCircle2;
    } else if (data.e2e_compute_lead_status === "Cold") {
        badgeColor = "bg-primary/20 text-primary border-primary/30"; // Blue/Cold
        Icon = XCircle;
    }

    return (
        <section className="glass-card p-6 slide-in">
            <div className="flex justify-between items-start mb-6">
                <h2 className="text-xl font-bold flex items-center gap-2">
                    <HandCoins className="w-5 h-5 text-primary" />
                    Deep Funding Synthesis
                </h2>

                <div className={`flex items-center gap-1.5 px-3 py-1.5 rounded-full border text-xs font-bold ${badgeColor}`}>
                    <Icon className="w-3.5 h-3.5" />
                    <span>E2E GPU Fit: {data.e2e_compute_lead_status}</span>
                </div>
            </div>

            <div className="space-y-6">

                {/* Compute Evidence Block */}
                <div className="bg-background/40 p-4 rounded-lg border border-white/5">
                    <h3 className="text-sm font-semibold text-foreground mb-1 flex items-center gap-2">
                        <Cpu className="w-4 h-4 text-muted" /> Intent & Capital Allocation
                    </h3>
                    <p className="text-sm text-muted leading-relaxed">
                        <span className="font-medium text-foreground mr-2">Core Purpose:</span>
                        {data.capital_allocation_purpose}
                    </p>
                    <p className="text-sm text-foreground/80 mt-2 pl-4 border-l-2 border-primary/50 italic">
                        {data.compute_spending_evidence}
                    </p>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                    {/* Investor Types */}
                    <div>
                        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                            <TrendingUp className="w-4 h-4 text-muted" /> Investor Profile
                        </h3>
                        <div className="flex flex-wrap gap-2">
                            {data.investor_types && data.investor_types.length > 0 ? (
                                data.investor_types.map((type: string, i: number) => (
                                    <span key={i} className="px-2.5 py-1 text-xs rounded bg-white/5 border border-white/10 text-muted-foreground">
                                        {type}
                                    </span>
                                ))
                            ) : (
                                <span className="text-xs text-muted">Unknown</span>
                            )}
                        </div>
                    </div>

                    {/* Timeline */}
                    <div>
                        <h3 className="text-sm font-semibold text-foreground mb-3 flex items-center gap-2">
                            <Calendar className="w-4 h-4 text-muted" /> Execution Timeline
                        </h3>
                        <div className="space-y-3 relative border-l border-white/10 ml-2 pl-4">
                            {data.funding_timeline && data.funding_timeline.length > 0 ? (
                                data.funding_timeline.map((round: FundingMilestone, i: number) => (
                                    <div key={i} className="relative">
                                        <div className="absolute -left-[21px] top-1.5 w-2 h-2 rounded-full bg-primary ring-4 ring-card-bg"></div>
                                        <p className="text-sm font-semibold text-foreground">
                                            {round.date_or_round} <span className="text-primary ml-1">{round.amount}</span>
                                        </p>
                                        <p className="text-xs text-muted/70 mt-0.5">
                                            {round.investors?.join(", ")}
                                        </p>
                                    </div>
                                ))
                            ) : (
                                <p className="text-xs text-muted">Timeline unclear from public data.</p>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </section>
    );
}
