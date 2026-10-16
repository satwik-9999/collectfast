import io
import qrcode
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm

def generate_invoice_pdf(invoice, items, profile, client):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'InvoiceTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )
    
    subtitle_style = ParagraphStyle(
        'InvoiceSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=12
    )

    bold_label = ParagraphStyle(
        'BoldLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        textColor=colors.HexColor('#1E293B'),
    )

    normal_text = ParagraphStyle(
        'NormalText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        textColor=colors.HexColor('#334155'),
        leading=13
    )

    story = []

    # Header Table: Business Info Left, Invoice Details Right
    bus_text = f"""<b>{profile['business_name']}</b><br/>
{profile.get('address', '')}<br/>
<b>Phone:</b> {profile.get('phone', '')} | <b>Email:</b> {profile.get('email', '')}<br/>
<b>GSTIN:</b> {profile.get('gstin', 'N/A')}
"""
    inv_meta = f"""<font size="18" color="#2563EB"><b>TAX INVOICE</b></font><br/><br/>
<b>Invoice #:</b> {invoice['invoice_number']}<br/>
<b>Issue Date:</b> {invoice['issue_date']}<br/>
<b>Due Date:</b> {invoice['due_date']}<br/>
<b>Status:</b> <font color="{'#16A34A' if invoice['status']=='paid' else '#DC2626'}"><b>{invoice['status'].upper()}</b></font>
"""
    
    header_table = Table([
        [Paragraph(bus_text, normal_text), Paragraph(inv_meta, normal_text)]
    ], colWidths=[100 * mm, 80 * mm])
    header_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 10 * mm))

    # Bill To Box
    client_box = f"""<b>BILLED TO:</b><br/>
<font size="11"><b>{client['name']}</b></font> {f"({client['company']})" if client.get('company') else ''}<br/>
{client.get('address', '')}<br/>
<b>Phone:</b> {client.get('phone', '')} | <b>Email:</b> {client.get('email', '')}<br/>
<b>GSTIN:</b> {client.get('gstin', 'Unregistered')}
"""
    bill_table = Table([[Paragraph(client_box, normal_text)]], colWidths=[180 * mm])
    bill_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#E2E8F0')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 10),
        ('RIGHTPADDING', (0,0), (-1,-1), 10),
    ]))
    story.append(bill_table)
    story.append(Spacer(1, 8 * mm))

    # Items Table
    table_data = [
        [
            Paragraph("<b>#</b>", bold_label),
            Paragraph("<b>Description</b>", bold_label),
            Paragraph("<b>Qty</b>", bold_label),
            Paragraph("<b>Unit Price (₹)</b>", bold_label),
            Paragraph("<b>Amount (₹)</b>", bold_label)
        ]
    ]

    for idx, item in enumerate(items, 1):
        table_data.append([
            Paragraph(str(idx), normal_text),
            Paragraph(item['description'], normal_text),
            Paragraph(f"{item['quantity']:g}", normal_text),
            Paragraph(f"₹{item['unit_price']:,.2f}", normal_text),
            Paragraph(f"₹{item['total']:,.2f}", normal_text)
        ])

    item_table = Table(table_data, colWidths=[12 * mm, 88 * mm, 20 * mm, 30 * mm, 30 * mm])
    item_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F1F5F9')),
        ('ALIGN', (2,0), (-1,-1), 'RIGHT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#E2E8F0')),
    ]))
    story.append(item_table)
    story.append(Spacer(1, 6 * mm))

    # Totals + UPI QR Section
    # Generate UPI QR image
    upi_uri = f"upi://pay?pa={profile.get('upi_id', '')}&pn={profile.get('business_name', '')}&am={invoice['grand_total']:.2f}&cu=INR&tn=Invoice%20{invoice['invoice_number']}"
    qr = qrcode.QRCode(box_size=4, border=1)
    qr.add_data(upi_uri)
    qr.make(fit=True)
    qr_img = qr.make_image(fill_color="black", back_color="white")
    
    qr_buffer = io.BytesIO()
    qr_img.save(qr_buffer, format='PNG')
    qr_buffer.seek(0)
    reportlab_qr = Image(qr_buffer, width=32 * mm, height=32 * mm)

    payment_info = f"""<b>DIRECT INSTANT PAYMENT (UPI / BANK):</b><br/>
<b>UPI ID:</b> <font color="#2563EB"><b>{profile.get('upi_id', 'N/A')}</b></font><br/>
<b>Bank:</b> {profile.get('bank_name', 'N/A')}<br/>
<b>A/C No:</b> {profile.get('acc_number', 'N/A')}<br/>
<b>IFSC:</b> {profile.get('ifsc_code', 'N/A')}<br/>
<i>Scan QR on right with GPay, PhonePe, Paytm or BHIM</i>
"""

    summary_text = f"""<b>Subtotal:</b> ₹{invoice['subtotal']:,.2f}<br/>
<b>GST ({invoice['tax_rate']}%):</b> ₹{invoice['tax_amount']:,.2f}<br/>
{"<b>Discount:</b> -₹" + f"{invoice['discount_amount']:,.2f}<br/>" if invoice.get('discount_amount') else ''}
<font size="13" color="#0F172A"><b>Grand Total: ₹{invoice['grand_total']:,.2f}</b></font>
"""

    bottom_table = Table([
        [Paragraph(payment_info, normal_text), reportlab_qr, Paragraph(summary_text, normal_text)]
    ], colWidths=[70 * mm, 40 * mm, 70 * mm])
    bottom_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F8FAFC')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#CBD5E1')),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(bottom_table)

    if invoice.get('notes'):
        story.append(Spacer(1, 6 * mm))
        story.append(Paragraph(f"<b>Terms & Notes:</b> {invoice['notes']}", normal_text))

    doc.build(story)
    buffer.seek(0)
    return buffer.getvalue()
