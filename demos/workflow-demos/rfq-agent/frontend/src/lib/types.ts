export type RFQStatus = "processing" | "dispatched" | "pending_review" | "failed" | "approved" | "rejected";
export type RFQType = "product" | "freight";

export interface RFQListItem {
  rfq_id: string;
  created_at: string;
  dispatched_at?: string | null;
  source: string;
  sender: string;
  email_id?: string | null;
  buyer_name: string | null;
  urgency: string | null;
  category: string | null;
  rfq_type: RFQType | null;
  total: number | null;
  pricing_confidence: number | null;
  status: RFQStatus;
}

export interface LineItem {
  description: string;
  quantity: number | null;
  unit: string | null;
  specs: string | null;
}

export interface LinePrice {
  line_item_index: number;
  unit_price: number;
  quantity: number;
  subtotal: number;
  discount_pct: number;
  rush_premium_pct: number;
  notes: string | null;
}

export interface RFQDetail extends RFQListItem {
  email_id?: string | null;
  subject: string | null;
  buyer_contact: string | null;
  delivery_location: string | null;
  rfq_deadline: string | null;
  complexity: string | null;
  line_items: LineItem[] | null;
  line_pricing: LinePrice[] | null;
  catalog_matches: Record<string, unknown>[] | null;
  feasibility: Record<string, unknown>[] | null;
  unfulfillable_items: number[] | null;
  subtotal: number | null;
  pricing_confidence: number | null;
  draft_quote: string | null;
  review_notes: string | null;
  error: string | null;
  freight_origin: string | null;
  freight_destination: string | null;
  freight_cargo_desc: string | null;
  freight_weight_kg: number | null;
  freight_volume_cbm: number | null;
  freight_truck_type: string | null;
  freight_distance_km: number | null;
  freight_quote_amount: number | null;
}

export interface RFQListResponse {
  items: RFQListItem[];
  total: number;
  page: number;
  limit: number;
}

export interface StatsResponse {
  total: number;
  dispatched: number;
  pending_review: number;
  processing: number;
  failed: number;
  total_value: number;
}

export interface EmailSummary {
  id: string;
  subject: string;
  from_name: string;
  from_email: string;
  date: string;
  date_iso: string;
  unread: boolean;
  size_kb: number;
  tag: string;
  preview: string;
}

export interface EmailAttachment {
  filename: string;
  size_kb: number;
  content_type: string;
}

export interface EmailDetail extends EmailSummary {
  body: string;
  attachments: EmailAttachment[];
  thread_id?: string | null;
  thread_messages?: EmailDetail[];
  rfq?: {
    rfq_id: string;
    status: string;
    total: number | null;
    draft_quote: string | null;
  } | null;
}

export interface UploadResponse {
  rfq_id: string;
  status: RFQStatus;
  total: number | null;
  pricing_confidence: number | null;
  line_items_count: number;
  draft_quote: string | null;
  review_notes: string | null;
  rfq_type: RFQType | null;
}
