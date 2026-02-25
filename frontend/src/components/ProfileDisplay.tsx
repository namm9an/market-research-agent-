"use client";

import { useState } from "react";
import { Building2, Users, HandCoins, Blocks, ShieldCheck, MapPin } from "lucide-react";

export interface Firmographics {
    name?: string;
    year_founded?: string;
    hq_location?: string;
    employee_count?: string;
}

export interface Positioning {
    unique_value_prop?: string;
    customer_it_caters?: string;
    target_audience?: string;
}

export interface Financials {
    last_funding_round?: string;
    total_funding?: string;
    parts_of_funding?: string;
    investors?: string[];
}

export interface Executive {
    name: string;
    title: string;
}

export interface ProfileData {
    firmographics?: Firmographics;
    positioning?: Positioning;
    financials?: Financials;
    people_funded?: string[];
    executives?: Executive[];
    offerings?: string[];
    portfolio?: string[];
    trust_signals?: string[];
}

export interface ProfileDisplayProps {
    profile: ProfileData;
    rawText?: string;
}

export default function ProfileDisplay({ profile, rawText }: ProfileDisplayProps) {
    const [viewRaw, setViewRaw] = useState(false);

    if (!profile) return null;

    return (
        <div className="mt-4 space-y-6 slide-in text-left">
            {/* Header / Firmographics */}
            <div className="border border-card-border rounded-xl p-6 bg-card-bg/30 relative">
                <div className="flex justify-between items-start mb-4">
                    <div>
                        <h3 className="text-2xl font-bold text-foreground">
                            {profile.firmographics?.name || "Unknown Company"}
                        </h3>
                        <div className="flex items-center gap-4 mt-2 text-sm text-muted">
                            {profile.firmographics?.hq_location && (
                                <span className="flex items-center gap-1"><MapPin className="w-4 h-4" /> {profile.firmographics.hq_location}</span>
                            )}
                            {profile.firmographics?.year_founded && (
                                <span className="flex items-center gap-1"><Building2 className="w-4 h-4" /> Est. {profile.firmographics.year_founded}</span>
                            )}
                            {profile.firmographics?.employee_count && (
                                <span className="flex items-center gap-1"><Users className="w-4 h-4" /> {profile.firmographics.employee_count} Employees</span>
                            )}
                        </div>
                    </div>
                    {rawText && (
                        <button onClick={() => setViewRaw(!viewRaw)} className="text-xs text-primary underline absolute top-6 right-6">
                            {viewRaw ? "Hide Raw Data" : "View Raw Scrape"}
                        </button>
                    )}
                </div>

                {profile.positioning?.unique_value_prop && (
                    <p className="text-sm leading-relaxed text-muted/80 italic border-l-2 border-primary pl-4 my-4">
                        &quot;{profile.positioning.unique_value_prop}&quot;
                    </p>
                )}
                {(profile.positioning?.customer_it_caters || profile.positioning?.target_audience) && (
                    <div className="mt-3 text-sm">
                        <span className="font-semibold text-foreground mr-2">Target Customers / ICP:</span>
                        <span>{profile.positioning.customer_it_caters || profile.positioning.target_audience}</span>
                    </div>
                )}
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {/* Financials block */}
                <div className="border border-card-border rounded-xl p-5 bg-card-bg/10">
                    <h4 className="flex items-center gap-2 font-semibold mb-4 text-primary">
                        <HandCoins className="w-4 h-4" /> Financials
                    </h4>
                    <div className="space-y-3 text-sm">
                        <div className="flex justify-between border-b border-card-border pb-2">
                            <span className="text-muted">Funding Round</span>
                            <span className="font-medium text-foreground">{profile.financials?.last_funding_round || "-"}</span>
                        </div>
                        <div className="flex justify-between border-b border-card-border pb-2">
                            <span className="text-muted">Total Funding</span>
                            <span className="font-medium text-foreground">{profile.financials?.total_funding || "-"}</span>
                        </div>
                        {profile.financials?.parts_of_funding && (
                            <div className="flex justify-between border-b border-card-border pb-2">
                                <span className="text-muted">Funding Parts</span>
                                <span className="font-medium text-foreground">{profile.financials.parts_of_funding}</span>
                            </div>
                        )}
                        {profile.financials?.investors && profile.financials.investors.length > 0 && (
                            <div className="pt-2">
                                <span className="text-muted block mb-2">Key Investors:</span>
                                <div className="flex flex-wrap gap-2">
                                    {profile.financials.investors.map((inv: string, i: number) => (
                                        <span key={i} className="px-2 py-1 bg-white/5 rounded text-xs leading-tight">{inv}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                    </div>
                </div>

                {/* Executives block */}
                <div className="border border-card-border rounded-xl p-5 bg-card-bg/10">
                    <h4 className="flex items-center gap-2 font-semibold mb-4 text-primary">
                        <Users className="w-4 h-4" /> Leadership & People Funded
                    </h4>
                    {profile.people_funded && profile.people_funded.length > 0 && (
                        <div className="mb-4">
                            <span className="text-xs text-muted block mb-2">People Funded / Founders:</span>
                            <div className="flex flex-wrap gap-2">
                                {profile.people_funded.map((person: string, i: number) => (
                                    <span key={i} className="px-2 py-1 bg-white/5 rounded text-xs leading-tight">{person}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {profile.executives && profile.executives.length > 0 ? (
                        <div>
                            <span className="text-xs text-muted block mb-2">Executives:</span>
                            <ul className="space-y-3">
                                {profile.executives.map((exec: Executive, i: number) => (
                                    <li key={i} className="flex flex-col text-sm border-b border-card-border pb-2 last:border-0 last:pb-0">
                                        <span className="font-medium text-foreground">{exec.name}</span>
                                        <span className="text-xs text-muted/60">{exec.title}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    ) : (
                        !profile.people_funded?.length && <p className="text-xs text-muted">No specific leadership roles extracted.</p>
                    )}
                </div>

                {/* Offerings & Portfolio block */}
                <div className="border border-card-border rounded-xl p-5 bg-card-bg/10">
                    <h4 className="flex items-center gap-2 font-semibold mb-4 text-primary">
                        <Blocks className="w-4 h-4" /> Products & Portfolio
                    </h4>
                    {profile.offerings && profile.offerings.length > 0 && (
                        <div className="mb-4">
                            <span className="text-xs text-muted block mb-2 font-medium">Core Offerings:</span>
                            <ul className="list-disc list-inside space-y-2 text-sm text-foreground/80">
                                {profile.offerings.map((item: string, i: number) => (
                                    <li key={i}>{item}</li>
                                ))}
                            </ul>
                        </div>
                    )}

                    {profile.portfolio && profile.portfolio.length > 0 && (
                        <div>
                            <span className="text-xs text-muted block mb-2 font-medium">Portfolio / Subsidiaries:</span>
                            <div className="flex flex-wrap gap-2">
                                {profile.portfolio.map((item: string, i: number) => (
                                    <span key={i} className="px-2 py-1 bg-primary/10 text-primary border border-primary/20 rounded text-xs leading-tight">{item}</span>
                                ))}
                            </div>
                        </div>
                    )}

                    {(!profile.offerings?.length && !profile.portfolio?.length) && (
                        <p className="text-xs text-muted">No offerings or portfolio explicitly detailed.</p>
                    )}
                </div>

                {/* Trust Signals block */}
                <div className="border border-card-border rounded-xl p-5 bg-card-bg/10">
                    <h4 className="flex items-center gap-2 font-semibold mb-4 text-primary">
                        <ShieldCheck className="w-4 h-4" /> Trust Signals
                    </h4>
                    {profile.trust_signals && profile.trust_signals.length > 0 ? (
                        <div className="flex flex-wrap gap-2">
                            {profile.trust_signals.map((signal: string, i: number) => (
                                <span key={i} className="px-2.5 py-1.5 bg-success/10 text-success border border-success/20 rounded-md text-xs font-medium leading-tight">
                                    {signal}
                                </span>
                            ))}
                        </div>
                    ) : (
                        <p className="text-xs text-muted">No clear trust signals extracted.</p>
                    )}
                </div>
            </div>

            {/* Raw Text toggle section */}
            {viewRaw && rawText && (
                <div className="mt-8 border border-warning/30 rounded-lg p-5 bg-warning/5">
                    <h4 className="text-sm font-semibold text-warning mb-3">Raw Intercepted Document</h4>
                    <pre className="text-xs font-mono text-muted whitespace-pre-wrap overflow-y-auto max-h-64 p-3 bg-black/30 rounded border border-white/5">
                        {rawText}
                    </pre>
                </div>
            )}
        </div>
    );
}
