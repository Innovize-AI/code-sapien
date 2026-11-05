# Phase 2 Architecture — DWPS Multi-Service Platform

## Vision

Phase 1 delivers Saarthi as a standalone WhatsApp admissions agent with a staff dashboard.
Phase 2 evolves it into a **multi-service platform** where DWPS staff log in once and see
only the tools relevant to their role — Admissions, Finance, HR, Operations, etc.

---

## Target Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                         DWPS Portal                          │
│                    (shell.dwpshyd.in)                        │
│                                                              │
│   ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│   │  Saarthi   │  │  Finance   │  │  HR / Ops  │  ...       │
│   │    Tile    │  │    Tile    │  │    Tile    │            │
│   └────────────┘  └────────────┘  └────────────┘            │
│        ↑ shown only if JWT has permission for that module    │
└──────────────────────────────────────────────────────────────┘
          │                    │                    │
          ▼                    ▼                    ▼
  saarthi.dwpshyd.in   finance.dwpshyd.in    hr.dwpshyd.in
  (Next.js, Phase 1)   (Next.js, Phase 2)   (Next.js, Phase 3)
          │                    │                    │
          ▼                    ▼                    ▼
   FastAPI :8080        FastAPI :8081        FastAPI :8082
   (Saarthi API)       (Finance API)         (HR API)
          │                    │                    │
          └────────────────────┴────────────────────┘
                               │
                    Shared PostgreSQL (Supabase)
                    Separate schema per service
```

---

## Central Auth Service

Single login at `auth.dwpshyd.in` (or Supabase Auth / Clerk).
Issues a **JWT** that every microservice independently verifies — no inter-service calls.

### JWT Payload

```json
{
  "sub": "staff_uuid",
  "name": "Priya Sharma",
  "email": "priya@dwpshyd.in",
  "org": "dwps",
  "permissions": {
    "saarthi":  ["read", "takeover", "reply", "broadcast"],
    "finance":  ["read"],
    "hr":       []
  },
  "iat": 1753000000,
  "exp": 1753086400
}
```

### Permission Actions (per module)

| Action | Description |
|--------|-------------|
| `read` | View dashboards, conversations, reports |
| `takeover` | Pause AI, enter manual mode |
| `reply` | Send manual WhatsApp replies |
| `broadcast` | Send bulk campaigns |
| `manage` | Create/edit/delete records |
| `admin` | User management, settings |

---

## Database Design

Each service owns its schema within the shared Supabase instance.

```
public schema (shared)
  └── staff            -- all staff across all services
  └── roles            -- "admissions_admin", "finance_viewer" etc.
  └── staff_roles      -- many-to-many
  └── permissions      -- role → module → actions[]

saarthi schema (Phase 1, already built)
  └── leads, sessions, conversation_logs, visits, fee_data ...

finance schema (Phase 2)
  └── invoices, payments, budgets ...

hr schema (Phase 3)
  └── employees, payroll, leaves ...
```

### Staff + Permissions Tables (add in Phase 2)

```sql
CREATE TABLE public.staff (
  id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  email      TEXT UNIQUE NOT NULL,
  name       TEXT NOT NULL,
  org_id     TEXT NOT NULL DEFAULT 'dwps',
  is_active  BOOLEAN DEFAULT true,
  created_at TIMESTAMPTZ DEFAULT now()
);

CREATE TABLE public.roles (
  id     UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name   TEXT NOT NULL,               -- "admissions_admin", "finance_viewer"
  org_id TEXT NOT NULL DEFAULT 'dwps'
);

CREATE TABLE public.permissions (
  role_id TEXT NOT NULL,
  module  TEXT NOT NULL,              -- "saarthi", "finance", "hr"
  actions TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE public.staff_roles (
  staff_id UUID REFERENCES public.staff(id),
  role_id  UUID REFERENCES public.roles(id),
  PRIMARY KEY (staff_id, role_id)
);
```

---

## Shared JWT Middleware (FastAPI)

Every microservice uses the same middleware. Extract to a shared package (`dwps-auth`).

```python
# packages/dwps_auth/middleware.py

from fastapi import Depends, HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt

bearer = HTTPBearer()

def require_permission(module: str, action: str):
    def dependency(credentials: HTTPAuthorizationCredentials = Security(bearer)):
        try:
            payload = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=["HS256"],
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            raise HTTPException(status_code=401, detail="Invalid token")

        allowed = payload.get("permissions", {}).get(module, [])
        if action not in allowed:
            raise HTTPException(status_code=403, detail=f"Missing permission: {module}:{action}")

        return payload  # downstream can use staff info from here

    return dependency
```

Usage in any service:

```python
# Saarthi
@router.post("/console/pause")
async def toggle_pause(
    req: PauseRequest,
    staff = Depends(require_permission("saarthi", "takeover")),
    db: AsyncSession = Depends(get_db),
):
    ...

# Finance (Phase 2)
@router.get("/invoices")
async def list_invoices(
    staff = Depends(require_permission("finance", "read")),
    db: AsyncSession = Depends(get_db),
):
    ...
```

---

## Shell App (Portal)

Thin Next.js app at `shell.dwpshyd.in`. After login it:

1. Decodes the JWT (client-side, no verification needed — trust the cookie)
2. Reads `permissions` to build the tile grid
3. Each tile is a link to the relevant subdomain

```tsx
// Shell reads permissions from JWT and renders only accessible modules
const MODULES = [
  { key: "saarthi",  label: "Admissions AI",     href: "https://saarthi.dwpshyd.in",  icon: GraduationCap },
  { key: "finance",  label: "Finance Dashboard",  href: "https://finance.dwpshyd.in",  icon: IndianRupee   },
  { key: "hr",       label: "HR & Payroll",       href: "https://hr.dwpshyd.in",       icon: Users         },
];

export default function Portal() {
  const { permissions } = useJWT();
  const accessible = MODULES.filter(m => permissions[m.key]?.includes("read"));

  return (
    <div className="grid grid-cols-3 gap-6">
      {accessible.map(m => <ModuleTile key={m.key} {...m} />)}
    </div>
  );
}
```

---

## Migration Path from Phase 1

Phase 1 Saarthi requires **zero changes** to support Phase 2. The migration is additive:

| Step | What changes | Phase 1 touched? |
|------|-------------|------------------|
| Add `public.staff` + `public.roles` tables | DB only | No |
| Extract JWT middleware to shared package | New package | Import only |
| Build shell/portal app | New repo | No |
| Add `supabase_jwt_secret` to each service `.env` | Already in config.py | Already there |
| New services (Finance, HR) | New repos | No |

The `supabase_jwt_secret` already in Phase 1 `config.py` becomes the **shared signing secret** across all services.

---

## Recommended Auth Provider

| Option | When to use |
|--------|-------------|
| **Supabase Auth** (current) | ≤ 3 services, ≤ 50 staff, DWPS only. Free tier, already integrated. |
| **Clerk** | Multiple schools onboarded, need SSO, org management UI, MFA out of box |
| **Auth0** | Enterprise, compliance requirements, need SAML/LDAP |

For DWPS Phase 2, **Supabase Auth** is sufficient. The `staff` table lives in Supabase,
roles are stored in `user_metadata`, and the JWT is issued by Supabase automatically.
Switch to Clerk only if you onboard other schools and need multi-tenant org management.

---

## Summary

- **Phase 1** — Saarthi standalone. Supabase Auth with simple role in `user_metadata`.
- **Phase 2** — Add shell portal + `staff/roles/permissions` tables + Finance service. JWT shared across services via `supabase_jwt_secret`.
- **Phase 3+** — New services plug in with zero changes to existing ones. Consider Clerk if multi-school.

The single design decision that makes this work: **stateless JWT with permissions embedded**.
Each service is fully independent and trusts the token — no central auth service to call at runtime.
