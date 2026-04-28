import React from 'react';
import { Badge } from "@/components/ui/badge";
import { CheckCircle2, AlertCircle, HelpCircle, Mail } from "lucide-react";

interface VerificationBadgeProps {
  status: string | null | undefined;
}

export const VerificationBadge: React.FC<VerificationBadgeProps> = ({ status }) => {
  if (!status) return null;

  const normalizedStatus = status.toLowerCase();

  if (normalizedStatus === 'verified' || normalizedStatus === 'deliverable') {
    return (
      <Badge variant="secondary" className="bg-emerald-500/10 text-emerald-500 border-emerald-500/20 gap-1.5 py-1">
        <CheckCircle2 className="w-3.5 h-3.5" />
        Verified
      </Badge>
    );
  }

  if (normalizedStatus === 'undeliverable' || normalizedStatus === 'invalid') {
    return (
      <Badge variant="secondary" className="bg-rose-500/10 text-rose-500 border-rose-500/20 gap-1.5 py-1">
        <AlertCircle className="w-3.5 h-3.5" />
        Undeliverable
      </Badge>
    );
  }

  if (normalizedStatus === 'risky' || normalizedStatus === 'catch-all') {
    return (
      <Badge variant="secondary" className="bg-amber-500/10 text-amber-500 border-amber-500/20 gap-1.5 py-1">
        <Mail className="w-3.5 h-3.5" />
        Risky
      </Badge>
    );
  }

  return (
    <Badge variant="secondary" className="bg-slate-500/10 text-slate-500 border-slate-500/20 gap-1.5 py-1">
      <HelpCircle className="w-3.5 h-3.5" />
      {status}
    </Badge>
  );
};
