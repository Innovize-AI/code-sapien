# Speed-to-Lead — Knowledge Base Data Guide

This document explains exactly what data you need to provide so the AI sales agent can answer leads accurately.

There are three inputs: **knowledge.txt**, **portfolio.json**, and **resources.json**.
You do not need to format anything yourself — share the raw information with us and we will prepare these files.

---

## 1. knowledge.txt — FAQs and Operational Facts

This is the AI's primary reference. It should cover everything a lead might ask.
Structure it as sections with plain headings. The AI retrieves relevant chunks automatically.

### Sections to include

---

### About Your Company

Basic background a lead might want to know before trusting you.

```
## ABOUT [YOUR FIRM NAME]

Founded: [year]
Experience: [X years in real estate]
Projects completed: [N]
Families served: [N]
Certifications: [RERA, ISO, etc.]

Head office: [address]
Phone: [number]
Email: [email]
Website: [URL]
```

---

### Why Choose You

3–7 trust-building points. Keep them factual, not marketing copy.

```
## WHY CHOOSE [FIRM NAME]

1. RERA registered — all projects approved, legally transparent.
2. On-time delivery — consistent track record with [X] projects delivered on schedule.
3. [Payment plan flexibility — CLP, 20:80, subvention scheme available]
4. [In-house property management after possession]
5. [Banking tie-ups — SBI, HDFC, ICICI, Axis for home loans]
```

---

### Current Projects

One section per active project. Include everything a lead might ask.

```
## CURRENT PROJECTS

### [Project Name] — [Location]
Status: New Launch / Under Construction / Ready to Move
Configuration: 2 BHK / 3 BHK / 4 BHK / Villa
Unit Size: [min] – [max] sq ft
Price: Rs [X] per sq ft (approx Rs [Y] Cr to Rs [Z] Cr)
Total Units: [N]
Towers: [N towers, floors]
RERA Number: [PXXXXXXXXX]
Possession: [Month Year] (estimated)

Location advantages: [2–3 sentences on connectivity, landmarks, nearby IT parks/schools]

Highlights:
- [Key amenity 1 — e.g. 2-acre podium garden]
- [Key amenity 2 — e.g. Olympic-size pool]
- [Key amenity 3]
```

Add a separate section for each project. If a project is sold out, note it clearly so the agent does not pitch it.

---

### Visit Logistics

Critical section — the agent uses this during booking and conversion stages.

```
## SITE VISIT INFORMATION

Visit hours: [10AM–6PM, 7 days a week / Mon–Sat 10AM–5PM / etc.]
Duration: Approximately 60–90 minutes with a sales manager.
Cab service: Complimentary cab pickup from [coverage area — e.g. anywhere in Hyderabad / within 25 km].
Commitment: No obligation on the visit day.

To book a visit: WhatsApp us or call [number].
What to bring: Any ID proof for registration at the site.
```

---

### Pricing and Payment Plans

```
## PRICING AND PAYMENT

Overall price range: [Rs X lakhs to Rs Y crore depending on project and configuration]
Minimum starting price: [Rs X lakhs — project name]
Payment plan options:
- Construction Linked Plan (CLP): pay in stages as construction milestones are met.
- 20:80 plan: 20% now, 80% at possession.
- Subvention scheme: EMI paid by builder until possession (subject to project availability).

Home loan tie-ups: [SBI / HDFC / ICICI / Axis / Yes Bank — team can assist with pre-approvals]
```

---

### Process — How Buying Works

Include this so the agent can educate first-time buyers.

```
## BUYING PROCESS

1. Site Visit — see the project, no commitment.
2. EOI (Expression of Interest) — blocks your preferred unit with a token amount.
3. Agreement — sale agreement signed within [X days].
4. Construction Linked Payments — staged payments as per plan.
5. Possession — handover with OC (Occupancy Certificate).

RERA protects buyers: developers are legally required to meet timelines or pay compensation.
```

---

### Objections and FAQs

Cover the questions your sales team hears most often. The AI handles these automatically.

```
## FREQUENTLY ASKED QUESTIONS

Q: Are there builder delays?
A: All our projects are RERA registered. RERA mandates 10.75% per annum compensation for delays. [Firm] has a consistent on-time delivery track record across [N] projects.

Q: Can I get a home loan?
A: Yes. We have tie-ups with [bank names]. Our team can help with pre-approvals for both salaried and self-employed buyers.

Q: Is the location good for investment?
A: [Your answer — e.g. Gachibowli corridor has seen X% appreciation over 5 years. RERA + reputed builder = lower risk.]

Q: What if I want to compare with other builders?
A: [Your answer — factual differentiators only. Do not mention competitor names.]

Q: Can I bring my family on the visit?
A: Absolutely — families are welcome. We can arrange the cab for everyone.

Q: Is there a maintenance charge after possession?
A: [Your answer on AMC, property management, etc.]
```

Add as many Q&A pairs as your sales team encounters.

---

### RERA and Legal

```
## RERA AND LEGAL

All projects RERA registered with MaHaRERA / RERA [state].
Registration numbers:
- [Project 1]: [RERA number]
- [Project 2]: [RERA number]

Legal team available for queries on agreement terms.
```

---

## 2. portfolio.json — Project Cards for the AI

The AI uses this to match leads to the right project based on their config and budget.
Each project is one object in the array.

```json
[
  {
    "id": "your-project-slug",
    "title": "Project Name — Configuration, Location",
    "description": "2–3 sentence description the AI will use to pitch this project. Include location, price range, unit size, standout feature, and RERA number.",
    "location": "Area, City",
    "config": "3BHK",
    "price_min": 11800000,
    "price_max": 16000000,
    "price_per_sqft": 7999,
    "size_min_sqft": 1471,
    "size_max_sqft": 2001,
    "total_units": 759,
    "towers": 3,
    "status": "new_launch",
    "rera_number": "P01100011037",
    "possession_date": "2028-2029 (estimated)",
    "vertical": "real_estate"
  }
]
```

**Field reference:**

| Field | What to fill |
|---|---|
| `id` | Unique short slug, lowercase with hyphens. E.g. `my-project-name` |
| `title` | Full display name with config and location |
| `description` | 2–3 sentences the AI will use to pitch it |
| `location` | Neighbourhood, City |
| `config` | Comma-separated: `"2BHK,3BHK"` or just `"3BHK"` |
| `price_min` / `price_max` | Rupees as integers (no commas). E.g. 9000000 for 90 lakhs |
| `price_per_sqft` | Per sq ft base price. Leave `null` if not disclosed |
| `size_min_sqft` / `size_max_sqft` | Unit size range in sq ft |
| `status` | `new_launch` / `under_construction` / `ready_to_move` / `sold_out` |
| `rera_number` | RERA registration number |
| `possession_date` | Estimated possession, as text |

---

## 3. resources.json — Brochures and Videos

These are PDFs or YouTube links the AI can share during the conversation.
The AI decides when to share each one based on the conversation context.

```json
[
  {
    "id": "project-brochure",
    "title": "Project Name — Brochure",
    "description": "Share when lead has shown genuine interest and asks for more details. Contains floor plans, price list, and amenity overview.",
    "resource_type": "pdf",
    "filename": "project-brochure.pdf"
  },
  {
    "id": "payment-plan-guide",
    "title": "Payment Plan Guide",
    "description": "Share when lead asks about home loans, EMI, or payment stages.",
    "resource_type": "pdf",
    "filename": "payment-plan-guide.pdf"
  },
  {
    "id": "walkthrough-video",
    "title": "Project Walkthrough — YouTube",
    "description": "Share when lead asks to see the project visually or wants a virtual tour.",
    "resource_type": "youtube",
    "url": "https://youtube.com/watch?v=..."
  }
]
```

**For PDFs:** provide the actual PDF files. We upload them and generate shareable links.
**For videos:** provide the YouTube or Google Drive link directly in the `url` field.

The `description` field is important — it tells the AI when to share each resource. Be specific.

---

## 4. Firm Settings (One-Time Setup)

These are configured in our system once during onboarding:

| Setting | Example | Notes |
|---|---|---|
| Firm name | Aparna Constructions | Displayed in all messages |
| Visit CTA label | site visit (cab arranged) | Phrase used when inviting to visit |
| Contact phone | 7095333335 | Used in escalation and fallback messages |
| Contact email | sales@yourfirm.com | Optional |

Everything else — pricing, hours, cab coverage, RERA — lives in the knowledge base so it can be updated without a developer.

---

## Checklist

Before going live, confirm you have provided:

- [ ] `knowledge.txt` — about the firm, all projects, visit logistics, pricing, FAQs
- [ ] `portfolio.json` — one entry per active project
- [ ] `resources.json` — list of all brochures/videos with when-to-share descriptions
- [ ] PDF files for all brochures
- [ ] Firm settings: display name, contact phone, contact email, visit CTA label

---

*Questions? Contact your InnovizeAI setup contact.*
