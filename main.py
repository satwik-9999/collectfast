import os
import io
import uuid
import urllib.parse
from datetime import datetime, date, timedelta
from typing import Optional, List

from fastapi import FastAPI, Request, Form, Depends, HTTPException, Response
from fastapi.responses import HTMLResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import qrcode

from database import init_db, get_connection
from pdf_generator import generate_invoice_pdf

app = FastAPI(title="CollectFast - UPI & WhatsApp Invoicing Engine")

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates")
STATIC_DIR = os.path.join(BASE_DIR, "static")

templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Initialize database immediately
init_db()

@app.on_event("startup")
def startup():
    init_db()

def get_profile():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM profile WHERE id = 1")
    row = c.fetchone()
    conn.close()
    return dict(row) if row else {}

# Helper to format Indian currency
def format_inr(val):
    try:
        val = float(val)
        return f"{val:,.2f}"
    except:
        return "0.00"

templates.env.filters["inr"] = format_inr

# ----------------- ROUTES ----------------- #

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    conn = get_connection()
    c = conn.cursor()
    profile = get_profile()

    # Calculate metrics
    c.execute("SELECT SUM(grand_total) FROM invoices WHERE status = 'paid'")
    total_paid = c.fetchone()[0] or 0.0

    c.execute("SELECT SUM(grand_total) FROM invoices WHERE status = 'pending'")
    total_pending = c.fetchone()[0] or 0.0

    c.execute("SELECT SUM(grand_total) FROM invoices WHERE status = 'overdue'")
    total_overdue = c.fetchone()[0] or 0.0

    total_billed = total_paid + total_pending + total_overdue
    collection_rate = (total_paid / total_billed * 100) if total_billed > 0 else 100.0

    # Recent invoices
    c.execute("""
    SELECT i.*, cl.name as client_name, cl.company as client_company, cl.phone as client_phone
    FROM invoices i
    JOIN clients cl ON i.client_id = cl.id
    ORDER BY i.id DESC LIMIT 6
    """)
    recent_invoices = [dict(row) for row in c.fetchall()]

    # Overdue list needing WhatsApp reminders
    c.execute("""
    SELECT i.*, cl.name as client_name, cl.phone as client_phone
    FROM invoices i
    JOIN clients cl ON i.client_id = cl.id
    WHERE i.status IN ('overdue', 'pending')
    ORDER BY i.due_date ASC LIMIT 5
    """)
    attention_invoices = [dict(row) for row in c.fetchall()]

    conn.close()

    return templates.TemplateResponse(request, "dashboard.html", {
        "profile": profile,
        "total_paid": total_paid,
        "total_pending": total_pending,
        "total_overdue": total_overdue,
        "collection_rate": round(collection_rate, 1),
        "recent_invoices": recent_invoices,
        "attention_invoices": attention_invoices
    })

@app.get("/invoices", response_class=HTMLResponse)
async def list_invoices(request: Request, status: Optional[str] = None):
    conn = get_connection()
    c = conn.cursor()
    profile = get_profile()

    query = """
    SELECT i.*, cl.name as client_name, cl.company as client_company, cl.phone as client_phone
    FROM invoices i
    JOIN clients cl ON i.client_id = cl.id
    """
    params = []
    if status and status != 'all':
        query += " WHERE i.status = ?"
        params.append(status)

    query += " ORDER BY i.id DESC"
    c.execute(query, params)
    invoices = [dict(row) for row in c.fetchall()]
    conn.close()

    return templates.TemplateResponse(request, "invoices.html", {
        "profile": profile,
        "invoices": invoices,
        "current_status": status or 'all'
    })

@app.get("/invoices/new", response_class=HTMLResponse)
async def new_invoice_page(request: Request):
    conn = get_connection()
    c = conn.cursor()
    profile = get_profile()

    c.execute("SELECT id, name, company, phone FROM clients ORDER BY name ASC")
    clients = [dict(row) for row in c.fetchall()]

    # Next invoice number
    c.execute("SELECT COUNT(*) FROM invoices")
    count = c.fetchone()[0] + 1
    next_inv_num = f"INV-{datetime.now().year}-{count:03d}"

    conn.close()
    today_str = date.today().strftime("%Y-%m-%d")
    due_str = (date.today() + timedelta(days=7)).strftime("%Y-%m-%d")

    return templates.TemplateResponse(request, "invoice_create.html", {
        "profile": profile,
        "clients": clients,
        "next_inv_num": next_inv_num,
        "today_str": today_str,
        "due_str": due_str
    })

@app.post("/invoices/create")
async def create_invoice(
    request: Request,
    invoice_number: str = Form(...),
    client_id: Optional[str] = Form(None),
    new_client_name: Optional[str] = Form(None),
    new_client_phone: Optional[str] = Form(None),
    new_client_company: Optional[str] = Form(None),
    new_client_email: Optional[str] = Form(None),
    issue_date: str = Form(...),
    due_date: str = Form(...),
    tax_rate: float = Form(18.0),
    discount_amount: float = Form(0.0),
    notes: Optional[str] = Form(""),
    # Items
    item_desc: List[str] = Form(...),
    item_qty: List[float] = Form(...),
    item_price: List[float] = Form(...)
):
    conn = get_connection()
    c = conn.cursor()

    # Check or create client
    target_client_id = None
    if client_id and client_id != "new":
        target_client_id = int(client_id)
    else:
        if not new_client_name or not new_client_phone:
            raise HTTPException(status_code=400, detail="Client name & phone are required")
        c.execute("""
        INSERT INTO clients (name, company, phone, email)
        VALUES (?, ?, ?, ?)
        """, (new_client_name, new_client_company or "", new_client_phone, new_client_email or ""))
        target_client_id = c.lastrowid

    # Compute calculations
    subtotal = 0.0
    items_to_save = []
    for desc, qty, price in zip(item_desc, item_qty, item_price):
        if desc.strip():
            tot = float(qty) * float(price)
            subtotal += tot
            items_to_save.append((desc.strip(), float(qty), float(price), tot))

    tax_amount = round(subtotal * (float(tax_rate) / 100.0), 2)
    grand_total = round(subtotal + tax_amount - float(discount_amount), 2)
    token = str(uuid.uuid4())[:12]

    # Save invoice
    c.execute("""
    INSERT INTO invoices (invoice_number, client_id, issue_date, due_date, status, subtotal, tax_rate, tax_amount, discount_amount, grand_total, notes, token)
    VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?, ?, ?)
    """, (invoice_number, target_client_id, issue_date, due_date, subtotal, tax_rate, tax_amount, discount_amount, grand_total, notes, token))
    invoice_id = c.lastrowid

    for item in items_to_save:
        c.execute("""
        INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total)
        VALUES (?, ?, ?, ?, ?)
        """, (invoice_id, item[0], item[1], item[2], item[3]))

    # Increment invoice counter in profile
    c.execute("UPDATE profile SET invoices_count = invoices_count + 1 WHERE id = 1")
    conn.commit()
    conn.close()

    return RedirectResponse(f"/invoices/{invoice_id}?created=true", status_code=303)

@app.get("/invoices/{invoice_id}", response_class=HTMLResponse)
async def view_invoice(request: Request, invoice_id: int):
    conn = get_connection()
    c = conn.cursor()
    profile = get_profile()

    c.execute("""
    SELECT i.*, cl.name as client_name, cl.company as client_company, cl.phone as client_phone, cl.email as client_email, cl.address as client_address, cl.gstin as client_gstin
    FROM invoices i
    JOIN clients cl ON i.client_id = cl.id
    WHERE i.id = ?
    """, (invoice_id,))
    inv_row = c.fetchone()
    if not inv_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found")
    
    invoice = dict(inv_row)

    c.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    items = [dict(row) for row in c.fetchall()]
    conn.close()

    # Pre-generate WhatsApp message links
    public_url = f"{request.base_url}pay/{invoice['token']}"
    
    # 1. Gentle Reminder
    msg_gentle = f"Hello {invoice['client_name']}, hope you are well. Here is invoice {invoice['invoice_number']} for ₹{invoice['grand_total']:,.2f} due on {invoice['due_date']}. You can pay directly via UPI / Card here: {public_url} . Thank you! - {profile['business_name']}"
    wa_gentle = f"https://wa.me/{invoice['client_phone'].replace('+', '').replace(' ', '')}?text={urllib.parse.quote(msg_gentle)}"

    # 2. Due Today / Urgent Reminder
    msg_urgent = f"Hi {invoice['client_name']}, gentle reminder that invoice {invoice['invoice_number']} for ₹{invoice['grand_total']:,.2f} is pending. Instant UPI link: {public_url} . Please clear at your earliest. Thanks! - {profile['business_name']}"
    wa_urgent = f"https://wa.me/{invoice['client_phone'].replace('+', '').replace(' ', '')}?text={urllib.parse.quote(msg_urgent)}"

    # 3. Overdue Notice
    msg_overdue = f"Dear {invoice['client_name']}, invoice {invoice['invoice_number']} (₹{invoice['grand_total']:,.2f}) is now overdue. Kindly tap here to clear via Google Pay / PhonePe: {public_url} . Reach out if you have any questions."
    wa_overdue = f"https://wa.me/{invoice['client_phone'].replace('+', '').replace(' ', '')}?text={urllib.parse.quote(msg_overdue)}"

    return templates.TemplateResponse(request, "invoice_view.html", {
        "profile": profile,
        "invoice": invoice,
        "items": items,
        "public_url": public_url,
        "wa_gentle": wa_gentle,
        "wa_urgent": wa_urgent,
        "wa_overdue": wa_overdue
    })

@app.post("/invoices/{invoice_id}/status")
async def toggle_invoice_status(invoice_id: int, status: str = Form(...)):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE invoices SET status = ? WHERE id = ?", (status, invoice_id))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/invoices/{invoice_id}", status_code=303)

@app.get("/invoices/{invoice_id}/pdf")
async def download_pdf(invoice_id: int):
    conn = get_connection()
    c = conn.cursor()
    profile = get_profile()

    c.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,))
    invoice = dict(c.fetchone())
    c.execute("SELECT * FROM clients WHERE id = ?", (invoice['client_id'],))
    client = dict(c.fetchone())
    c.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice_id,))
    items = [dict(row) for row in c.fetchall()]
    conn.close()

    pdf_bytes = generate_invoice_pdf(invoice, items, profile, client)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={invoice['invoice_number']}.pdf"}
    )

# ----------------- PUBLIC CLIENT PAYMENT PORTAL ----------------- #

@app.get("/pay/{token}", response_class=HTMLResponse)
async def public_payment_page(request: Request, token: str):
    conn = get_connection()
    c = conn.cursor()
    profile = get_profile()

    c.execute("""
    SELECT i.*, cl.name as client_name, cl.company as client_company, cl.phone as client_phone, cl.email as client_email, cl.address as client_address
    FROM invoices i
    JOIN clients cl ON i.client_id = cl.id
    WHERE i.token = ?
    """, (token,))
    inv_row = c.fetchone()
    if not inv_row:
        conn.close()
        raise HTTPException(status_code=404, detail="Invoice not found or link has expired")

    invoice = dict(inv_row)
    c.execute("SELECT * FROM invoice_items WHERE invoice_id = ?", (invoice['id'],))
    items = [dict(row) for row in c.fetchall()]
    conn.close()

    # Standard Indian UPI Payment URI
    upi_uri = f"upi://pay?pa={profile.get('upi_id', '')}&pn={urllib.parse.quote(profile.get('business_name', ''))}&am={invoice['grand_total']:.2f}&cu=INR&tn=Invoice%20{invoice['invoice_number']}"

    return templates.TemplateResponse(request, "public_invoice.html", {
        "profile": profile,
        "invoice": invoice,
        "items": items,
        "upi_uri": upi_uri
    })

@app.get("/pay/{token}/qr")
async def generate_qr_image(token: str):
    conn = get_connection()
    c = conn.cursor()
    profile = get_profile()

    c.execute("SELECT invoice_number, grand_total FROM invoices WHERE token = ?", (token,))
    row = c.fetchone()
    conn.close()

    if not row:
        raise HTTPException(status_code=404, detail="Invoice not found")

    invoice_number, grand_total = row
    upi_uri = f"upi://pay?pa={profile.get('upi_id', '')}&pn={urllib.parse.quote(profile.get('business_name', ''))}&am={grand_total:.2f}&cu=INR&tn=Invoice%20{invoice_number}"

    qr = qrcode.QRCode(box_size=6, border=2)
    qr.add_data(upi_uri)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#0F172A", back_color="white")

    img_io = io.BytesIO()
    img.save(img_io, 'PNG')
    img_io.seek(0)
    return Response(content=img_io.getvalue(), media_type="image/png")

@app.post("/pay/{token}/mark-paid")
async def client_mark_paid(token: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE invoices SET status = 'paid' WHERE token = ?", (token,))
    conn.commit()
    conn.close()
    return RedirectResponse(f"/pay/{token}?paid_success=true", status_code=303)

# ----------------- CLIENT KHATA / DIRECTORY ----------------- #

@app.get("/clients", response_class=HTMLResponse)
async def list_clients(request: Request):
    conn = get_connection()
    c = conn.cursor()
    profile = get_profile()

    c.execute("""
    SELECT 
        cl.*,
        COUNT(i.id) as total_invoices,
        COALESCE(SUM(i.grand_total), 0) as total_billed,
        COALESCE(SUM(CASE WHEN i.status = 'paid' THEN i.grand_total ELSE 0 END), 0) as total_paid,
        COALESCE(SUM(CASE WHEN i.status IN ('pending', 'overdue') THEN i.grand_total ELSE 0 END), 0) as total_outstanding
    FROM clients cl
    LEFT JOIN invoices i ON cl.id = i.client_id
    GROUP BY cl.id
    ORDER BY total_outstanding DESC
    """)
    clients = [dict(row) for row in c.fetchall()]
    conn.close()

    return templates.TemplateResponse(request, "clients.html", {
        "profile": profile,
        "clients": clients
    })

@app.post("/clients/new")
async def add_client(
    name: str = Form(...),
    company: Optional[str] = Form(""),
    phone: str = Form(...),
    email: Optional[str] = Form(""),
    gstin: Optional[str] = Form(""),
    address: Optional[str] = Form("")
):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    INSERT INTO clients (name, company, phone, email, gstin, address)
    VALUES (?, ?, ?, ?, ?, ?)
    """, (name, company, phone, email, gstin, address))
    conn.commit()
    conn.close()
    return RedirectResponse("/clients", status_code=303)

# ----------------- MONETIZATION & PRICING ----------------- #

@app.get("/pricing", response_class=HTMLResponse)
async def pricing_page(request: Request):
    profile = get_profile()
    return templates.TemplateResponse(request, "pricing.html", {
        "profile": profile
    })

@app.post("/pricing/upgrade")
async def upgrade_plan(plan: str = Form(...)):
    conn = get_connection()
    c = conn.cursor()
    c.execute("UPDATE profile SET plan_tier = ? WHERE id = 1", (plan,))
    conn.commit()
    conn.close()
    return RedirectResponse("/pricing?upgraded=true", status_code=303)

# ----------------- SETTINGS ----------------- #

@app.get("/settings", response_class=HTMLResponse)
async def settings_page(request: Request):
    profile = get_profile()
    return templates.TemplateResponse(request, "settings.html", {
        "profile": profile
    })

@app.post("/settings/save")
async def save_settings(
    business_name: str = Form(...),
    owner_name: str = Form(...),
    phone: str = Form(...),
    email: str = Form(...),
    upi_id: str = Form(...),
    gstin: Optional[str] = Form(""),
    address: Optional[str] = Form(""),
    bank_name: Optional[str] = Form(""),
    acc_number: Optional[str] = Form(""),
    ifsc_code: Optional[str] = Form("")
):
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
    UPDATE profile SET
        business_name = ?,
        owner_name = ?,
        phone = ?,
        email = ?,
        upi_id = ?,
        gstin = ?,
        address = ?,
        bank_name = ?,
        acc_number = ?,
        ifsc_code = ?
    WHERE id = 1
    """, (business_name, owner_name, phone, email, upi_id, gstin, address, bank_name, acc_number, ifsc_code))
    conn.commit()
    conn.close()
    return RedirectResponse("/settings?saved=true", status_code=303)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
