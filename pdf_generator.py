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

    # Dynamically assign the regional authority based on the EEZ
    eez_name = spill_data['eez'].upper()
    if "INDIA" in eez_name:
        authority = "INDIAN COAST GUARD"
    elif "OMAN" in eez_name:
        authority = "OMAN MARITIME SECURITY"
    elif "LIBYA" in eez_name:
        authority = "MEDITERRANEAN TASK FORCE"
    else:
        authority = f"{eez_name} MARITIME AUTHORITY"

    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontSize=16, leading=20,
        textColor=colors.HexColor("#0f172a"), spaceAfter=8
    )
    elements.append(Paragraph(f"{authority}: SAR INCIDENT DOSSIER", title_style))
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
        f"This discharge footprint has been correlated with the aforementioned vessel using Sentinel-1 SAR imagery. "
        f"Urgent aerial verification and interception by {authority} is requested."
    )
    elements.append(Paragraph(mandate, styles['Normal']))

    doc.build(elements)
    buffer.seek(0)
    return buffer