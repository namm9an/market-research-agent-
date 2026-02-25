"""PDF export service — generates professional PDF reports from research data."""

import logging
from io import BytesIO

from fpdf import FPDF

from app.models.schemas import ResearchJob

logger = logging.getLogger(__name__)


def sanitize_text(text: str) -> str:
    """Replace Unicode characters that fpdf2's built-in fonts can't render."""
    replacements = {
        '\u2014': '--',   # em dash
        '\u2013': '-',    # en dash
        '\u2018': "'",    # left single quote
        '\u2019': "'",    # right single quote
        '\u201c': '"',    # left double quote
        '\u201d': '"',    # right double quote
        '\u2026': '...',  # ellipsis
        '\u2022': '-',    # bullet
        '\u2011': '-',    # non-breaking hyphen
        '\u00a0': ' ',    # non-breaking space
        '\u2192': '->',   # right arrow
        '\u2190': '<-',   # left arrow
        '\u2265': '>=',   # greater or equal
        '\u2264': '<=',   # less or equal
        '\u00b7': '-',    # middle dot
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)
    # Strip any remaining non-latin-1 chars
    return text.encode('latin-1', errors='replace').decode('latin-1')


class ReportPDF(FPDF):
    """Custom PDF class with header/footer for research reports."""

    def __init__(self, company_name: str):
        super().__init__()
        self.company_name = company_name

    def header(self):
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(100, 100, 100)
        self.cell(0, 8, sanitize_text(f"Market Research Report -- {self.company_name}"), align="L")
        self.ln(4)
        self.set_draw_color(52, 152, 219)
        self.set_line_width(0.5)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(6)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def section_title(self, title: str):
        """Add a styled section heading."""
        self.set_font("Helvetica", "B", 14)
        self.set_text_color(44, 62, 80)
        self.ln(4)
        self.cell(0, 10, sanitize_text(title), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(52, 152, 219)
        self.set_line_width(0.3)
        self.line(10, self.get_y(), 80, self.get_y())
        self.ln(4)

    def sub_title(self, title: str):
        """Add a sub-heading."""
        self.set_font("Helvetica", "B", 11)
        self.set_text_color(52, 73, 94)
        self.cell(0, 8, sanitize_text(title), new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def body_text(self, text: str):
        """Add body paragraph."""
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 5.5, sanitize_text(text))
        self.ln(3)

    def bullet_point(self, text: str):
        """Add a bullet point."""
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 60, 60)
        self.cell(6, 5.5, "-")  # bullet char
        self.multi_cell(0, 5.5, sanitize_text(text))
        self.ln(1)

    def numbered_item(self, number: int, text: str):
        """Add a numbered item."""
        self.set_font("Helvetica", "B", 10)
        self.set_text_color(52, 152, 219)
        self.cell(8, 5.5, f"{number}.")
        self.set_font("Helvetica", "", 10)
        self.set_text_color(60, 60, 60)
        self.multi_cell(0, 5.5, sanitize_text(text))
        self.ln(1)

    def tag(self, label: str, color: tuple):
        """Add a small colored tag."""
        self.set_font("Helvetica", "B", 8)
        self.set_fill_color(*color)
        self.set_text_color(255, 255, 255)
        self.cell(
            self.get_string_width(sanitize_text(label)) + 6, 5, sanitize_text(label),
            fill=True, align="C",
        )
        self.cell(3, 5, "")  # spacer


def generate_pdf(job: ResearchJob) -> bytes:
    """Generate a professional PDF report from a completed research job.

    Args:
        job: Completed ResearchJob with report data.

    Returns:
        PDF file content as bytes.
    """
    r = job.report
    pdf = ReportPDF(company_name=job.query)
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)
    pdf.add_page()

    # --- Title ---
    pdf.set_font("Helvetica", "B", 22)
    pdf.set_text_color(44, 62, 80)
    pdf.cell(0, 12, sanitize_text(f"{job.query}"), new_x="LMARGIN", new_y="NEXT")
    pdf.set_font("Helvetica", "", 10)
    pdf.set_text_color(120, 120, 120)
    pdf.cell(0, 6, "Market Research Report", new_x="LMARGIN", new_y="NEXT")
    if job.completed_at:
        pdf.cell(
            0, 6,
            sanitize_text(
                f"Generated on {job.completed_at.strftime('%B %d, %Y at %H:%M UTC')} "
                f"| Duration: {job.duration_seconds}s | Sources: {len(r.sources)}"
            ),
            new_x="LMARGIN", new_y="NEXT",
        )
    pdf.ln(6)

    # --- Company Overview ---
    pdf.section_title("Company Overview")
    pdf.body_text(r.company_overview)

    # --- Financials ---
    fin = getattr(r, "financials", None)
    if fin:
        pdf.section_title("Core Business & Financials")
        pdf.body_text(f"Core Business: {fin.core_business_summary}")
        pdf.body_text(f"Market Cap: {fin.market_cap} | Funding Stage: {fin.funding_stage}")
        if fin.revenue_history:
            pdf.sub_title("Revenue History")
            for rev in fin.revenue_history:
                pdf.bullet_point(f"{rev.year}: {rev.amount}")
            pdf.ln(2)

    # --- Leader Discovery ---
    pdf.section_title("Leader Discovery")
    leaders = getattr(r, "leaders", []) or []
    if leaders:
        for leader in leaders:
            title_line = f"{leader.name} -- {leader.title}"
            if leader.function:
                title_line += f" ({leader.function})"
            title_line += f" [{leader.confidence}]"
            pdf.sub_title(title_line)
            if leader.evidence:
                pdf.body_text(leader.evidence)
            if leader.source_url:
                pdf.set_font("Helvetica", "", 8)
                pdf.set_text_color(52, 152, 219)
                pdf.cell(0, 4.5, leader.source_url[:100], new_x="LMARGIN", new_y="NEXT", link=leader.source_url)
                pdf.set_text_color(100, 100, 100)
                pdf.ln(2)
    else:
        pdf.body_text("No reliable leaders extracted from available context.")

    # --- ICP Fit ---
    pdf.section_title("ICP Fit (E2E Networks)")
    icp_fit = getattr(r, "icp_fit", None)
    if icp_fit:
        
        # Color coding for Fit Tier
        if icp_fit.fit_tier.lower() == "high":
            tier_color = SUCCESS_COLOR
        elif icp_fit.fit_tier.lower() == "medium":
            tier_color = WARNING_COLOR
        else:
            tier_color = DANGER_COLOR
            
        pdf.set_font(FONT_FAMILY, style="B", size=10)
        pdf.set_text_color(*tier_color)
        pdf.cell(0, 6, f"Fit Score: {icp_fit.fit_score}/100 | Tier: {icp_fit.fit_tier.upper()}", ln=True)
        pdf.set_text_color(*TEXT_COLOR)
        pdf.ln(2)
        
        if icp_fit.summary:
            pdf.body_text(icp_fit.summary)
            
        if icp_fit.reasons:
            pdf.sub_title("Fit Reasons")
            for reason in icp_fit.reasons:
                pdf.bullet_point(reason)

    # --- Deep Funding Intelligence ---
    fund = getattr(r, "funding_intelligence", None)
    if fund:
        pdf.section_title("Capital Allocation & GPU Spending Intent")
        
        # Color coding for Compute Lead Status
        if fund.e2e_compute_lead_status == "Hot":
            lead_color = DANGER_COLOR
        elif fund.e2e_compute_lead_status == "Warm":
            lead_color = WARNING_COLOR
        else:
            lead_color = (0, 150, 255) # Blue
            
        pdf.set_font(FONT_FAMILY, style="B", size=10)
        pdf.set_text_color(*lead_color)
        pdf.cell(0, 6, f"Compute Lead Status: {fund.e2e_compute_lead_status.upper()}", ln=True)
        pdf.set_text_color(*TEXT_COLOR)
        pdf.ln(2)
        
        pdf.body_text(fund.capital_allocation_purpose)
        
        pdf.set_font("Helvetica", "I", 9)
        pdf.set_text_color(100, 100, 100)
        pdf.multi_cell(0, 5, f"Evidence: {fund.compute_spending_evidence}")
        pdf.ln(2)
        pdf.set_text_color(*TEXT_COLOR)

        if fund.investor_types:
            pdf.sub_title("Investor Profile")
            pdf.body_text(", ".join(fund.investor_types))
            
        if fund.funding_timeline:
            pdf.sub_title("Execution Timeline")
            for round_data in fund.funding_timeline:
                inv_text = ", ".join(round_data.investors) if getattr(round_data, 'investors', None) else "Unknown"
                pdf.bullet_point(f"{round_data.date_or_round}: {round_data.amount} ({inv_text})")
            pdf.ln(2)

        if icp_fit.recommended_pitch_angles:
            pdf.sub_title("Recommended Pitch Angles")
            for angle in icp_fit.recommended_pitch_angles:
                pdf.bullet_point(angle)

        if icp_fit.concerns:
            pdf.sub_title("Concerns")
            for concern in icp_fit.concerns:
                pdf.bullet_point(concern)
    else:
        pdf.body_text("ICP fit assessment unavailable.")

    # --- Market Trends ---
    pdf.section_title("Market Trends")
    for trend in r.trends:
        relevance_colors = {
            "high": (231, 76, 60),
            "medium": (243, 156, 18),
            "low": (149, 165, 166),
        }
        pdf.sub_title(trend.title)
        pdf.tag(trend.relevance.upper(), relevance_colors.get(trend.relevance, (120, 120, 120)))
        pdf.ln(4)
        pdf.body_text(trend.description)

    # --- Competitive Landscape ---
    pdf.section_title("Competitive Landscape")
    pdf.body_text(r.competitive_landscape)

    # --- Key Findings ---
    pdf.section_title("Key Findings")
    for i, finding in enumerate(r.key_findings, 1):
        pdf.numbered_item(i, finding)

    # --- Sources ---
    pdf.section_title("Sources")
    pdf.set_font("Helvetica", "", 8)
    pdf.set_text_color(100, 100, 100)
    for source in r.sources:
        title = source.title[:80] + "..." if len(source.title) > 80 else source.title
        pdf.cell(0, 4.5, sanitize_text(f"- {title}"), new_x="LMARGIN", new_y="NEXT")
        pdf.set_text_color(52, 152, 219)
        pdf.cell(0, 4, f"  {source.url[:90]}", new_x="LMARGIN", new_y="NEXT", link=source.url)
        pdf.set_text_color(100, 100, 100)
        pdf.ln(1)

    # Generate bytes
    return pdf.output()
