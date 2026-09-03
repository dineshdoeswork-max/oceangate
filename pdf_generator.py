# PDF report ka kaam nahi hai sirf document banana — yeh ek field-ready action brief banana hai.
# "Jab samajh aati hai, tab decision fast hota hai, aur fast decision hi rescue ko possible banata hai."
# Chalo, report ko clean, sharp, and operationally useful banate hain.
import io
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

def generate_icg_report(spill_data: dict) -> io.BytesIO:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=16, leading=20,
        textColor=colors.HexColor("#0f172a"), spaceAfter=8
    )
    elements.append(Paragraph("INDIAN COAST GUARD: SAR INCIDENT DOSSIER", title_style))
    elements.append(Paragraph(f"SURVEILLANCE ID: {spill_data['name']}", styles['Normal']))
    elements.append(Spacer(1, 14))

    overview = [
        ["Detection Location", spill_data['location'], "Confidence", f"{spill_data['confidence']}%"],
        ["Platform", spill_data['satellite'], "Pass ID", spill_data['orbit_pass']],
        ["Jurisdiction", spill_data['eez'], "Timestamp", spill_data['date_display']],
        ["Surface Area", f"{spill_data['area_km2']} sq km", "Length", f"{spill_data['length_km']} km"]
    ]
    t1 = Table(overview, colWidths=[110, 160, 100, 170])
    t1.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f8fafc")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    elements.append(t1)
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("CORRELATED VESSEL DETAILS (AIS TRACK)", styles['Heading3']))
    v = spill_data['vessel']
    vessel_info = [
        ["Name", v['name'], "MMSI", v['mmsi']],
        ["Type", v['type'], "IMO", v['imo']],
        ["Flag State", v['flag'], "Length", f"{v['length_m']} m"]
    ]
    t2 = Table(vessel_info, colWidths=[110, 160, 100, 170])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#f1f5f9")),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#cbd5e1")),
        ('FONTNAME', (0,0), (0,-1), 'Helvetica-Bold'),
        ('FONTNAME', (2,0), (2,-1), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 9),
    ]))
    elements.append(t2)
    elements.append(Spacer(1, 16))

    elements.append(Paragraph("OPERATIONAL DIRECTIVE", styles['Heading3']))
    mandate = (
        "Under the National Oil Spill Disaster Contingency Plan (NOS-DCP), this discharge footprint "
        "has been correlated with the aforementioned vessel using Sentinel-1 SAR imagery and AIS vector extrapolation. "
        "Urgent aerial verification and interception by the nearest Coast Guard District Headquarters is requested."
    )
    elements.append(Paragraph(mandate, styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer