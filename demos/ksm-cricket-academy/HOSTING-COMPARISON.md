# Hosting Platform Comparison — Next.js Apps

> Researched September 2026. Verify pricing at each provider before committing — promotional rates change frequently.

---

## Main Comparison

| Platform | Free Tier | Free Custom Domain | Free SSL | Paid Starts At | Next.js Support | Deploy Method |
|---|---|---|---|---|---|---|
| **Vercel** | Yes (Hobby) | Yes — Hobby supports up to 50 custom domains per project | Yes | $20/mo (Pro) | Native (built by Vercel team) | Git / CLI |
| **Netlify** | Yes (Free plan) | Yes — included on free plan | Yes | $9/mo (Personal) | Good (via adapter) | Git / CLI |
| **Render** | Yes (spins down after 15 min) | Yes — custom domains on free tier | Yes | $7/mo (no spin-down) | Good | Git |
| **Railway** | Free plan: $1/mo credit, 0 custom domains. Hobby: $5/mo, 2 domains | No on free plan. Yes on Hobby ($5/mo) | Yes | $5/mo (Hobby) | Good | Git / CLI |
| **DigitalOcean App Platform** | Yes — static sites free (3 apps, 1 GiB transfer/app) | Yes — custom domains on free tier | Yes | $5/mo (Node.js app) | Good | Git |
| **DigitalOcean VPS (Droplet)** | No | Point your own DNS (free) | Yes (Let's Encrypt, self-setup) | $6/mo | Full (self-configured) | SSH / CI |
| **Google Cloud Run** | Yes — 2M req/mo, 360K GB-sec memory, 1 GB egress free forever | Yes — domain mapping is free | Yes | Pay-per-use (~$0 at low traffic) | Full (via Docker) | Docker / gcloud CLI |
| **Hostinger Web Apps (Managed)** | No | Free domain registration included — year 1 only | Yes | $3.99/mo (promo) | Good — auto-detects Next.js | hPanel / GitHub |
| **Hostinger VPS (KVM 1)** | No | Free domain registration included — year 1 only | Yes (Let's Encrypt, self-setup) | $6.49/mo (promo) | Full (self-configured) | SSH |

---

## Custom Domain — Exact Details

| Platform | What "free custom domain" actually means |
|---|---|
| **Vercel** | Connect your own domain at no extra cost. Up to 50 domains/project on Hobby. No registration included — you buy the domain elsewhere. |
| **Netlify** | Connect your own domain free on all plans. No registration included. |
| **Render** | Custom domain mapping is free on all tiers including free. No registration included. |
| **Railway** | Free plan allows 0 custom domains. Hobby ($5/mo) allows 2. No registration included. |
| **DigitalOcean App Platform** | Connect your own domain free on all tiers. No registration included. |
| **DigitalOcean VPS** | Point your domain's DNS to your droplet — free. You manage SSL yourself (Certbot / Let's Encrypt). |
| **Google Cloud Run** | Domain mapping is free. SSL certificates auto-provisioned. No registration included. |
| **Hostinger Managed** | Includes one free domain registration for year 1 (renewal ~$10–15/yr). Best option if you don't own a domain yet. |
| **Hostinger VPS** | Also includes free domain registration for year 1 across all KVM plans. |

---

## Free Tier — Key Limits

| Platform | Bandwidth | Compute | Sleeps / Spins Down? | Other |
|---|---|---|---|---|
| **Vercel Hobby** | 100 GB/mo | 1M function invocations/mo | No | 1 seat, non-commercial use only |
| **Netlify Free** | Not published on pricing page | Not published | No | 1 member |
| **Render Free** | Shared pool | 750 instance hours/mo | Yes — after 15 min idle (~1 min restart) | No persistent disk, no SSH |
| **Railway Free** | Shared | $1/mo credit (~tiny) | No | 0 custom domains, very limited |
| **DigitalOcean Free** | 1 GiB/app/mo | Static only (no Node.js) | No | Node.js requires paid plan |
| **Google Cloud Run** | 1 GB egress/mo | 2M req + 360K GB-sec/mo | No (scales to zero but no cold-start delay cap) | Needs Docker knowledge |

---

## Paid Plan Pricing (Accurate)

| Platform | Plan | Price | What You Get |
|---|---|---|---|
| **Vercel** | Pro | $20/mo | Unlimited bandwidth, teams, analytics |
| **Netlify** | Personal | $9/mo | More build minutes, form submissions |
| **Netlify** | Pro | $20/mo | Unlimited members |
| **Render** | Starter Web Service | $7/mo | No spin-down, 512 MB RAM, 0.5 CPU |
| **Railway** | Hobby | $5/mo | $5 credit included, 2 custom domains |
| **Railway** | Pro | $20/mo | $20 credit included, 20 custom domains |
| **DigitalOcean App** | Basic Node.js | $5/mo | 512 MiB RAM, 1 vCPU, 50 GiB transfer |
| **DigitalOcean VPS** | KVM 1 | $6.49/mo (promo) | 4 GB RAM, 50 GB NVMe, 4 TB bandwidth |
| **Google Cloud Run** | Pay-per-use | ~$0–5/mo low traffic | Auto-scales, generous free tier |
| **Hostinger Managed** | Web Apps | $3.99/mo (promo, was $16.99) | Free domain yr 1, GitHub deploy, Next.js support |
| **Hostinger VPS** | KVM 1 | $6.49/mo (promo, was $11.99) | 4 GB RAM, 50 GB NVMe, free domain yr 1 |

> Hostinger prices shown are promotional rates. Renewal rates are significantly higher — Managed renews at ~$16.99/mo, VPS KVM 1 renews at ~$11.99/mo.

---

## Recommendation for KSM Cricket Academy

| Scenario | Best Choice | Why |
|---|---|---|
| Domain not registered yet, budget-first | **Hostinger Managed ($3.99/mo)** | Domain included yr 1, Next.js auto-detected, lowest all-in cost |
| Domain already owned, zero infra effort | **Vercel Hobby (Free)** | Git push deploys, custom domain free, no sleep, no config |
| Expecting traffic spikes (tournament days) | **Google Cloud Run (near-free)** | Scales to handle spikes automatically, near-zero idle cost |
| Want a proper managed server with control | **Hostinger VPS KVM 1 ($6.49/mo)** | Full control, domain included, 4 TB bandwidth |
| Registration form must never sleep | **Any paid plan** | Avoid Render free tier — 1 min restart on a payment/registration form is unacceptable |

---

> Sources: vercel.com/pricing, vercel.com/docs, netlify.com/pricing, render.com/docs/free, railway.com/pricing, digitalocean.com/pricing/app-platform, cloud.google.com/run/pricing, hostinger.com/nodejs-hosting, hostinger.com/vps-hosting — September 2026
