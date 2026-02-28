"""PDF report helpers consumed by the Streamlit UI."""

from datetime import datetime
from fpdf import FPDF
from fpdf.enums import XPos, YPos
from typing import Any, Dict, List, Optional


def generate_pdf_report(report_data: Dict[str, Any], candidates: Optional[List[Dict[str, Any]]] = None) -> bytes:
    """Build a formatted recruitment PDF report from the session payload.

    Args:
        report_data: Full report payload returned by the API.
        candidates: Optional list of selected candidate summaries.

    Returns:
        The generated report as bytes, or an empty bytestring when creation failed.
    """
    pdf = FPDF(orientation="L")
    pdf.add_page()

    # HEADER
    pdf.set_fill_color(30, 41, 59)
    pdf.rect(0, 0, 297, 40, "F")
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", "B", 22)
    pdf.cell(w=0, h=20, text="JD Recruiting Assistance Report", border=0, align="C", new_x=XPos.LEFT, new_y=YPos.NEXT)

    pdf.set_font("Arial", "B", 14)
    jd_title = report_data.get("campaign_id", "CAMP_001")
    jd_name = report_data.get("job_title", "Recruitment Campaign")
    pdf.cell(w=0, h=10, text=f"{jd_name} | JD #{jd_title}", border=0, align="C", new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.ln(10)

    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", "B", 14)
    pdf.set_draw_color(30, 41, 59)
    pdf.cell(w=0, h=10, text="1. Session Insights", border=0, align="L", new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.line(10, pdf.get_y(), 60, pdf.get_y())
    pdf.ln(2)

    session_summary = report_data.get("session_summary", {})
    performance_metrics = report_data.get("performance_metrics", {})

    pdf.set_font("Arial", "", 11)
    pdf.cell(
        w=0,
        h=8,
        text=
        f"Candidates Sourced: {session_summary.get('total_candidates_sourced', 0)} | "
        f"Matches: {session_summary.get('high_quality_matches', 0)} | "
        f"Manual Reviews: {session_summary.get('manual_review_items', 0)}",
        border=0,
        align="L",
        fill=False,
        new_x=XPos.LEFT,
        new_y=YPos.NEXT,
    )
    pdf.cell(
        w=0,
        h=8,
        text=
        f"Audit Status: {session_summary.get('ethical_audit', {}).get('status', 'pending')} | "
        f"Duration: {performance_metrics.get('total_execution_time', 'N/A')}",
        border=0,
        align="L",
        fill=False,
        new_x=XPos.LEFT,
        new_y=YPos.NEXT,
    )
    pdf.ln(10)

    if candidates:
        pdf.set_font("Arial", "B", 14)
        pdf.cell(w=0, h=10, text="2. Qualitative Breakdown", border=0, align="L", new_x=XPos.LEFT, new_y=YPos.NEXT)
        pdf.line(10, pdf.get_y(), 60, pdf.get_y())
        pdf.ln(5)

        pdf.set_fill_color(241, 245, 249)
        pdf.set_font("Arial", "B", 10)
        pdf.cell(w=50, h=10, text="Name", border=1, align="L", fill=True)
        pdf.cell(w=60, h=10, text="Current Role", border=1, align="L", fill=True)
        pdf.cell(w=20, h=10, text="Score", border=1, align="C", fill=True)
        pdf.cell(w=100, h=10, text="Portfolio/URL", border=1, align="L", fill=True)
        pdf.cell(w=40, h=10, text="Flags", border=1, align="L", fill=True, new_x=XPos.LEFT, new_y=YPos.NEXT)

        pdf.set_font("Arial", "", 9)
        for i, cand in enumerate(candidates):
            current_y = pdf.get_y()
            is_declined = cand.get("score", 1) < 0.5
            if i < 3 and not is_declined:
                pdf.set_fill_color(200, 255, 200)
            elif is_declined:
                pdf.set_fill_color(255, 230, 230)
            else:
                pdf.set_fill_color(255, 255, 255)

            flag_text = "Data Deficient" if any("Data Deficient" in tag for tag in cand.get("tags", [])) else "-"

            candidate_score = cand.get("score")
            if candidate_score is None:
                candidate_score = cand.get("final_score", 0)
            profile_link = cand.get("profile_url") or cand.get("url") or "-"
            pdf.cell(
                w=50,
                h=10,
                text=str(cand.get("name", "-")),
                border=1,
                align="L",
                fill=True,
            )
            pdf.cell(
                w=60,
                h=10,
                text=str(cand.get("role", "-")),
                border=1,
                align="L",
                fill=True,
            )
            pdf.cell(
                w=20,
                h=10,
                text=f"{candidate_score * 100:.0f}%",
                border=1,
                align="C",
                fill=True,
            )
            pdf.cell(
                w=100,
                h=10,
                text=str(profile_link),
                border=1,
                align="L",
                fill=True,
            )
            pdf.cell(
                w=40,
                h=10,
                text=flag_text,
                border=1,
                align="L",
                fill=True,
                new_x=XPos.LEFT,
                new_y=YPos.NEXT,
            )

            if is_declined:
                pdf.set_draw_color(185, 28, 28)
                pdf.line(10, current_y + 5, 280, current_y + 5)
                pdf.set_draw_color(0, 0, 0)
        pdf.ln(5)

    pdf.set_font("Arial", "B", 14)
    pdf.cell(w=0, h=10, text="3. Final Recommendation", border=0, align="L", new_x=XPos.LEFT, new_y=YPos.NEXT)
    pdf.line(10, pdf.get_y(), 60, pdf.get_y())
    pdf.set_font("Arial", "I", 11)
    pdf.ln(2)
    pdf.multi_cell(0, 8, report_data.get("recommendation", "No recommendation available."))

    pdf.set_y(-25)
    pdf.set_font("Arial", "I", 8)
    pdf.set_text_color(100, 100, 100)
    report_date = datetime.now().strftime("%B %d, %Y")
    pdf.cell(0, 10, f"Analysis Date: {report_date} | Generated by Recruitment Assistant AI", align="C")

    output_data = pdf.output()
    if output_data is None:
        return b""
    return bytes(output_data)