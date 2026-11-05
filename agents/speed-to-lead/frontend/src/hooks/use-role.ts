"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase";
import type { User } from "@supabase/supabase-js";

export type Role = "admin" | "counselor" | "viewer" | "agent";

interface StaffSession {
  name: string;
  email: string;
  role: Role;
  firmId: string | null;
  personId: string | null;
  permissions: Record<string, string[]>;
}

const EMPTY: StaffSession = {
  name: "",
  email: "",
  role: "viewer",
  firmId: null,
  personId: null,
  permissions: {},
};

function sessionFromUser(user: User): StaffSession {
  const meta = user.user_metadata ?? {};
  return {
    name:        meta.name        ?? user.email ?? "",
    email:       user.email       ?? "",
    role:        meta.role        ?? "viewer",
    firmId:      meta.firm_id     ?? null,
    personId:    meta.person_id   ?? null,
    permissions: meta.permissions ?? {},
  };
}

export function useRole() {
  const [session, setSession] = useState<StaffSession>(EMPTY);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const sb = createClient();

    // Prime from current session without a round-trip
    sb.auth.getSession().then(({ data }) => {
      const user = data.session?.user;
      if (user) setSession(sessionFromUser(user));
      setLoading(false);
    });

    // Keep in sync: use the user from the event, no extra getUser() call
    const { data: listener } = sb.auth.onAuthStateChange((_event, authSession) => {
      if (authSession?.user) {
        setSession(sessionFromUser(authSession.user));
      } else {
        setSession(EMPTY);
      }
      setLoading(false);
    });

    return () => listener.subscription.unsubscribe();
  }, []);

  const can = (module: string, action: string): boolean =>
    session.permissions[module]?.includes(action) ?? false;

  return { ...session, can, loading };
}
