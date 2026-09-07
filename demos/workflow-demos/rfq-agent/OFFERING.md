# RFQ Agent — Packaged Offering

**Target:** Manufacturing, Trading/Distribution, Construction, Pharma, Logistics  
**Positioning:** AI-powered RFQ-to-Quote automation. Receive RFQs from any channel, auto-generate quotes, dispatch instantly — without a sales person manually reading every email.

---

## What's Included in the Package

### 1. Source Connectors (where RFQs come in)
| Source | Notes |
|---|---|
| Email (Gmail / Outlook) | Monitor inbox, auto-ingest RFQ emails |
| WhatsApp Business | Buyer sends PDF or types RFQ in chat |
| Web Form | Embeddable widget for their website |
| Manual Upload | PDF, Word, image, or paste text |
| Webhook / API | For businesses with existing portals or ERPs |

Toggle each source on/off from the Settings page. Paste credentials once, never touch it again.

---

### 2. Output / Dispatch Destinations
| Destination | What happens |
|---|---|
| Email reply | Auto-send formatted quote to buyer |
| Slack | Notify sales team with quote summary + approval link |
| WhatsApp | Reply on the same thread buyer used |
| Google Sheets | Append every quote to a tracker sheet |
| CRM (HubSpot / Zoho / Salesforce) | Create a deal with quote attached |
| PDF Download | Branded PDF quotation, ready to forward |
| ERP Push (Tally / SAP) | Push accepted quotes as sales orders |

---

### 3. Catalog Management
- Upload product catalog via CSV / Excel
- View and edit products inline
- See which products matched on recent RFQs
- Flag products that frequently come up but aren't in catalog
- Bulk price update (increase all by X%)

---

### 4. Rules & Thresholds (No-code config)
| Rule | Default | Configurable |
|---|---|---|
| Confidence threshold for auto-dispatch | 75% | Yes |
| Amount above which review is required | ₹5,00,000 | Yes |
| Categories that always go to review | — | Yes |
| Dispatch hours (no quotes at 2am) | Always on | Yes |
| Quote validity / expiry | 7 days | Yes |
| GST slab to apply | 18% | Yes per category |

---

### 5. Approval Workflow
- Single-level: one person approves before dispatch
- Multi-level: manager → finance head for large quotes
- Mobile-friendly approval — approve from phone
- Auto-escalate if not approved within X hours

---

### 6. Quote Customization
- Company logo, name, colors on every quote PDF
- Custom header / footer text
- Standard T&Cs block (editable)
- Payment terms selection (advance / 30 days / LC)
- Partial fulfillment quotes ("We can supply 8 of 12 items")
- Quote versioning (V1, V2, V3 per RFQ)

---

### 7. Multi-language Support
- Accept RFQs in Hindi, Telugu, Tamil, Marathi
- Quote generated in English (or buyer's language)
- Especially useful for WhatsApp channel

---

### 8. Voice RFQ (Add-on)
- Buyer calls and describes requirement verbally
- Transcribed via Whisper → parsed → quoted
- Ideal for small traders who don't type RFQs

---

### 9. Follow-up Automation
- If buyer doesn't respond in X days → auto follow-up email/WhatsApp
- "Your quote for 500 M8 bolts expires in 2 days — shall we proceed?"
- Win/loss tracking — mark accepted/rejected, track close rate

---

### 10. Revision Handling
- Buyer replies "can you do 450 instead of 500?" → agent re-quotes
- Track revision history per RFQ
- Highlight what changed between versions

---

### 11. Analytics Dashboard
| Metric | Why it matters |
|---|---|
| Avg time: RFQ received → quote dispatched | Show time saved vs manual |
| Auto-dispatch rate | % of quotes sent without human touch |
| Avg quote value | Business volume insight |
| Most requested products | Procurement planning |
| Buyer response rate | Effectiveness of quotes |
| Win rate by category | Where you win/lose |

---

### 12. Onboarding Wizard (first-time setup)
5 steps, takes under 30 minutes:
1. Company name + logo
2. Connect email inbox (OAuth — no password sharing)
3. Upload product catalog (CSV template provided)
4. Set pricing rules (markup %, GST %, review thresholds)
5. Test with a real RFQ

---

### 13. Customer Portal (Add-on)
- Buyer gets a link to track their RFQ status
- Can accept/reject quote online
- Can request revision
- Removes back-and-forth email chains entirely

---

### 14. Competitor Intelligence (Add-on)
- If market rate data is available, show if your price is competitive
- "Market rate for M8 bolts: ₹4.20/unit — your price: ₹3.90/unit ✓"

---

## What This Replaces

| Before | After |
|---|---|
| Sales person reads every email manually | AI extracts items instantly |
| Checks catalog in Excel | AI matches against catalog automatically |
| Calculates price in head or spreadsheet | AI applies rules + generates quote |
| Types quote in Word/email | Formatted PDF dispatched automatically |
| Forgets to follow up | Auto follow-up on schedule |
| No visibility on pipeline | Live dashboard with all metrics |

**Time saved:** 45–90 minutes per RFQ for a manufacturing business handling 10–50 RFQs/day.

---

## Deployment Options

| Option | Details |
|---|---|
| Hosted (SaaS) | We host, client gets subdomain — `client.rfqagent.in` |
| On-premise | Deployed on client's server, their data stays with them |
| White-label | Branded as client's own product for resellers |

---

## Implementation Timeline

| Phase | Duration | What gets done |
|---|---|---|
| Setup & Config | Week 1 | Catalog upload, email/WhatsApp connect, rules config |
| Testing | Week 2 | Test with real RFQs, tune confidence thresholds |
| Go-live | Week 3 | Full deployment, team training |
| Optimization | Month 2 | Analytics review, rule adjustments |

---

## Industries & Customization per Vertical

| Industry | Custom fields | Typical RFQ volume |
|---|---|---|
| Manufacturing | Material grade, tolerance, finish | 10–50/day |
| Trading / Distribution | Brand preference, pack size, MOQ | 20–100/day |
| Construction | Site delivery, project code, BOQ items | 5–20/day |
| Pharma | Batch size, expiry, FSSAI/Schedule | 10–30/day |
| Logistics / Freight | Origin, destination, cargo type, weight | 15–60/day |

---

## Construction — Vertical Deep Dive

**Who:** General contractors, real estate developers, MEP subcontractors, infrastructure firms  
**Sweet spot:** ₹50–500 Cr turnover, 3–20 active sites, no ERP or using basic Tally

### Their Specific Struggles

| Pain | Detail |
|---|---|
| BOQ chaos | Every project has a Bill of Quantities with 100–500 line items. Sending it to 5 vendors and reconciling 5 different response formats takes days. |
| Price volatility | TMT bars, cement, aggregates change price weekly. A quote from last Tuesday is already wrong. |
| WhatsApp overload | Site engineers raise material requests on WhatsApp. Procurement head has 200 unread messages on any given day. |
| No urgency triage | "Critical" (site stops tomorrow) and "routine" (next month) items land in the same inbox with no differentiation. |
| Multi-site confusion | 5 active sites, each with different project codes. Materials purchased for Site A billed to Site B by mistake. |
| Approval gaps | Purchases >₹50k need PM sign-off, >₹2L need MD. Nobody tracks whether approval was given before purchase. |
| Vendor reliability blind spot | They know ABC Steels is unreliable but have no data to prove it — just a feeling. |

### What the Agent Does Differently for Construction

**BOQ Parser**
- Accepts full BOQ as Excel/PDF (100–500 line items)
- Splits into vendor-wise RFQs automatically (structural steel to Steel vendor, electrical to MEP vendor)
- No more manually copying items into 5 separate emails

**Three RFQ Types**
1. **Materials** — cement, steel, aggregates, tiles, pipes, paint
2. **Plant Hire** — JCB, crane, scaffolding, concrete mixer (daily/weekly rate)
3. **Subcontractor Scope** — plastering, tiling, electrical, plumbing (rate per sqft/unit)

**Rate History**
- "Last purchased TMT Fe500 at ₹58/kg on 12 July from ABC Steels"
- Shows alongside new quote so buyer can immediately see if vendor is inflating price

**Regional Pricing**
- Material prices vary 15–25% between Mumbai, Pune, Hyderabad, Bangalore
- Catalog stores location-aware base rates, not a single national price

**Site-wise Tagging**
- Every RFQ tagged to a project code (e.g., `PROJ-2024-BLR-04`)
- Procurement dashboard filterable by site
- Correct cost center for billing

**Approval Hierarchy**
- <₹50,000 → auto-dispatch
- ₹50,000–₹2,00,000 → Project Manager approval
- >₹2,00,000 → MD approval
- Escalates automatically if no response in 2 hours

**Quote Validity Warning**
- PDF quote shows "Valid for 3 days only" with construction materials (vs 30 days for standard products)
- Auto-reminder to buyer at day 2

**Vendor Scorecard**
- On-time delivery rate per vendor
- Quality rejection rate (materials that came and were rejected at site)
- Price reliability (how often quoted price matches invoice)
- Surfaces this alongside each new quote: "ABC Steels: 78% on-time, 2 rejections last quarter"

### Preset Settings for Construction

When a construction company onboards, these defaults are applied automatically:

| Setting | Construction Default | Standard Default |
|---|---|---|
| Quote validity | 3 days | 30 days |
| Amount threshold for review | ₹50,000 | ₹5,00,000 |
| GST rate | 18% (materials) / 12% (subcontract) | 18% |
| RFQ types enabled | Materials + Plant Hire + Subcontractor | Product only |
| Multi-level approval | On (2 levels) | Off |
| Site/project code field | Required | Hidden |
| Rate history | Shown on every quote | Hidden |
| BOQ upload | Enabled | Disabled |

### Sales Talking Points

- **"Your site engineers are raising material requests on WhatsApp at 8pm. Your procurement team sees them at 9am the next day. That's a 13-hour delay on every urgent order."**
- **"You're calling vendors every time because you don't know if last month's rate still holds. We track that for you."**
- **"A mid-size contractor doing ₹100Cr/year handles 800–1,500 RFQs. At 45 min/RFQ manual effort, that's one full-time employee doing nothing but sending quotation emails."**
- **"You've been burned by a vendor who quoted low and invoiced higher. Our system flags vendors with a history of price variance."**
