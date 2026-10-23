// Admin review queue for the public X account (/api/v1/admin/social).
export type SocialPostStatus = 'draft' | 'approved' | 'posted' | 'rejected' | 'failed' | 'skipped';

export interface SocialPost {
  id: string;
  platform: string;
  kind: 'trade' | 'rollup' | 'digest' | 'weekly';
  status: SocialPostStatus;
  score: number;
  reasons: string[];
  text: string;
  x_length: number;
  thread: string[];
  link_url: string | null;
  image_url: string | null;
  member_id: string | null;
  external_id: string | null;
  external_url: string | null;
  error: string | null;
  created_at: string | null;
  approved_at: string | null;
  posted_at: string | null;
  trade_ids: string[];
}

export interface SocialStatus {
  mode: 'review' | 'auto';
  x_enabled: boolean;
  daily_cap: number;
  window_utc: string;
  posted_24h: number;
  counts: Record<SocialPostStatus, number>;
}
