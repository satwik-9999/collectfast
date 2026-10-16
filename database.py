import sqlite3
import os
import uuid
from datetime import datetime, date, timedelta

DB_PATH = os.path.join(os.path.dirname(__file__), "collectfast.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Business profile
    c.execute("""
    CREATE TABLE IF NOT EXISTS profile (
        id INTEGER PRIMARY KEY,
        business_name TEXT DEFAULT 'Apex Creative Studio',
        owner_name TEXT DEFAULT 'Satwik Rao',
        email TEXT DEFAULT 'satwik@example.com',
        phone TEXT DEFAULT '919876543210',
        upi_id TEXT DEFAULT 'satwikrao@okhdfcbank',
        gstin TEXT DEFAULT '29ABCDE1234F1Z5',
        address TEXT DEFAULT '104, Indiranagar 100ft Road, Bengaluru, KA 560038',
        bank_name TEXT DEFAULT 'HDFC Bank',
        acc_number TEXT DEFAULT '50100234567890',
        ifsc_code TEXT DEFAULT 'HDFC0001234',
        plan_tier TEXT DEFAULT 'pro',
        invoices_count INTEGER DEFAULT 0
    )
    """)

    # Clients
    c.execute("""
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        company TEXT,
        email TEXT,
        phone TEXT NOT NULL,
        gstin TEXT,
        address TEXT,
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Invoices
    c.execute("""
    CREATE TABLE IF NOT EXISTS invoices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_number TEXT UNIQUE NOT NULL,
        client_id INTEGER NOT NULL,
        issue_date TEXT NOT NULL,
        due_date TEXT NOT NULL,
        status TEXT DEFAULT 'pending', -- 'paid', 'pending', 'overdue', 'draft'
        subtotal REAL DEFAULT 0,
        tax_rate REAL DEFAULT 18.0,
        tax_amount REAL DEFAULT 0,
        discount_amount REAL DEFAULT 0,
        grand_total REAL DEFAULT 0,
        notes TEXT,
        token TEXT UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id)
    )
    """)

    # Invoice Line Items
    c.execute("""
    CREATE TABLE IF NOT EXISTS invoice_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        description TEXT NOT NULL,
        quantity REAL DEFAULT 1,
        unit_price REAL NOT NULL,
        total REAL NOT NULL,
        FOREIGN KEY (invoice_id) REFERENCES invoices (id) ON DELETE CASCADE
    )
    """)

    # Reminders Log
    c.execute("""
    CREATE TABLE IF NOT EXISTS reminders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        invoice_id INTEGER NOT NULL,
        reminder_type TEXT,
        sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        channel TEXT DEFAULT 'WhatsApp',
        FOREIGN KEY (invoice_id) REFERENCES invoices (id)
    )
    """)

    conn.commit()

    # Check if profile exists, if not create default
    c.execute("SELECT COUNT(*) FROM profile")
    if c.fetchone()[0] == 0:
        c.execute("""
        INSERT INTO profile (business_name, owner_name, email, phone, upi_id, gstin, address, bank_name, acc_number, ifsc_code, plan_tier)
        VALUES ('Apex Creative Studio', 'Satwik Rao', 'satwik@example.com', '919876543210', 'satwikrao@okhdfcbank', '29ABCDE1234F1Z5', '104, Indiranagar 100ft Rd, Bengaluru, KA', 'HDFC Bank', '50100234567890', 'HDFC0001234', 'pro')
        """)
        conn.commit()

    # Seed demo data if clients table is empty
    c.execute("SELECT COUNT(*) FROM clients")
    if c.fetchone()[0] == 0:
        seed_demo_data(conn)

    conn.close()

def seed_demo_data(conn):
    c = conn.cursor()
    today = date.today()
    
    # 4 Demo Clients
    clients = [
        ("Kavita Menon", "Zenith Digital Media", "kavita@zenithmedia.in", "919845012345", "29XYZAB1234C1Z1", "Koramangala 4th Block, Bengaluru"),
        ("Rahul Sharma", "IronFit Gym & Wellness", "rahul@ironfit.in", "919988776655", "", "Bandra West, Mumbai"),
        ("Ananya Roy", "NexGen Software Labs", "ananya@nexgenlabs.io", "919871234567", "07AAACN1234Q1Z8", "Sector 62, Noida"),
        ("Vikram Singhania", "Singhania Logistics", "accounts@singhanialogistics.com", "919712345678", "27AAAAA0000A1Z5", "Nariman Point, Mumbai")
    ]

    client_ids = []
    for cl in clients:
        c.execute("""
        INSERT INTO clients (name, company, email, phone, gstin, address)
        VALUES (?, ?, ?, ?, ?, ?)
        """, cl)
        client_ids.append(c.lastrowid)

    # Invoices
    # 1. Paid invoice (Zenith Digital) - 15 days ago
    inv1_date = (today - timedelta(days=20)).strftime("%Y-%m-%d")
    inv1_due = (today - timedelta(days=5)).strftime("%Y-%m-%d")
    c.execute("""
    INSERT INTO invoices (invoice_number, client_id, issue_date, due_date, status, subtotal, tax_rate, tax_amount, discount_amount, grand_total, notes, token)
    VALUES (?, ?, ?, ?, 'paid', 85000, 18, 15300, 0, 100300, 'Monthly SEO & Content Retainer - Completed', ?)
    """, ("INV-2026-001", client_ids[0], inv1_date, inv1_due, str(uuid.uuid4())[:12]))
    inv1_id = c.lastrowid
    c.execute("INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
              (inv1_id, "SEO & Content Marketing Monthly Retainer", 1, 60000, 60000))
    c.execute("INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
              (inv1_id, "High-Authority Backlink Outreach Package", 1, 25000, 25000))

    # 2. Overdue invoice (IronFit Gym) - Due 6 days ago
    inv2_date = (today - timedelta(days=16)).strftime("%Y-%m-%d")
    inv2_due = (today - timedelta(days=6)).strftime("%Y-%m-%d")
    c.execute("""
    INSERT INTO invoices (invoice_number, client_id, issue_date, due_date, status, subtotal, tax_rate, tax_amount, discount_amount, grand_total, notes, token)
    VALUES (?, ?, ?, ?, 'overdue', 35000, 18, 6300, 0, 41300, 'Website Redesign Phase 2 Payment', ?)
    """, ("INV-2026-002", client_ids[1], inv2_date, inv2_due, str(uuid.uuid4())[:12]))
    inv2_id = c.lastrowid
    c.execute("INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
              (inv2_id, "Gym Membership Web Portal UI/UX Design", 1, 20000, 20000))
    c.execute("INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
              (inv2_id, "Front-end Development & Mobile Responsiveness", 1, 15000, 15000))

    # 3. Pending invoice (NexGen Labs) - Due in 3 days
    inv3_date = (today - timedelta(days=4)).strftime("%Y-%m-%d")
    inv3_due = (today + timedelta(days=3)).strftime("%Y-%m-%d")
    c.execute("""
    INSERT INTO invoices (invoice_number, client_id, issue_date, due_date, status, subtotal, tax_rate, tax_amount, discount_amount, grand_total, notes, token)
    VALUES (?, ?, ?, ?, 'pending', 48000, 18, 8640, 2000, 54640, 'UI System & Component Library Delivery', ?)
    """, ("INV-2026-003", client_ids[2], inv3_date, inv3_due, str(uuid.uuid4())[:12]))
    inv3_id = c.lastrowid
    c.execute("INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
              (inv3_id, "Figma Design System & Token Integration", 1, 48000, 48000))

    # 4. Another Pending (Singhania Logistics) - Due in 7 days
    inv4_date = today.strftime("%Y-%m-%d")
    inv4_due = (today + timedelta(days=7)).strftime("%Y-%m-%d")
    c.execute("""
    INSERT INTO invoices (invoice_number, client_id, issue_date, due_date, status, subtotal, tax_rate, tax_amount, discount_amount, grand_total, notes, token)
    VALUES (?, ?, ?, ?, 'pending', 75000, 18, 13500, 0, 88500, 'Quarterly Cloud Architecture Audit', ?)
    """, ("INV-2026-004", client_ids[3], inv4_date, inv4_due, str(uuid.uuid4())[:12]))
    inv4_id = c.lastrowid
    c.execute("INSERT INTO invoice_items (invoice_id, description, quantity, unit_price, total) VALUES (?, ?, ?, ?, ?)",
              (inv4_id, "AWS Cloud Cost & Security Architecture Review", 1, 75000, 75000))

    conn.commit()
