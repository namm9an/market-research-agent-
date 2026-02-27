"use client";

import { useState } from "react";
import {
    Target, Package, Brain, TrendingUp, Shield, Phone,
    ChevronDown, ChevronUp, ExternalLink, Zap, AlertTriangle,
    CheckCircle2, XCircle, HelpCircle
} from "lucide-react";

// ── Type Definitions ────────────────────────────────────────

interface PositioningSnapshot {
    company_name?: string;
    headline?: string;
    value_proposition?: string;
    primary_cta?: string;
    target_audience?: string;
}

interface ProductsCapabilities {
    core_products?: string[];
    technical_stack?: string[];
    pricing_visible?: string;
    deployment_model?: string;
}

interface PainPointSignals {
    keywords_detected?: string[];
    primary_narrative?: string;
    secondary_narrative?: string | null;
}

interface BuyingSignal {
    signal: string;
    source: string;
    strength: string;
}

interface ObjectionRadar {
    soc2_iso?: string;
    sla_transparency?: string;
    onprem_offering?: string;
    enterprise_support?: string;
    data_residency?: string;
}

interface ContactGTM {
    sales_emails?: string[];
    regions_served?: string[];
    enterprise_vs_startup?: string;
    demo_available?: string;
}

export interface ProfileData {
    positioning_snapshot?: PositioningSnapshot;
    products_capabilities?: ProductsCapabilities;
    pain_point_signals?: PainPointSignals;
    buying_signals?: BuyingSignal[];
    objection_radar?: ObjectionRadar;
    contact_gtm?: ContactGTM;
    // Legacy fields (ignored but kept for backward compat)
    [key: string]: unknown;
}

interface ProfileDisplayProps {
    profile: ProfileData;
    rawText?: string;
}

// ── Helper Components ───────────────────────────────────────

function StatusIcon({ value }: { value?: string }) {
    if (!value) return <HelpCircle className="w-4 h-4 text-muted/40" />;
    const v = value.toLowerCase();
    if (v.includes("mentioned") || v === "yes" || v === "true")
        return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    if (v.includes("not found") || v === "no" || v === "false")
        return <XCircle className="w-4 h-4 text-red-400/60" />;
    return <HelpCircle className="w-4 h-4 text-yellow-400" />;
}

function StrengthBadge({ strength }: { strength: string }) {
    const s = (strength || "").toLowerCase();
    if (s.includes("strong"))
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30">Strong</span>;
    if (s.includes("moderate"))
        return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-yellow-500/20 text-yellow-400 border border-yellow-500/30">Moderate</span>;
    return <span className="px-2 py-0.5 rounded-full text-[10px] font-bold uppercase bg-white/10 text-muted border border-white/10">Weak</span>;
}

function SectionCard({ icon, title, children, accent = "primary" }: {
    icon: React.ReactNode;
    title: string;
    children: React.ReactNode;
    accent?: string;
}) {
    const accentMap: Record<string, string> = {
        primary: "text-primary border-primary/20",
        emerald: "text-emerald-400 border-emerald-500/20",
        amber: "text-amber-400 border-amber-500/20",
        rose: "text-rose-400 border-rose-500/20",
        cyan: "text-cyan-400 border-cyan-500/20",
        violet: "text-violet-400 border-violet-500/20",
    };
    const cls = accentMap[accent] || accentMap.primary;

    return (
        <div className={`rounded-xl border ${cls.split(" ").pop()} bg-white/[0.03] backdrop-blur-sm p-5`}>
            <h3 className={`flex items-center gap-2 text-sm font-semibold uppercase tracking-wider mb-4 ${cls.split(" ")[0]}`}>
                {icon}
                {title}
            </h3>
            {children}
        </div>
    );
}

// ── Main Component ──────────────────────────────────────────

export default function ProfileDisplay({ profile, rawText }: ProfileDisplayProps) {
    const [showRaw, setShowRaw] = useState(false);

    const pos = profile.positioning_snapshot;
    const prod = profile.products_capabilities;
    const pain = profile.pain_point_signals;
    const signals = profile.buying_signals || [];
    const objection = profile.objection_radar;
    const contact = profile.contact_gtm;

    return (
        <div className="space-y-5">

            {/* ── Positioning Snapshot ──────────────────────── */}
            {pos && (
                <SectionCard icon={<Target className="w-4 h-4" />} title="Positioning Snapshot" accent="primary">
                    <div className="space-y-3">
                        {pos.company_name && (
                            <h2 className="text-2xl font-bold text-foreground">{pos.company_name}</h2>
                        )}
                        {pos.headline && (
                            <blockquote className="border-l-2 border-primary/40 pl-3 text-base italic text-muted">
                                &ldquo;{pos.headline}&rdquo;
                            </blockquote>
                        )}
                        {pos.value_proposition && (
                            <p className="text-sm text-foreground/80">{pos.value_proposition}</p>
                        )}
                        <div className="flex flex-wrap gap-3 mt-2">
                            {pos.primary_cta && (
                                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-primary/10 border border-primary/20">
                                    <Zap className="w-3.5 h-3.5 text-primary" />
                                    <span className="text-xs font-semibold text-primary">CTA: {pos.primary_cta}</span>
                                </div>
                            )}
                            {pos.target_audience && (
                                <div className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10">
                                    <Target className="w-3.5 h-3.5 text-muted" />
                                    <span className="text-xs text-muted">ICP: {pos.target_audience}</span>
                                </div>
                            )}
                        </div>
                    </div>
                </SectionCard>
            )}

            {/* ── 2-Column Grid ──────────────────────────── */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">

                {/* ── Products & Capabilities ──────────────── */}
                {prod && (
                    <SectionCard icon={<Package className="w-4 h-4" />} title="Products & Capabilities" accent="cyan">
                        <div className="space-y-3">
                            {prod.core_products && prod.core_products.length > 0 && (
                                <div>
                                    <p className="text-[10px] uppercase tracking-wider text-muted/60 mb-1.5">Core Products</p>
                                    <ul className="space-y-1">
                                        {prod.core_products.map((p, i) => (
                                            <li key={i} className="text-sm text-foreground/80 flex items-start gap-2">
                                                <span className="text-cyan-400 mt-1">•</span> {p}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                            {prod.technical_stack && prod.technical_stack.length > 0 && (
                                <div>
                                    <p className="text-[10px] uppercase tracking-wider text-muted/60 mb-1.5">Tech Stack</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {prod.technical_stack.map((t, i) => (
                                            <span key={i} className="px-2 py-0.5 text-xs rounded-md bg-cyan-500/10 text-cyan-300 border border-cyan-500/20">{t}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            <div className="flex gap-4 pt-1">
                                {prod.pricing_visible && (
                                    <div className="text-xs">
                                        <span className="text-muted/60">Pricing: </span>
                                        <span className="text-foreground/80 font-medium">{prod.pricing_visible}</span>
                                    </div>
                                )}
                                {prod.deployment_model && (
                                    <div className="text-xs">
                                        <span className="text-muted/60">Deploy: </span>
                                        <span className="text-foreground/80 font-medium">{prod.deployment_model}</span>
                                    </div>
                                )}
                            </div>
                        </div>
                    </SectionCard>
                )}

                {/* ── Pain Point Signals ───────────────────── */}
                {pain && (
                    <SectionCard icon={<Brain className="w-4 h-4" />} title="Pain Point Signals" accent="amber">
                        <div className="space-y-3">
                            {pain.keywords_detected && pain.keywords_detected.length > 0 && (
                                <div>
                                    <p className="text-[10px] uppercase tracking-wider text-muted/60 mb-1.5">Keywords Detected</p>
                                    <div className="flex flex-wrap gap-1.5">
                                        {pain.keywords_detected.map((kw, i) => (
                                            <span key={i} className="px-2 py-0.5 text-xs rounded-md bg-amber-500/10 text-amber-300 border border-amber-500/20">{kw}</span>
                                        ))}
                                    </div>
                                </div>
                            )}
                            {pain.primary_narrative && (
                                <div>
                                    <p className="text-[10px] uppercase tracking-wider text-muted/60 mb-1">Primary Narrative</p>
                                    <p className="text-sm text-foreground/80 font-medium">{pain.primary_narrative}</p>
                                </div>
                            )}
                            {pain.secondary_narrative && (
                                <div>
                                    <p className="text-[10px] uppercase tracking-wider text-muted/60 mb-1">Secondary Narrative</p>
                                    <p className="text-sm text-foreground/70">{pain.secondary_narrative}</p>
                                </div>
                            )}
                        </div>
                    </SectionCard>
                )}

                {/* ── Buying Signals ───────────────────────── */}
                {signals.length > 0 && (
                    <SectionCard icon={<TrendingUp className="w-4 h-4" />} title="Buying Signals" accent="emerald">
                        <div className="space-y-2.5">
                            {signals.map((sig, i) => (
                                <div key={i} className="flex items-start gap-3 p-2.5 rounded-lg bg-white/[0.02] border border-white/5">
                                    <AlertTriangle className="w-4 h-4 text-emerald-400 mt-0.5 shrink-0" />
                                    <div className="flex-1 min-w-0">
                                        <p className="text-sm text-foreground/80">{sig.signal}</p>
                                        <div className="flex items-center gap-2 mt-1">
                                            <span className="text-[10px] text-muted/50">{sig.source}</span>
                                            <StrengthBadge strength={sig.strength} />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </SectionCard>
                )}

                {/* ── Objection Radar ──────────────────────── */}
                {objection && (
                    <SectionCard icon={<Shield className="w-4 h-4" />} title="Objection Radar" accent="rose">
                        <div className="space-y-2">
                            {[
                                { label: "SOC2 / ISO", value: objection.soc2_iso },
                                { label: "SLA Transparency", value: objection.sla_transparency },
                                { label: "On-Prem Offering", value: objection.onprem_offering },
                                { label: "Enterprise Support", value: objection.enterprise_support },
                                { label: "Data Residency", value: objection.data_residency },
                            ].map((item, i) => (
                                <div key={i} className="flex items-center justify-between py-1.5 border-b border-white/5 last:border-0">
                                    <span className="text-sm text-foreground/70">{item.label}</span>
                                    <div className="flex items-center gap-1.5">
                                        <span className="text-xs text-muted/60 capitalize">{item.value || "unknown"}</span>
                                        <StatusIcon value={item.value} />
                                    </div>
                                </div>
                            ))}
                        </div>
                    </SectionCard>
                )}
            </div>

            {/* ── Contact & GTM (Full Width) ──────────────── */}
            {contact && (
                <SectionCard icon={<Phone className="w-4 h-4" />} title="Contact & GTM" accent="violet">
                    <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
                        {contact.sales_emails && contact.sales_emails.length > 0 && contact.sales_emails[0] !== "" && (
                            <div>
                                <p className="text-[10px] uppercase tracking-wider text-muted/60 mb-1">Sales Emails</p>
                                {contact.sales_emails.map((email, i) => (
                                    <a key={i} href={`mailto:${email}`} className="block text-sm text-violet-400 hover:text-violet-300 transition-colors truncate">
                                        {email}
                                    </a>
                                ))}
                            </div>
                        )}
                        {contact.regions_served && contact.regions_served.length > 0 && (
                            <div>
                                <p className="text-[10px] uppercase tracking-wider text-muted/60 mb-1">Regions</p>
                                <div className="flex flex-wrap gap-1">
                                    {contact.regions_served.map((r, i) => (
                                        <span key={i} className="px-2 py-0.5 text-xs rounded-md bg-violet-500/10 text-violet-300 border border-violet-500/20">{r}</span>
                                    ))}
                                </div>
                            </div>
                        )}
                        {contact.enterprise_vs_startup && (
                            <div>
                                <p className="text-[10px] uppercase tracking-wider text-muted/60 mb-1">Segment Focus</p>
                                <p className="text-sm text-foreground/80">{contact.enterprise_vs_startup}</p>
                            </div>
                        )}
                        {contact.demo_available && (
                            <div>
                                <p className="text-[10px] uppercase tracking-wider text-muted/60 mb-1">Demo Available</p>
                                <div className="flex items-center gap-1.5">
                                    <StatusIcon value={contact.demo_available} />
                                    <span className="text-sm text-foreground/80 capitalize">{contact.demo_available}</span>
                                </div>
                            </div>
                        )}
                    </div>
                </SectionCard>
            )}

            {/* ── Raw Scrape Toggle ──────────────────────── */}
            {rawText && (
                <div className="mt-2">
                    <button
                        onClick={() => setShowRaw(!showRaw)}
                        className="flex items-center gap-1.5 text-xs text-muted/60 hover:text-muted transition-colors"
                    >
                        <ExternalLink className="w-3 h-3" />
                        {showRaw ? "Hide" : "View"} Raw Scrape
                        {showRaw ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
                    </button>
                    {showRaw && (
                        <pre className="mt-2 p-4 rounded-lg bg-black/40 border border-white/10 text-xs text-muted/70 overflow-x-auto max-h-80 custom-scrollbar whitespace-pre-wrap">
                            {rawText}
                        </pre>
                    )}
                </div>
            )}
        </div>
    );
}
