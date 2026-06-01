// ── Auth ──────────────────────────────────────────────────────────────────────

export interface TokenResponse {
  access_token: string;
  token_type: string;
  role: "user" | "admin";
}

export interface UserInfo {
  id: string;
  email: string;
  display_name: string;
  role: "user" | "admin";
  created_at: string;
}

// ── Products / Analytics ──────────────────────────────────────────────────────

export interface TopProduct {
  rank: number;
  product_id: string;
  product_name: string;
  brand: string;
  category: string;
  bayesian_score: number;
  controversy_label: "high" | "medium" | "low";
  total_mentions: number;
  positive_pct: number;
  negative_pct: number;
  top_aspect: string | null;
}

export interface AspectSentiment {
  aspect_label: string;
  positive_count: number;
  negative_count: number;
  neutral_count: number;
  total_mentions: number;
  positive_pct: number;
  negative_pct: number;
}

export interface ProductDetail {
  product_id: string;
  product_name: string;
  brand: string;
  category: string;
  bayesian_score: number;
  controversy_label: string;
  total_mentions: number;
  aspects: AspectSentiment[];
  as_of_date: string;
}

export interface CausalEventSummary {
  product_name: string;
  change_point_date: string;
  sentiment_direction: "POSITIVE" | "NEGATIVE";
  event_video_title: string;
  event_view_count: number;
  explanation_text: string;
}

export interface AttributionData {
  product_id: string;
  product_name: string;
  events: CausalEventSummary[];
}

export interface SearchResultItem {
  product_id: string;
  product_name: string;
  brand: string;
  category: string;
  bayesian_score: number;
  controversy_label: string;
  total_mentions: number;
}

export interface SearchResponse {
  results: SearchResultItem[];
  total: number;
  query: string;
}

// ── Dashboard (Admin) ─────────────────────────────────────────────────────────

export interface CategoryStat {
  category: string;
  label: string;
  mention_count: number;
  week_change_pct: number;
}

export interface UserDashboardData {
  category_stats: CategoryStat[];
  top_products: TopProduct[];
  latest_causal_events: CausalEventSummary[];
  as_of_date: string;
}

export interface DagRunSummary {
  dag_id: string;
  run_id: string;
  state: "success" | "failed" | "running" | "queued";
  start_date: string | null;
  duration_seconds: number | null;
}

export interface PipelineStatus {
  airflow_webserver: "healthy" | "unhealthy" | "unknown";
  airflow_scheduler: "healthy" | "unhealthy" | "unknown";
  quota_used_today: number;
  quota_limit: number;
  last_nlp_batch_run_id: string | null;
  nlp_fallback_pct: number | null;
}

export interface QuickStat {
  videos_today: number;
  comments_today: number;
  products_tracked: number;
  active_channels: number;
  active_keywords: number;
}

export interface AttentionItem {
  level: "warning" | "info";
  message: string;
}

export interface AdminDashboardData {
  pipeline_status: PipelineStatus;
  quick_stats: QuickStat;
  recent_dag_runs: DagRunSummary[];
  attention_items: AttentionItem[];
  as_of_date: string;
}

// ── Admin Config ──────────────────────────────────────────────────────────────

export interface ChannelConfigItem {
  channel_id: string;
  channel_name: string;
  channel_url: string | null;
  channel_handle: string | null;
  subscriber_count: number | null;
  is_active: boolean;
  is_historically_scanned: boolean;
  created_at: string;
  last_updated_at: string | null;
}

export interface KeywordConfigItem {
  keyword_id: string;
  keyword_text: string;
  search_cluster: string | null;
  is_active: boolean;
  created_at: string;
  last_updated_at: string | null;
}

// ── Pipeline Health ───────────────────────────────────────────────────────────

export interface TaskInstanceDetail {
  task_id: string;
  state: string;
  duration: number | null;
  try_number: number;
}

export interface DagRunDetail {
  dag_id: string;
  run_id: string;
  state: string;
  start_date: string | null;
  duration_seconds: number | null;
  tasks: TaskInstanceDetail[];
}

export interface AirflowHealth {
  webserver: string;
  scheduler: string;
}

export interface PipelineMetrics {
  quota_used_today: number;
  quota_limit: number;
  videos_crawled_today: number;
  comments_crawled_today: number;
  channels_pending_historical: number;
  last_nlp_batch_id: string | null;
}

export interface PipelineHealthData {
  airflow: AirflowHealth;
  recent_dag_runs: DagRunDetail[];
  metrics: PipelineMetrics;
  as_of: string;
}
