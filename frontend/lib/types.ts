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

export interface CategoryStat {
  category: string;
  label: string;
  mention_count: number;
  week_change_pct: number;
}

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

export interface CausalEventSummary {
  product_name: string;
  change_point_date: string;
  sentiment_direction: "POSITIVE" | "NEGATIVE";
  event_video_title: string;
  event_view_count: number;
  explanation_text: string;
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
