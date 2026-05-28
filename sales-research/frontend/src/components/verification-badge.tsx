import React from 'react';
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertCircle, HelpCircle, Mail } from "lucide-react";

interface VerificationBadgeProps {
  status: string | null | undefined;
  size?: 'sm' | 'md';
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({ status, size = 'md' }) => {
  if (!status) return null;

  const normalizedStatus = status.toLowerCase();
  const isSm = size === 'sm';
  const badgeClasses = `gap-1.5 ${isSm ? 'py-0.5 px-2 text-[10px]' : 'py-1 px-3'}`;
  const iconSize = isSm ? 'w-3 h-3' : 'w-3.5 h-3.5';

  if (normalizedStatus === 'verified' || normalizedStatus === 'deliverable') {
    return (
      <Badge variant="secondary" className={`bg-emerald-500/10 text-emerald-500 border-emerald-500/20 font-bold ${badgeClasses}`}>
        <CheckCircle2 className={iconSize} />
        Verified
      </Badge>
    );
  }

  if (normalizedStatus === 'undeliverable' || normalizedStatus === 'invalid') {
    return (
      <Badge variant="secondary" className={`bg-rose-500/10 text-rose-500 border-rose-500/20 font-bold ${badgeClasses}`}>
        <AlertCircle className={iconSize} />
        Undeliverable
      </Badge>
    );
  }

  if (normalizedStatus === 'risky' || normalizedStatus === 'catch-all') {
    return (
      <Badge variant="secondary" className={`bg-amber-500/10 text-amber-500 border-amber-500/20 font-bold ${badgeClasses}`}>
        <Mail className={iconSize} />
        Risky
      </Badge>
    );
  }

  return (
    <Badge variant="secondary" className={`bg-slate-500/10 text-slate-500 border-slate-500/20 font-bold ${badgeClasses}`}>
      <HelpCircle className={iconSize} />
      {status}
    </Badge>
  );
};
