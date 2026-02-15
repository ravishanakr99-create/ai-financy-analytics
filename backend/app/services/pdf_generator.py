"""Standardized consolidated PDF report generator."""

from io import BytesIO
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _p(text: object, style: ParagraphStyle) -> Paragraph:
    safe = escape(str(text if text is not None else ""))
    return Paragraph(safe, style)


def _styled_table(data: list[list], col_widths: list[float], body_style: ParagraphStyle) -> Table:
    wrapped = [data[0]]
    for row in data[1:]:
        wrapped.append([_p(cell, body_style) for cell in row])

    table = Table(wrapped, colWidths=col_widths, repeatRows=1)
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#16324f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, 0), 9),
                ("LEADING", (0, 0), (-1, 0), 11),
                ("BACKGROUND", (0, 1), (-1, -1), colors.HexColor("#f8fbff")),
                ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#9fb3c8")),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#eef4fb")]),
                ("VALIGN", (0, 1), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 6),
                ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    return table


def generate_report_pdf(report_data: dict) -> bytes:
    """Generate a standardized PDF from report data."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=0.7 * inch,
        leftMargin=0.7 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.7 * inch,
    )

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("ReportTitle", parent=styles["Heading1"], fontSize=18, textColor=colors.HexColor("#16324f"))
    h2 = ParagraphStyle("SectionHeading", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#16324f"), spaceAfter=6)
    table_body_style = ParagraphStyle(
        "TableBody",
        parent=styles["BodyText"],
        fontName="Helvetica",
        fontSize=8.5,
        leading=10.2,
        wordWrap="CJK",
    )

    story = []
    story.append(Paragraph("Consolidated Eligibility Report", title_style))
    story.append(Spacer(1, 6))
    story.append(Paragraph(f"<b>Report ID:</b> {report_data.get('report_id', 'N/A')}", styles["Normal"]))
    story.append(Paragraph(f"<b>Generated At:</b> {report_data.get('created_at', 'N/A')}", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Eligibility check result
    story.append(Paragraph("1. Eligibility Check Result", h2))
    eligibility_text = "Eligible" if report_data.get("eligibility") else "Not Eligible"
    story.append(Paragraph(f"<b>Status:</b> {eligibility_text}", styles["Normal"]))
    confidence = report_data.get("confidence_summary", {}).get("overall_confidence", "N/A")
    story.append(Paragraph(f"<b>Overall Confidence:</b> {confidence}", styles["Normal"]))
    story.append(Spacer(1, 8))

    decisions = report_data.get("decisions", [])
    decision_rows = [["Rule", "Pass/Fail", "Details"]]
    for item in decisions:
        decision_rows.append(
            [
                item.get("rule_name", ""),
                "Pass" if item.get("passed") else "Fail",
                item.get("message", ""),
            ]
        )
    story.append(_styled_table(decision_rows, [2.1 * inch, 1.0 * inch, 3.4 * inch], table_body_style))
    story.append(Spacer(1, 12))

    # Monthly salary breakdown table
    story.append(Paragraph("2. Monthly Salary Breakdown", h2))
    salary_rows = [["Month", "Employer", "Amount", "Confidence"]]
    salary_data = report_data.get("salary_breakdown", [])
    if salary_data:
        for row in salary_data:
            salary_rows.append(
                [
                    row.get("month", ""),
                    row.get("employer", ""),
                    f"{row.get('amount', 0):,.2f}",
                    f"{row.get('confidence', 0):.2f}",
                ]
            )
    else:
        salary_rows.append(["N/A", "N/A", "0.00", "0.00"])
    story.append(_styled_table(salary_rows, [1.2 * inch, 2.4 * inch, 1.4 * inch, 1.5 * inch], table_body_style))
    story.append(Spacer(1, 12))

    # Current obligations table
    story.append(Paragraph("3. Current Obligations", h2))
    obligation_rows = [["Lender", "Type", "Monthly", "Outstanding"]]
    obligations = report_data.get("obligations", [])
    if obligations:
        for row in obligations:
            obligation_rows.append(
                [
                    row.get("lender", ""),
                    row.get("obligation_type", ""),
                    f"{row.get('monthly_amount', 0):,.2f}",
                    f"{row.get('outstanding_amount', 0):,.2f}",
                ]
            )
    else:
        obligation_rows.append(["N/A", "N/A", "0.00", "0.00"])
    story.append(_styled_table(obligation_rows, [1.5 * inch, 2.1 * inch, 1.2 * inch, 1.7 * inch], table_body_style))
    story.append(Spacer(1, 12))

    # Pending documents list
    story.append(Paragraph("4. Pending Documents", h2))
    missing_docs = report_data.get("missing_documents", [])
    if missing_docs:
        for doc_name in missing_docs:
            story.append(Paragraph(f"- {doc_name}", styles["Normal"]))
    else:
        story.append(Paragraph("No pending documents.", styles["Normal"]))
    story.append(Spacer(1, 12))

    # Pending form details
    story.append(Paragraph("5. Pending Form Details", h2))
    pending_rows = [["Form Code", "Form Name", "Reason"]]
    pending_forms = report_data.get("pending_forms", [])
    if pending_forms:
        for form in pending_forms:
            pending_rows.append([form.get("form_code", ""), form.get("form_name", ""), form.get("reason", "")])
    else:
        pending_rows.append(["N/A", "No pending forms", "All mandatory forms complete"])
    story.append(_styled_table(pending_rows, [1.2 * inch, 2.0 * inch, 3.3 * inch], table_body_style))
    story.append(Spacer(1, 12))

    # Probable credit-team queries
    story.append(Paragraph("6. Probable Credit-Team Queries", h2))
    query_rows = [["Query", "Confidence", "Rationale"]]
    predicted_queries = report_data.get("predicted_queries", [])
    if predicted_queries:
        for query in predicted_queries:
            query_rows.append(
                [
                    query.get("query", ""),
                    f"{query.get('confidence', 0):.2f}",
                    query.get("rationale", ""),
                ]
            )
    else:
        query_rows.append(["No likely queries predicted", "0.00", "Insufficient patterns"])
    story.append(_styled_table(query_rows, [2.8 * inch, 1.0 * inch, 2.7 * inch], table_body_style))

    doc.build(story)
    return buffer.getvalue()
