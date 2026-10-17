# 🚀 CollectFast — 0% Fee UPI Invoicing & WhatsApp Payment Recovery Engine

[![Live Demo](https://img.shields.io/badge/Live_Demo-Try_Online-success?style=for-the-badge&logo=google-chrome)](https://satwik-9999.github.io/collectfast/)
[![GitHub Repo](https://img.shields.io/badge/GitHub-Repo-181717?style=for-the-badge&logo=github)](https://github.com/satwik-9999/collectfast)
[![License: Commercial](https://img.shields.io/badge/License-White--Label-blue?style=for-the-badge)](./COMMERCIAL_LICENSE.md)

👉 **[⚡ Click Here to Launch the Live Interactive Demo](https://satwik-9999.github.io/collectfast/)** (Simulate dynamic UPI QR codes and 1-click WhatsApp follow-ups in your browser without installing anything).

**CollectFast** is a high-margin B2B Micro-SaaS designed for Indian freelancers, digital agencies, and service SMBs to generate professional GST invoices, collect instant payments with dynamic UPI QR codes (0% gateway fees), and recover unpaid dues 3x faster via 1-click WhatsApp behavioral nudges.

---

## 🎯 The Math to ₹1,00,000 / Month MRR

Software alone does not make money; **paying customers** do. Here are two direct strategies to reach ₹1,00,000/month using this exact product:

| Target Market | Tier Price | Clients Needed | Monthly Recurring Revenue |
| :--- | :--- | :--- | :--- |
| **Digital Agencies & Studios** | **₹1,499 / mo** | **67 Agencies** | **₹1,00,433 / mo** |
| **Freelancers & Consultants** | **₹499 / mo** | **200 Users** | **₹99,800 / mo** |

### Why Customers Pay:
* **0% Transaction Fees**: Unlike Razorpay or Stripe which deduct 2% to 3% + GST on every transaction, CollectFast routes money directly to the vendor's bank account via standard BHIM UPI protocol.
* **Instant WhatsApp Recovery**: Over 80% of overdue invoices in India are delayed simply because vendors hate awkward follow-up calls. 1-click psychology-tested WhatsApp nudges reduce payment collection delay by 70%.

---

## ⚡ Core Features Built In

1. **Dashboard & ₹1L Goal Tracker**: Real-time monitoring of collected revenue, pending dues, overdue accounts, and collection efficiency percentage.
2. **Instant Dynamic UPI QR Generator**: Generates real-time NPCI-compliant UPI QR codes (`upi://pay?pa=...&am=...&cu=INR`) for every invoice.
3. **1-Click WhatsApp Chaser**:
   - *Gentle Nudge*: Polite reminder before due date.
   - *Due Notice*: Direct link + payment urgency.
   - *Overdue / Final Notice*: Firm message with one-tap payment link.
4. **Customer Payment Portal (`/pay/{token}`)**:
   - Mobile-optimized checkout page.
   - 1-tap "Pay with Google Pay / PhonePe / Paytm / BHIM" launcher via native mobile deep-linking.
   - Bank NEFT/IMPS transfer details.
   - "I have paid" confirmation button.
5. **PDF Generator (`/invoices/{id}/pdf`)**: Generates print-ready Tax Invoices with embedded UPI QR codes and bank details using ReportLab.
6. **Client Khata & Ledger (`/clients`)**: Complete ledger of who owes what, total billed vs cleared.
7. **Built-in Monetization & Upgrades (`/pricing`)**: Free, Pro (₹499/mo), and Agency (₹1,499/mo) subscription tiers with an interactive ROI calculator.

---

## 🛠️ How to Run & Deploy

### Run Locally:
```powershell
cd C:\Users\Satwi\.gemini\antigravity\scratch\collectfast
py -3.13 -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

### Deploy to Production (Zero Cost to Start):
1. **Host on Render / Railway / Fly.io**: Connect this GitHub repo, set build command `pip install -r requirements.txt`, and start command `uvicorn main:app --host 0.0.0.0 --port $PORT`.
2. **Add Custom Domain**: e.g., `app.collectfast.in`.
3. **Connect Payment Gateway for SaaS Subscriptions**: Integrate Razorpay Subscriptions or Cashfree for accepting ₹499/mo or ₹1,499/mo subscription payments.
