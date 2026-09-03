from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch


def generate(path, inspection, fields, image_path=None):
    doc = SimpleDocTemplate(path, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("Product Label Compliance Inspection Report", styles["Title"]),
        Paragraph("Automated Package Declaration & Compliance Verification", styles["Subtitle"]),
        Spacer(1, 14),
    ]

    status_str = f"Inspection ID: #{inspection['id']} | Status: {inspection['overall_status']} | Compliance Score: {inspection['compliance_score']}%"
    story.append(Paragraph(status_str, styles["BodyText"]))

    if image_path:
        try:
            story += [Spacer(1, 8), Image(image_path, width=3 * inch, height=2 * inch, kind="proportional")]
        except Exception:
            pass

    rows = [["Label Field", "Detected Value", "Status", "Summary"]]
    for f in fields:
        field_label = f["field_name"].replace("_", " ").title()
        val = f.get("extracted_value") or "-"
        rows.append([field_label, val, f["status"], f["validation_message"]])

    t = Table(rows, colWidths=[1.5 * inch, 1.6 * inch, 0.9 * inch, 2.6 * inch], repeatRows=1)
    t.setStyle(TableStyle([
        ("GRID", (0, 0), (-1, -1), 0.4, colors.grey),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
    ]))
    story += [Spacer(1, 12), t, Spacer(1, 12)]

    story += [
        Paragraph("Extracted Label Text", styles["Heading2"]),
        Paragraph((inspection.get("cleaned_ocr_text") or "N/A").replace("&", "&amp;").replace("\n", "<br/>"), styles["BodyText"]),
        Spacer(1, 12),
        Paragraph("Disclaimer: This automated report is generated for label inspection assistance.", styles["Italic"]),
    ]

    doc.build(story)
