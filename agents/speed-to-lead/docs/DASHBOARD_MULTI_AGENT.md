# Multi-Agent Dashboard Architecture

The frontend dashboard is built to serve multiple AI agents from a single interface.
New agents slot in by adding one entry to the `AGENTS` config in `sidebar.tsx`.

## Sidebar Structure

```
┌────────────────────────────┐
│ 🤖 Saarthi                 │  ← Platform brand (fixed)
│    AI Agent Dashboard      │
├────────────────────────────┤
│ ┌──────────────────────┐   │
│ │ DWPS Admissions  ▾   │   │  ← Agent dropdown (click to switch)
│ └──────────────────────┘   │
│                            │
│   📊 Analytics             │  ← Nav items for selected agent
│   💬 Conversations         │
│   📅 Campus Visits         │
│                            │
├────────────────────────────┤
│ [Avatar] Pavan · Admin     │  ← User info (role-aware)
│ Sign out                   │
└────────────────────────────┘
```

## Adding a New Agent

In `src/components/sidebar.tsx`, add an entry to the `AGENTS` array:

```typescript
const AGENTS = [
  {
    id:    "admissions",               // unique slug
    name:  "DWPS Admissions AI",       // shown in dropdown
    icon:  GraduationCap,              // lucide-react icon
    color: "#c9a84c",                  // accent color (hex)
    nav: [
      { href: "/dashboard",     icon: LayoutDashboard, label: "Analytics"     },
      { href: "/conversations", icon: MessageSquare,   label: "Conversations" },
      { href: "/visits",        icon: CalendarCheck,   label: "Campus Visits" },
    ],
  },

  // ── Add new agents below ──────────────────────────────────────────────────
  {
    id:    "sales-research",
    name:  "Sales Research AI",
    icon:  Search,
    color: "#6366f1",
    nav: [
      { href: "/sales/dashboard", icon: LayoutDashboard, label: "Analytics" },
      { href: "/sales/leads",     icon: Users,           label: "Leads"      },
    ],
  },
];
```

## Route Convention for New Agents

Each agent should own a route prefix matching its `id`:

| Agent            | Route prefix       | Layout group                  |
|------------------|--------------------|-------------------------------|
| admissions       | `/`                | `src/app/(dashboard)/`        |
| sales-research   | `/sales/`          | `src/app/(dashboard)/sales/`  |
| hr-agent         | `/hr/`             | `src/app/(dashboard)/hr/`     |

All agent routes live inside the `(dashboard)` layout group so they share the sidebar automatically.

## Current Agents

### DWPS Admissions AI
- **Backend**: `clients/DWPS/saarthi-admissions-agent/backend`
- **Color**: `#c9a84c` (DWPS gold)
- **Pages**: Analytics · Conversations · Campus Visits

## Files

| File | Purpose |
|------|---------|
| `src/components/sidebar.tsx` | Agent registry + sidebar UI |
| `src/app/(dashboard)/layout.tsx` | Shared layout wrapping all agent pages |
| `src/hooks/use-role.ts` | Role-aware user info (admin / counselor / viewer) |
