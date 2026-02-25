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
- Return 5-10 likely decision-makers relevant for infra/cloud/GPU conversations
- Specifically look for Founders and Co-Founders, as well as executive and senior technical roles (CEO, CTO, CIO, VP Engineering, Head of Infra, Head of AI/Data)
- Use only evidence present in context
- Do not invent people or titles
- If evidence is weak, lower confidence

CONTEXT DATA:
{context}

OUTPUT FORMAT (respond in valid JSON only, no extra text):
[
  {{
    "name": "Full Name",
    "title": "Role Title (e.g. Founder, CEO)",
    "function": "Technology | Engineering | Data/AI | Finance | Operations | Other",
    "source_url": "https://...",
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
