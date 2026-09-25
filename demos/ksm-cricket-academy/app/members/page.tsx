'use client';

import { useState, useMemo } from 'react';
import { MagnifyingGlass, DownloadSimple, Funnel, UserCircle } from '@phosphor-icons/react';
import { MOCK_MEMBERS, CONSTITUENCIES, type Member } from '@/lib/data';

const PAGE_SIZE = 12;

export default function MembersPage() {
  const [constituency, setConstituency] = useState('all');
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  const filtered = useMemo(() => {
    return MOCK_MEMBERS.filter((m) => {
      const matchesZone = constituency === 'all' || m.constituency === constituency;
      const q = search.toLowerCase();
      const matchesSearch =
        !q ||
        m.name.toLowerCase().includes(q) ||
        m.village.toLowerCase().includes(q) ||
        m.district.toLowerCase().includes(q) ||
        m.membershipNo.toLowerCase().includes(q);
      return matchesZone && matchesSearch;
    });
  }, [constituency, search]);

  const totalPages = Math.ceil(filtered.length / PAGE_SIZE);
  const paged = filtered.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE);

  const handleConstituencyChange = (val: string) => { setConstituency(val); setPage(1); };
  const handleSearch = (val: string) => { setSearch(val); setPage(1); };

  const exportToExcel = async () => {
    const XLSX = await import('xlsx');
    const rows = filtered.map((m) => ({
      'Membership No.': m.membershipNo,
      Name: m.name,
      Age: m.age,
      Village: m.village,
      District: m.district,
      Constituency: CONSTITUENCIES.find((c) => c.id === m.constituency)?.name ?? m.constituency,
      Phone: m.phone,
      'Join Date': m.joinDate,
      Status: m.status,
    }));
    const ws = XLSX.utils.json_to_sheet(rows);
    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Members');
    XLSX.writeFile(wb, 'ksm-members.xlsx');
  };

  const zoneBadge: Record<string, string> = {
    north: 'border-blue-800 text-blue-400',
    south: 'border-pitch/30 text-pitch',
    east: 'border-amber-800 text-amber-400',
    west: 'border-purple-800 text-purple-400',
    central: 'border-accent/30 text-accent',
  };

  return (
    <div className="min-h-[100dvh] bg-surface pt-24 pb-16">
      <div className="max-w-7xl mx-auto px-4 sm:px-6">

        <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 mb-10">
          <div>
            <h1 className="font-display font-black text-cream uppercase text-4xl sm:text-5xl tracking-tight">
              Members
            </h1>
            <p className="text-muted text-sm mt-1">
              {filtered.length} member{filtered.length !== 1 ? 's' : ''} across 5 constituencies
            </p>
          </div>
          <button onClick={exportToExcel}
            className="inline-flex items-center gap-2 border border-border text-muted font-bold text-xs px-4 py-3 uppercase tracking-[0.12em] hover:border-cream hover:text-cream transition-colors active:scale-[0.98]">
            <DownloadSimple size={15} />
            Export Excel
          </button>
        </div>

        {/* Constituency stat tiles */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-6">
          {CONSTITUENCIES.map((c) => {
            const count = MOCK_MEMBERS.filter((m) => m.constituency === c.id).length;
            const isActive = constituency === c.id;
            return (
              <button key={c.id}
                onClick={() => handleConstituencyChange(isActive ? 'all' : c.id)}
                className={`p-4 text-left border transition-colors ${
                  isActive ? 'border-accent bg-accent/10' : 'border-border bg-elevated hover:border-subtle'
                }`}>
                <p className={`text-[10px] font-semibold uppercase tracking-[0.15em] ${isActive ? 'text-accent' : 'text-muted'}`}>
                  {c.name}
                </p>
                <p className={`font-display font-black text-3xl mt-1 ${isActive ? 'text-cream' : 'text-cream'}`}>
                  {count}
                </p>
              </button>
            );
          })}
        </div>

        {/* Search + filter */}
        <div className="bg-elevated border border-border p-4 mb-6 flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <MagnifyingGlass size={15} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted" />
            <input type="text" value={search} onChange={(e) => handleSearch(e.target.value)}
              placeholder="Search by name, village, or membership number"
              className="w-full pl-9 pr-4 py-2.5 text-xs bg-card border border-border text-cream placeholder:text-muted focus:outline-none focus:border-accent transition-colors" />
          </div>
          <div className="flex items-center gap-2">
            <Funnel size={15} className="text-muted shrink-0" />
            <select value={constituency} onChange={(e) => handleConstituencyChange(e.target.value)}
              className="border border-border bg-card text-cream text-xs px-3 py-2.5 focus:outline-none focus:border-accent transition-colors">
              <option value="all">All Constituencies</option>
              {CONSTITUENCIES.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
            </select>
          </div>
        </div>

        {/* Member cards */}
        {paged.length === 0 ? (
          <div className="bg-elevated border border-border p-16 text-center">
            <UserCircle size={36} className="text-subtle mx-auto mb-3" />
            <p className="text-muted text-sm font-semibold uppercase tracking-wide">No members found</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {paged.map((member: Member) => (
              <div key={member.id} className="bg-elevated border border-border p-5">
                <div className="flex items-start justify-between mb-4">
                  <div className="w-9 h-9 bg-subtle flex items-center justify-center font-display font-black text-cream text-sm">
                    {member.name.charAt(0)}
                  </div>
                  <span className={`text-[10px] font-bold uppercase tracking-[0.12em] px-2 py-1 border ${
                    member.status === 'active'
                      ? 'border-pitch/30 text-pitch'
                      : 'border-border text-muted'
                  }`}>
                    {member.status}
                  </span>
                </div>

                <h3 className="font-display font-bold text-cream text-lg uppercase tracking-tight mb-0.5">
                  {member.name}
                </h3>
                <p className="text-[11px] text-muted uppercase tracking-[0.12em] mb-4">{member.membershipNo}</p>

                <div className="space-y-1.5 text-xs">
                  {[
                    ['Village', member.village],
                    ['District', member.district],
                    ['Age', `${member.age} yrs`],
                    ['Joined', new Date(member.joinDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })],
                  ].map(([label, value]) => (
                    <div key={label} className="flex justify-between">
                      <span className="text-muted uppercase tracking-[0.1em]">{label}</span>
                      <span className="text-cream">{value}</span>
                    </div>
                  ))}
                </div>

                <div className="mt-4 pt-4 border-t border-border">
                  <span className={`text-[10px] font-bold uppercase tracking-[0.12em] px-2 py-1 border ${
                    zoneBadge[member.constituency] ?? 'border-border text-muted'
                  }`}>
                    {CONSTITUENCIES.find((c) => c.id === member.constituency)?.name}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex items-center justify-center gap-3 mt-8">
            <button onClick={() => setPage((p) => Math.max(1, p - 1))} disabled={page === 1}
              className="px-4 py-2 text-xs border border-border text-muted hover:text-cream hover:border-cream transition-colors disabled:opacity-30 disabled:cursor-not-allowed uppercase tracking-[0.1em] font-semibold">
              Previous
            </button>
            <span className="text-xs text-muted uppercase tracking-[0.1em]">
              {page} / {totalPages}
            </span>
            <button onClick={() => setPage((p) => Math.min(totalPages, p + 1))} disabled={page === totalPages}
              className="px-4 py-2 text-xs border border-border text-muted hover:text-cream hover:border-cream transition-colors disabled:opacity-30 disabled:cursor-not-allowed uppercase tracking-[0.1em] font-semibold">
              Next
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
