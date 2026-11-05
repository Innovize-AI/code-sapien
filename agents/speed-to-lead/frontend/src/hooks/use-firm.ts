"use client";

import { useEffect, useState, useCallback } from "react";
import useSWR from "swr";
import { fetchFirm, fetchFirms } from "@/lib/api";
import type { Firm } from "@/types";
import { useRole } from "./use-role";

const STORE_KEY = "stl-active-firm";

function readStored(): string | null {
  try {
    return window.localStorage.getItem(STORE_KEY);
  } catch {
    return null;
  }
}

function writeStored(id: string) {
  try {
    window.localStorage.setItem(STORE_KEY, id);
  } catch {
    /* storage can be blocked, the choice just won't persist */
  }
}

export function useFirm() {
  const { role, firmId: metaFirmId, loading: roleLoading } = useRole();
  const isAdmin = role === "admin";

  // Demo mode: a signed-in user without a firm in their metadata (or local runs with auth
  // bypassed) picks a firm from the list. Real staff are locked to their own firm.
  const demoMode = !roleLoading && !metaFirmId && !isAdmin;

  // Admins can switch firms; staff are locked to their firm from metadata
  const [activeFirmId, setActiveFirmId] = useState<string | null>(null);

  const { data: allFirmsRaw } = useSWR<Firm[]>(
    isAdmin || demoMode ? "all-firms" : null,
    fetchFirms,
  );

  useEffect(() => {
    if (roleLoading || activeFirmId) return;
    if (metaFirmId) {
      setActiveFirmId(metaFirmId);
    } else if (demoMode && allFirmsRaw && allFirmsRaw.length > 0) {
      const stored = readStored();
      const pick =
        allFirmsRaw.find(f => f.id === stored) ??
        allFirmsRaw.find(f => f.vertical === "real_estate" && f.is_active) ??
        allFirmsRaw[0];
      setActiveFirmId(pick.id);
    }
  }, [roleLoading, metaFirmId, activeFirmId, demoMode, allFirmsRaw]);

  const { data: firm, isLoading: firmLoading } = useSWR<Firm>(
    activeFirmId ? `firm-${activeFirmId}` : null,
    () => fetchFirm(activeFirmId!),
  );

  const switchFirm = useCallback(
    (id: string) => {
      if (isAdmin || demoMode) {
        setActiveFirmId(id);
        writeStored(id);
      }
    },
    [isAdmin, demoMode],
  );

  return {
    firm,
    firmId: activeFirmId,
    allFirms: isAdmin || demoMode ? (allFirmsRaw ?? []) : [],
    isAdmin,
    demoMode,
    loading: roleLoading || firmLoading,
    switchFirm,
  };
}
