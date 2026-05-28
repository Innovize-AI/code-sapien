"use client";

import { useEffect, useState } from "react";
import { DashboardLayout } from "@/components/layout/dashboard-layout";
import { fetchHistory } from "@/lib/api";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import Link from "next/link";
import {
  Calendar,
  ExternalLink,
  ArrowRight,
  Globe,
  User,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
  Search,
  ShieldCheck,
  ShieldAlert,
  ShieldQuestion,
} from "lucide-react";
import { useBulkAnalysis } from "@/context/bulk-analysis-context";
import { useAuth } from "@/context/auth-context";
import { ensureProtocol } from "@/lib/utils";
import { Input } from "@/components/ui/input";
import { Spinner } from "@/components/ui/spinner"

interface HistoryItem {
  id: string;
  created_at: string;
  linkedin_url: string;
  fullname?: string;
  profile_picture_url?: string;
  website?: string;
  lead_score: number;
  rep_name?: string;
  // Optional fields for UI handling of temporary items
  status?: "pending" | "analyzing" | "completed" | "error";
  isTemporary?: boolean;
  result?: any;
  currentStep?: string;
  email_verification_status?: string;
}

const ProfileAvatar = ({
  src,
  fallbackName,
}: {
  src?: string;
  fallbackName?: string;
}) => {
  const [hasError, setHasError] = useState(false);

  if (!src || hasError) {
    return (
      <div className="h-10 w-10 rounded-full border bg-muted flex items-center justify-center overflow-hidden shrink-0">
        <User className="h-5 w-5 text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="h-10 w-10 rounded-full border bg-muted flex items-center justify-center overflow-hidden shrink-0">
      <img
        src={src}
        alt={fallbackName || "Profile"}
        className="h-full w-full object-cover"
        onError={() => setHasError(true)}
      />
    </div>
  );
};

const PAGE_SIZE = 50;

export default function HistoryPage() {
  const { user } = useAuth();
  const { leadsStatus } = useBulkAnalysis();
  const [page, setPage] = useState(0);

  const [historyItems, setHistoryItems] = useState<HistoryItem[]>([]);
  const [totalItems, setTotalItems] = useState(0);
  const [loading, setLoading] = useState(true);
  const [sortBy, setSortBy] = useState<string>("created_at");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("all");

  const renderEmailVerificationBadge = (status?: string) => {
    if (!status) return null;
    const s = status.toLowerCase();
    switch (s) {
      case "verified":
      case "ok":
      case "valid":
        return (
          <Badge
            variant="outline"
            className="text-[9px] h-4 px-1.5 bg-emerald-50 text-emerald-700 border-emerald-200 flex items-center gap-1"
          >
            <ShieldCheck className="w-2.5 h-2.5" />
            Verified
          </Badge>
        );
      case "unverified":
      case "invalid":
      case "error":
      case "failed":
        return (
          <Badge
            variant="outline"
            className="text-[9px] h-4 px-1.5 bg-red-600 text-white border-red-700 flex items-center gap-1 font-bold shadow-sm"
          >
            <ShieldAlert className="w-2.5 h-2.5" />
            {s === "invalid" ? "Invalid" : "Error"}
          </Badge>
        );
      case "catch_all":
      case "catchall":
      case "risky":
        return (
          <Badge
            variant="outline"
            className="text-[9px] h-4 px-1.5 bg-amber-100 text-amber-700 border-amber-300 flex items-center gap-1 font-bold"
          >
            <ShieldAlert className="w-2.5 h-2.5" />
            Risky
          </Badge>
        );
      default:
        return (
          <Badge
            variant="outline"
            className="text-[9px] h-4 px-1.5 bg-gray-50 text-gray-600 border-gray-200 flex items-center gap-1"
          >
            <ShieldQuestion className="w-2.5 h-2.5" />
            {s.charAt(0).toUpperCase() + s.slice(1)}
          </Badge>
        );
    }
  };

  const toggleSort = (column: string) => {
    if (sortBy === column) {
      setSortOrder(sortOrder === "asc" ? "desc" : "asc");
    } else {
      setSortBy(column);
      setSortOrder("desc");
    }
    setPage(0);
  };

  const SortButton = ({
    column,
    label,
  }: {
    column: string;
    label: string | React.ReactNode;
  }) => {
    const isActive = sortBy === column;
    return (
      <button
        onClick={() => toggleSort(column)}
        className={`flex items-center gap-1 hover:text-primary transition-colors ${
          isActive ? "text-primary font-bold" : ""
        }`}
      >
        {label}
        {isActive ? (
          sortOrder === "asc" ? (
            <ArrowUp className="w-3 h-3" />
          ) : (
            <ArrowDown className="w-3 h-3" />
          )
        ) : (
          <ArrowUpDown className="w-3 h-3 opacity-30" />
        )}
      </button>
    );
  };

  useEffect(() => {
    const timeoutId = setTimeout(() => {
      async function loadHistory() {
        setLoading(true);
        try {
          const skip = page * PAGE_SIZE;
          const data = await fetchHistory(
            skip,
            PAGE_SIZE,
            searchQuery,
            statusFilter,
            sortBy,
            sortOrder,
          );
          setHistoryItems(data.items || []);
          setTotalItems(data.total || 0);
        } catch (err) {
          console.error("Failed to fetch history", err);
        } finally {
          setLoading(false);
        }
      }
      loadHistory();
    }, 500); // Debounce search

    return () => clearTimeout(timeoutId);
  }, [page, sortBy, sortOrder, searchQuery, statusFilter]);

  // Merge history with temporary bulk analysis items (only on first page for simplicity)
  const displayHistory: HistoryItem[] = [
    ...(page === 0
      ? leadsStatus.map((lead) => ({
          id: `temp-${lead.url}`,
          created_at: new Date().toISOString(),
          linkedin_url: lead.url,
          lead_score: lead.result?.lead_score || 0,
          rep_name: user?.full_name || "You",
          status: lead.status,
          isTemporary: true,
          result: lead.result,
          currentStep: lead.currentStep,
        }))
      : []),
    ...historyItems,
  ];

  return (
    <DashboardLayout>
      <div className="flex flex-col gap-8">
        <div>
          <h1 className="text-3xl font-bold tracking-tight">
            Research History
          </h1>
          <p className="text-muted-foreground mt-2">
            View past lead analyses and reports.
          </p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Recent Reports</CardTitle>
            <CardDescription>
              A list of all generated sales research reports.
            </CardDescription>
            <div className="mt-4 flex flex-col sm:flex-row gap-3">
              <div className="relative flex-1 max-w-md">
                <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
                <Input
                  type="search"
                  placeholder="Search by name, company, or website..."
                  className="pl-9 h-10"
                  value={searchQuery}
                  onChange={(e) => {
                    setSearchQuery(e.target.value);
                    setPage(0);
                  }}
                />
              </div>
              <Select
                value={statusFilter}
                onValueChange={(val) => {
                  setStatusFilter(val);
                  setPage(0);
                }}
              >
                <SelectTrigger className="w-[180px] h-10 bg-background/50 border-primary/10">
                  <SelectValue placeholder="All Reports" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Global History</SelectItem>
                  {user && <SelectItem value={user.id}>My Reports</SelectItem>}
                </SelectContent>
              </Select>
            </div>
          </CardHeader>
          <CardContent>
            {loading && historyItems.length === 0 ? (
              <div className="flex justify-center p-8">
                <span className="animate-spin h-6 w-6 border-2 border-primary border-t-transparent rounded-full"></span>
              </div>
            ) : displayHistory.length === 0 ? (
              <div className="text-center p-8 text-muted-foreground">
                No reports found. Generate your first lead analysis!
              </div>
            ) : (
              <>
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>
                        <SortButton column="created_at" label="Date" />
                      </TableHead>
                      <TableHead>
                        <SortButton column="rep_name" label="Representative" />
                      </TableHead>
                      <TableHead>
                        <SortButton column="fullname" label="Profile" />
                      </TableHead>
                      <TableHead>
                        <SortButton column="lead_score" label="Lead Score" />
                      </TableHead>
                      <TableHead className="text-right">Action</TableHead>
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {displayHistory.map((item) => (
                      <TableRow
                        key={item.id}
                        className={item.isTemporary ? "bg-muted/30" : ""}
                      >
                        <TableCell className="font-medium flex items-center gap-2">
                          <Calendar className="h-4 w-4 text-muted-foreground" />
                          {new Date(item.created_at).toLocaleDateString()}
                          {item.isTemporary && (
                            <Badge
                              variant="outline"
                              className="ml-2 text-xs h-5"
                            >
                              {item.status === "analyzing"
                                ? "Processing"
                                : "Unsaved"}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell>
                          <Badge
                            variant="outline"
                            className="text-[10px] font-normal"
                          >
                            {item.rep_name || "System"}
                          </Badge>
                        </TableCell>
                        <TableCell>
                          <div className="flex items-center gap-3">
                            <ProfileAvatar
                              src={item.profile_picture_url}
                              fallbackName={item.fullname}
                            />
                            <div className="flex flex-col">
                              <div className="flex items-center gap-2">
                                <span className="font-bold text-sm">
                                  {item.fullname || "Anonymous"}
                                </span>
                                {renderEmailVerificationBadge(item.email_verification_status)}
                              </div>
                              <div className="flex flex-wrap items-center gap-2 mt-0.5">
                                <a
                                  href={item.linkedin_url}
                                  target="_blank"
                                  rel="noopener noreferrer"
                                  className="text-[10px] text-blue-600 hover:underline flex items-center gap-1"
                                >
                                  LinkedIn{" "}
                                </a>
                                {item.website && (
                                  <a
                                    href={ensureProtocol(item.website)}
                                    target="_blank"
                                    rel="noopener noreferrer"
                                    className="text-[10px] text-emerald-600 hover:underline flex items-center gap-1"
                                  >
                                    Website <Globe className="h-2.5 w-2.5" />
                                  </a>
                                )}
                                {item.email_verification_status && (
                                  <Badge 
                                    variant="outline" 
                                    className={`text-[9px] h-4 px-1 flex items-center gap-0.5 border-none ${
                                      item.email_verification_status === 'verified' ? 'text-emerald-600 bg-emerald-50' : 
                                      item.email_verification_status === 'invalid' ? 'text-rose-600 bg-rose-50' : 
                                      'text-amber-600 bg-amber-50'
                                    }`}
                                  >
                                    {item.email_verification_status === 'verified' && <ShieldCheck className="h-2.5 w-2.5" />}
                                    {item.email_verification_status === 'invalid' && <ShieldAlert className="h-2.5 w-2.5" />}
                                    {['catchall', 'unknown', 'disposable'].includes(item.email_verification_status) && <ShieldQuestion className="h-2.5 w-2.5" />}
                                    {item.email_verification_status.charAt(0).toUpperCase() + item.email_verification_status.slice(1)}
                                  </Badge>
                                )}
                              </div>
                            </div>
                          </div>
                        </TableCell>
                        <TableCell>
                          {item.status === "analyzing" ||
                          item.status === "pending" ? (
                            <div className="flex items-center gap-2 text-muted-foreground text-sm">
                              <Spinner size="sm" />
                              <span
                                className="truncate max-w-[150px]"
                                title={item.currentStep || "Analyzing..."}
                              >
                                {item.currentStep || "Analyzing..."}
                              </span>
                            </div>
                          ) : (
                            <Badge
                              variant={
                                item.lead_score > 70 ? "default" : "secondary"
                              }
                            >
                              {item.lead_score}
                            </Badge>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {item.isTemporary ? (
                            item.status === "completed" && item.result?.id ? (
                              <Link href={`/reports?id=${item.result.id}`}>
                                <span className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3">
                                  View Report{" "}
                                  <ArrowRight className="ml-2 h-4 w-4" />
                                </span>
                              </Link>
                            ) : item.status === "completed" ? (
                              <span className="text-xs text-muted-foreground">
                                ID missing - Check Find Leads
                              </span>
                            ) : (
                              <span className="text-xs text-muted-foreground">
                                {item.status === "error"
                                  ? "Failed"
                                  : "Processing..."}
                              </span>
                            )
                          ) : (
                            <Link href={`/reports?id=${item.id}`}>
                              <span className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-9 px-3">
                                View Report{" "}
                                <ArrowRight className="ml-2 h-4 w-4" />
                              </span>
                            </Link>
                          )}
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>

                {/* Pagination Controls */}
                <div className="flex items-center justify-between space-x-2 py-4 border-t px-2">
                  <div className="text-sm text-muted-foreground">
                    Showing {page * PAGE_SIZE + 1} to{" "}
                    {Math.min((page + 1) * PAGE_SIZE, totalItems)} of{" "}
                    {totalItems} reports
                  </div>
                  <div className="flex items-center space-x-2">
                    <button
                      onClick={() => setPage((p) => Math.max(0, p - 1))}
                      disabled={page === 0 || loading}
                      className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-40 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-3"
                    >
                      Previous
                    </button>
                    <div className="text-sm font-medium">Page {page + 1}</div>
                    <button
                      onClick={() => setPage((p) => p + 1)}
                      disabled={(page + 1) * PAGE_SIZE >= totalItems || loading}
                      className="inline-flex items-center justify-center rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-40 border border-input bg-background hover:bg-accent hover:text-accent-foreground h-8 px-3"
                    >
                      Next
                    </button>
                  </div>
                </div>
              </>
            )}
          </CardContent>
        </Card>
      </div>
    </DashboardLayout>
  );
}
