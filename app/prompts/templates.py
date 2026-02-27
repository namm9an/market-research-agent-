"""Prompt templates for the research agents."""

SWOT_PROMPT = """You are a senior market research analyst. Based on the following information about {company_name}, generate a detailed SWOT analysis.

INSTRUCTIONS:
- Each category (Strengths, Weaknesses, Opportunities, Threats) should have 3-5 bullet points
- Each bullet point should be specific and data-backed where possible
- Focus on actionable insights, not generic observations
- If information is insufficient for a category, note what additional research is needed

CONTEXT DATA:
{context}

OUTPUT FORMAT (respond in valid JSON only, no extra text):
{{
  "strengths": ["point 1", "point 2"],
  "weaknesses": ["point 1", "point 2"],
  "opportunities": ["point 1", "point 2"],
  "threats": ["point 1", "point 2"]
}}"""


TRENDS_PROMPT = """You are a market intelligence analyst. Based on the following web data about {company_name} and its industry, identify the top 5-7 current market trends.

INSTRUCTIONS:
- Each trend should have a clear title and 2-3 sentence description
- Rate each trend's relevance as high, medium, or low
- Focus on trends that are actionable for business strategy
- Include data points or evidence where available
- Don't fabricate statistics — only cite what's in the context

CONTEXT DATA:
{context}

OUTPUT FORMAT (respond in valid JSON only, no extra text):
[
  {{
    "title": "Trend title",
    "description": "2-3 sentence description with evidence",
    "relevance": "high"
  }}
]"""


LEADERS_PROMPT = """You are a B2B sales intelligence analyst. Extract current leadership contacts for {company_name} from the context.

INSTRUCTIONS:
- Return 8-12 leaders across ALL levels of the organization:
  * C-SUITE: CEO, CTO, CIO, CFO, COO, Founder, Co-Founder, Managing Director
  * VP LEVEL: VP Engineering, VP Sales, VP Product, VP Infrastructure, VP Cloud, VP Data
  * HEAD/DIRECTOR: Head of Infrastructure, Head of AI, Head of Engineering, Head of Sales, Director of Engineering, Director of Cloud
- TRUSTED SOURCES (use evidence from these only):
  * LinkedIn profile snippets (highest trust)
  * Official company website / about pages
  * Crunchbase, Tracxn, or PitchBook profiles
  * Major news outlets (TechCrunch, Bloomberg, Forbes)
- REJECT these sources — do NOT extract leaders that only appear in:
  * Random magazine articles, blogs, or press releases
  * Unverified directories or aggregator sites
- Do NOT invent people or guess titles
- If a person only appears in one unreliable source, do NOT include them
- If evidence is from a single source only, set confidence to "low"
- Leave source_url as empty string "", it will be auto-generated

CONTEXT DATA:
{context}

OUTPUT FORMAT (respond in valid JSON only, no extra text):
[
  {{
    "name": "Full Name",
    "title": "Role Title (e.g. Founder, CEO)",
    "function": "Technology | Engineering | Data/AI | Finance | Operations | Other",
    "source_url": "",
    "evidence": "Short snippet supporting this leadership mapping",
    "confidence": "high"
  }}
]"""


ICP_FIT_PROMPT = """You are an enterprise GTM analyst for E2E Networks.

E2E NETWORKS OFFERING (summary):
- GPU cloud infrastructure for AI training and inference
- High-performance compute and managed clusters
- Cost/performance positioning for AI workloads and model serving

Task: Evaluate how well {company_name} fits E2E Networks' ideal customer profile (ICP).

SCORING RUBRIC:
- 80-100: High fit (clear AI/GPU demand, scale, urgency, budget indicators)
- 50-79: Medium fit (some demand signals, partial readiness)
- 0-49: Low fit (weak relevance or missing signals)

INSTRUCTIONS:
- Use only context evidence
- Keep reasoning concise and practical for sales
- Include both positives and concerns

CONTEXT DATA:
{context}

OUTPUT FORMAT (respond in valid JSON only, no extra text):
{{
  "fit_score": 72,
  "fit_tier": "medium",
  "summary": "1-2 sentence fit summary",
  "reasons": ["reason 1", "reason 2", "reason 3"],
  "recommended_pitch_angles": ["angle 1", "angle 2", "angle 3"],
  "concerns": ["concern 1", "concern 2"]
}}"""


REPORT_PROMPT = """You are an expert business writer who transforms complex analysis into clear, professional reports. Compile a comprehensive market research report for {company_name}.

You have the following data:

SEARCH CONTEXT:
{context}

SWOT ANALYSIS:
{swot}

MARKET TRENDS:
{trends}

INSTRUCTIONS:
- Write a 2-3 paragraph company overview
- Summarize the competitive landscape in 1-2 paragraphs
- List 5-10 key findings as concise bullet points
- Be professional, clear, and actionable
- Don't fabricate data — only use what's provided

OUTPUT FORMAT (respond in valid JSON only, no extra text):
{{
  "company_overview": "2-3 paragraph overview",
  "competitive_landscape": "1-2 paragraph analysis",
  "key_findings": ["finding 1", "finding 2", "finding 3"]
}}"""

FINANCIALS_PROMPT = """You are a financial performance analyst. Extract the core business description, market cap/valuation, funding stage, and revenue history from the context about {company_name}.

INSTRUCTIONS:
- Core business summary must be a sharp, clear 1-2 sentence explanation of exactly how this company makes money.
- If market cap or valuation is private/unavailable, output "Private" or "Unknown".
- If funding stage is unknown, output "Unknown"
- Extract any available revenue numbers for recent years. Convert values to consistent string formats (e.g. "$50M", "$1.2B").
- Use ONLY evidence from the context data provided. Return an empty array for revenue if no data exists.

CONTEXT DATA:
{context}

OUTPUT FORMAT (respond in valid JSON only, no extra text):
{{
  "core_business_summary": "1-2 sentence description of what they sell and who they sell it to.",
  "market_cap": "$X.X Billion / Private",
  "funding_stage": "Public / Series C / Bootstrapped / Unknown",
  "revenue_history": [
    {{ "year": "2023", "amount": "$550M" }},
    {{ "year": "2022", "amount": "$400M" }}
  ]
}}"""

FUNDING_INTELLIGENCE_PROMPT = """You are an Enterprise Cloud & Tech Venture Analyst for E2E Networks (a GPU/Compute cloud provider).
Extrapolate the deep funding context and capital allocation strategy for {company_name}.

INSTRUCTIONS:
1. Identify the 'investor_types' (e.g., Tier 1 VC, Corporate Strategic, Private Equity, Debt). Look for names like "Accel", "Sequoia", "NVIDIA".
2. Build a 'funding_timeline' listing ALL major rounds (Seed, Series A, Series B, Series C, etc.), investor names, and amounts found in the context. DO NOT return an empty list if data exists.
3. Crucially, deduce the 'capital_allocation_purpose'. What are they doing with the money? Look closely for mentions of R&D, data centers, buying GPUs, training foundation models, or scaling infrastructure. Synthesize a 2-3 sentence summary.
4. Score them on 'e2e_compute_lead_status' ("Hot", "Warm", or "Cold"):
   - "Hot" if they explicitly mention building AI models, needing massive compute, expanding data centers, or buying GPUs.
   - "Warm" if they are a tech/SaaS company that likely has standard cloud infrastructure needs but no massive AI training explicitly stated.
   - "Cold" if the funding is purely for marketing, opening retail stores, or non-technical expansion.
5. Provide the 'compute_spending_evidence' (1-2 sentences summarizing why they got that score based on the text). If you see AI video generation or AI avatars, they are Hot or Warm.

CONTEXT DATA:
{context}

OUTPUT FORMAT (respond in valid JSON only, no extra text):
{{
  "investor_types": ["Tier 1 VC", "Strategic Partner"],
  "funding_timeline": [
    {{ "date_or_round": "Series B (2023)", "amount": "$50M", "investors": ["Sequoia", "NVIDIA"] }}
  ],
  "capital_allocation_purpose": "Expanding AI cluster and hiring researchers.",
  "e2e_compute_lead_status": "Hot",
  "compute_spending_evidence": "They specifically raised $50M to buy H100 GPUs and train new foundation models, indicating urgent massive compute needs."
}}"""

CRAWL_STRUCTURING_PROMPT = """You are a sales intelligence analyst. Extract actionable sales signals from this company's website content.

Your output helps sales reps prepare for cold calls in under 5 minutes. Be concise, tactical, and only use information present in the text.

Website Content:
{context}

OUTPUT FORMAT (Respond in valid JSON only, no extra text):
{{
  "positioning_snapshot": {{
    "company_name": "Company Name",
    "headline": "Their main headline or tagline from homepage",
    "value_proposition": "Their core value prop in one sentence",
    "primary_cta": "Their main call-to-action (e.g. Book Demo, Get Started, Contact Sales)",
    "target_audience": "Who they say they serve (e.g. enterprises, developers, startups)"
  }},
  "products_capabilities": {{
    "core_products": ["Product 1", "Product 2"],
    "technical_stack": ["GPU types", "APIs", "Infrastructure mentions"],
    "pricing_visible": "yes/no/freemium",
    "deployment_model": "SaaS / On-prem / Hybrid / Unknown"
  }},
  "pain_point_signals": {{
    "keywords_detected": ["scale", "cost", "latency", "security", "sovereign", "compliance"],
    "primary_narrative": "Their main pain point story in one sentence",
    "secondary_narrative": "Secondary pain angle if present, or null"
  }},
  "buying_signals": [
    {{
      "signal": "Description of a buying/expansion signal",
      "source": "Where on the site this was found (e.g. Careers page, Blog, Homepage)",
      "strength": "strong / moderate / weak"
    }}
  ],
  "objection_radar": {{
    "soc2_iso": "mentioned / not found",
    "sla_transparency": "mentioned / not found",
    "onprem_offering": "yes / no / not found",
    "enterprise_support": "mentioned / not found",
    "data_residency": "mentioned / not found"
  }},
  "contact_gtm": {{
    "sales_emails": ["sales@...", "enterprise@..."],
    "regions_served": ["India", "Global", "US"],
    "enterprise_vs_startup": "Both / Enterprise-focused / Startup-focused / Unknown",
    "demo_available": "yes / no / not found"
  }}
}}"""

