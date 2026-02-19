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
