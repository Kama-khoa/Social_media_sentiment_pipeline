import argparse
import hashlib
import logging
import sys
from datetime import date, datetime, timezone
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from google import genai
from google.cloud import bigquery
import numpy as np
import pandas as pd
import ruptures as rpt

from elt.config import load_config
from nlp.gemini_gateway import GeminiGateway
from pipeline_progress import progress_bar

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger("pelt_attribution")

_MIN_VIRAL_VIEWS = 10_000
_MAX_INTERPOLATION_GAP_DAYS = 10
_MIN_COVERAGE = 0.30


class PELTAttribution:
    def __init__(self, config=None, bq_client=None, genai_client=None):
        self.config = config or load_config()
        self.project_id = self.config.gcp.project_id
        self.dataset = self.config.gcp.dataset
        self.marts_dataset = f"{self.dataset}_marts"
        self.bq_client = bq_client or bigquery.Client(project=self.project_id)
        self._genai_client = genai_client
        self._gemini_gateway = None

    @property
    def genai_client(self):
        if self._genai_client is None:
            self._genai_client = genai.Client(api_key=self.config.gemini_api_key)
        return self._genai_client

    @property
    def gemini_gateway(self):
        if self._gemini_gateway is None:
            self._gemini_gateway = GeminiGateway(
                api_key=self.config.gemini_api_key,
                client=self.genai_client,
            )
        return self._gemini_gateway

    def fetch_sentiment_timeseries(self) -> pd.DataFrame:
        query = f"""
            SELECT
                f.mention_date AS ranking_date,
                f.product_id,
                p.product_name,
                p.category,
                COUNT(*) AS total_mentions,
                COUNTIF(UPPER(f.sentiment_label) = 'POSITIVE') AS positive_count,
                COUNTIF(UPPER(f.sentiment_label) = 'NEGATIVE') AS negative_count,
                COUNTIF(UPPER(f.sentiment_label) = 'NEUTRAL') AS neutral_count,
                AVG(CASE
                    WHEN UPPER(f.sentiment_label) = 'POSITIVE' THEN 1.0
                    WHEN UPPER(f.sentiment_label) = 'NEGATIVE' THEN -1.0
                    ELSE 0.0
                END) AS avg_sentiment
            FROM `{self.project_id}.{self.marts_dataset}.fact_product_mentions` f
            JOIN `{self.project_id}.{self.marts_dataset}.dim_products` p
              ON f.product_id = p.product_id
            WHERE p.is_active = TRUE
              AND f.aspect_label != 'NONE'
            GROUP BY 1, 2, 3, 4
            ORDER BY f.product_id, f.mention_date ASC
        """
        return self.bq_client.query(query).to_dataframe()

    def fetch_sentiment_timeseries_by_product_id(self, product_id: str) -> pd.DataFrame:
        query = f"""
            SELECT
                f.mention_date AS ranking_date,
                f.product_id,
                p.product_name,
                p.category,
                COUNT(*) AS total_mentions,
                COUNTIF(UPPER(f.sentiment_label) = 'POSITIVE') AS positive_count,
                COUNTIF(UPPER(f.sentiment_label) = 'NEGATIVE') AS negative_count,
                COUNTIF(UPPER(f.sentiment_label) = 'NEUTRAL') AS neutral_count,
                AVG(CASE
                    WHEN UPPER(f.sentiment_label) = 'POSITIVE' THEN 1.0
                    WHEN UPPER(f.sentiment_label) = 'NEGATIVE' THEN -1.0
                    ELSE 0.0
                END) AS avg_sentiment
            FROM `{self.project_id}.{self.marts_dataset}.fact_product_mentions` f
            JOIN `{self.project_id}.{self.marts_dataset}.dim_products` p
              ON f.product_id = p.product_id
            WHERE p.is_active = TRUE
              AND f.aspect_label != 'NONE'
              AND f.product_id = @product_id
            GROUP BY 1, 2, 3, 4
            ORDER BY f.product_id, f.mention_date ASC
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id)
        ])
        return self.bq_client.query(query, job_config=job_config).to_dataframe()

    def prepare_product_timeseries(
        self,
        product_df: pd.DataFrame,
        min_points: int = 10,
        min_coverage: float = _MIN_COVERAGE,
    ) -> pd.DataFrame | None:
        if product_df.empty:
            return None

        prepared = product_df.copy()
        prepared["ranking_date"] = pd.to_datetime(prepared["ranking_date"])
        prepared = prepared.sort_values("ranking_date").set_index("ranking_date")
        full_index = pd.date_range(prepared.index.min(), prepared.index.max(), freq="D")
        prepared = prepared.reindex(full_index)

        observed_points = int(prepared["avg_sentiment"].notna().sum())
        coverage = observed_points / len(prepared)
        if observed_points < min_points:
            logger.info("Skipping time series: only %d observed days, need %d.", observed_points, min_points)
            return None
        if coverage < min_coverage:
            logger.info("Skipping time series: coverage %.1f%% is below %.1f%%.", coverage * 100, min_coverage * 100)
            return None

        # Sử dụng ffill() (Forward Fill) để điền các ngày trống kéo dài
        prepared["avg_sentiment"] = prepared["avg_sentiment"].interpolate(
            method="linear",
            limit=_MAX_INTERPOLATION_GAP_DAYS,
            limit_area="inside",
        ).ffill().bfill()
        if prepared["avg_sentiment"].isna().any():
            logger.info("Skipping time series: it contains a gap longer than %d days.", _MAX_INTERPOLATION_GAP_DAYS)
            return None

        prepared.index.name = "ranking_date"
        return prepared.reset_index()

    def run_attribution(
        self,
        min_points: int = 10,
        penalty: float = 3.0,
        amplitude_threshold: float = 0.25,
        min_coverage: float = _MIN_COVERAGE,
        dry_run: bool = False,
        product_id: str | None = None,
    ) -> None:
        if product_id:
            df = self.fetch_sentiment_timeseries_by_product_id(product_id)
        else:
            df = self.fetch_sentiment_timeseries()

        if df.empty:
            logger.warning("No valid daily product sentiment data found.")
            return

        product_ids = df["product_id"].unique()
        for product_id in progress_bar(product_ids, desc="PELT attribution", unit="product"):
            source_df = df[df["product_id"] == product_id].copy()
            product_name = source_df["product_name"].iloc[0]
            product_df = self.prepare_product_timeseries(source_df, min_points, min_coverage)
            if product_df is None:
                logger.info("Skipping product %s: readiness gate not met.", product_id)
                continue

            points = product_df["avg_sentiment"].to_numpy(dtype=np.float64)
            try:
                change_indices = rpt.Pelt(model="rbf").fit(points).predict(pen=penalty)
            except Exception as exc:
                logger.error("Error running PELT for product %s: %s", product_id, exc)
                continue

            for idx in change_indices:
                if idx >= len(points):
                    continue

                mean_before = product_df.iloc[max(0, idx - 7):idx]["avg_sentiment"].mean()
                mean_after = product_df.iloc[idx:min(len(points), idx + 7)]["avg_sentiment"].mean()
                amplitude = mean_after - mean_before
                if abs(amplitude) <= amplitude_threshold:
                    continue

                direction = "POSITIVE" if amplitude > 0 else "NEGATIVE"
                change_date = product_df.iloc[idx]["ranking_date"].date()
                logger.info(
                    "Detected change point for %s on %s: %s (amplitude: %.2f)",
                    product_name,
                    change_date,
                    direction,
                    amplitude,
                )
                self._attribute_event(product_id, product_name, change_date, direction, dry_run=dry_run)

    def _attribute_event(
        self,
        product_id: str,
        product_name: str,
        change_date: date,
        direction: str,
        dry_run: bool = False,
    ) -> None:
        videos = self._query_videos_in_window(product_id, change_date)
        if not videos:
            logger.info("No viral video candidate for %s on %s. Using natural attribution fallback.", product_name, change_date)
            videos = [{
                "video_id": "N/A",
                "title": "Biến động thảo luận tự nhiên (Không tìm thấy video review có tương tác cao tương ứng)",
                "view_count": 0,
                "published_at": change_date.isoformat()
            }]

        change_dir_val = 1.0 if direction == "POSITIVE" else -1.0
        scored_videos = []
        for video in videos:
            published_at = video["published_at"]
            if isinstance(published_at, str):
                pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00")).date()
            elif isinstance(published_at, datetime):
                pub_date = published_at.date()
            else:
                pub_date = published_at

            days_diff = abs((pub_date - change_date).days)
            temporal_proximity = max(0.0, 1.0 - days_diff / 7.0)
            
            if video["video_id"] == "N/A":
                video_sentiment = 0.0
            else:
                video_sentiment = self._query_video_sentiment(product_id, video["video_id"])
                
            if video_sentiment * change_dir_val > 0:
                direction_alignment = 1.0
            elif video_sentiment == 0.0:
                direction_alignment = 0.5
            else:
                direction_alignment = 0.0

            scored_videos.append({
                **video,
                "temporal_proximity": temporal_proximity,
                "direction_alignment": direction_alignment,
                "attribution_score": temporal_proximity * 0.5 + direction_alignment * 0.5,
            })

        scored_videos.sort(key=lambda item: (item["attribution_score"], item["view_count"]), reverse=True)
        best_video = scored_videos[0]
        logger.info(
            "Best attributed video for %s on %s: %s (score: %.2f)",
            product_name,
            change_date,
            best_video["title"],
            best_video["attribution_score"],
        )
        if dry_run:
            logger.info("Dry run enabled: skipping Gemini explanation and BigQuery write.")
            return

        comments = self._query_representative_comments(product_id, best_video["video_id"], change_date)
        title, explanation = self._generate_explanation(product_name, product_id, change_date, direction, best_video, comments)
        
        if best_video["video_id"] == "N/A":
            best_video["title"] = title
            
        self._save_causal_event(product_id, change_date, direction, best_video, explanation)

    def _query_videos_in_window(self, product_id: str, change_date: date) -> list[dict]:
        query = f"""
            SELECT DISTINCT
                v.video_id,
                v.title,
                v.view_count,
                v.published_at
            FROM `{self.project_id}.{self.dataset}_staging.stg_youtube_videos` v
            JOIN `{self.project_id}.{self.dataset}.video_crawl_state` vcs ON v.video_id = vcs.video_id
            WHERE vcs.keyword_id = @product_id
              AND v.view_count > @min_viral_views
              AND DATE(v.published_at) BETWEEN DATE_SUB(@change_date, INTERVAL 7 DAY) AND DATE_ADD(@change_date, INTERVAL 7 DAY)
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("change_date", "DATE", change_date.isoformat()),
            bigquery.ScalarQueryParameter("min_viral_views", "INT64", _MIN_VIRAL_VIEWS),
        ])
        return [dict(row) for row in self.bq_client.query(query, job_config=job_config).result()]

    def _query_video_sentiment(self, product_id: str, video_id: str) -> float:
        query = f"""
            SELECT AVG(CASE
                WHEN UPPER(sentiment_label) = 'POSITIVE' THEN 1.0
                WHEN UPPER(sentiment_label) = 'NEGATIVE' THEN -1.0
                ELSE 0.0
            END) AS avg_sentiment
            FROM `{self.project_id}.{self.marts_dataset}.fact_product_mentions`
            WHERE video_id = @video_id
              AND product_id = @product_id
              AND aspect_label != 'NONE'
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
            bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
        ])
        rows = list(self.bq_client.query(query, job_config=job_config).result())
        return float(rows[0].avg_sentiment) if rows and rows[0].avg_sentiment is not None else 0.0

    def _query_representative_comments(self, product_id: str, video_id: str, change_date: date = None) -> list[str]:
        if video_id == "N/A" and change_date:
            query = f"""
                SELECT DISTINCT s.sentence_text
                FROM `{self.project_id}.{self.marts_dataset}.fact_product_mentions` f
                JOIN `{self.project_id}.{self.dataset}_intermediate.int_comment_sentences` s ON f.sentence_id = s.sentence_id
                WHERE f.product_id = @product_id
                  AND f.mention_date = @change_date
                  AND f.aspect_label != 'NONE'
                LIMIT 5
            """
            job_config = bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("change_date", "DATE", change_date.isoformat()),
            ])
        else:
            query = f"""
                SELECT DISTINCT s.sentence_text
                FROM `{self.project_id}.{self.marts_dataset}.fact_product_mentions` f
                JOIN `{self.project_id}.{self.dataset}_intermediate.int_comment_sentences` s ON f.sentence_id = s.sentence_id
                WHERE f.video_id = @video_id
                  AND f.product_id = @product_id
                  AND f.aspect_label != 'NONE'
                LIMIT 5
            """
            job_config = bigquery.QueryJobConfig(query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
            ])
        return [row.sentence_text for row in self.bq_client.query(query, job_config=job_config).result()]

    def _generate_explanation(
        self,
        product_name: str,
        product_id: str,
        change_date: date,
        direction: str,
        video: dict,
        comments: list[str],
    ) -> tuple[str, str]:
        direction_vi = "tích cực" if direction == "POSITIVE" else "tiêu cực"
        comments_text = "\n".join(f"- {comment}" for comment in comments) if comments else "Không có bình luận mẫu."
        
        prompt = f"""
        Bạn là chuyên gia phân tích thị trường công nghệ Việt Nam.
        Sản phẩm: {product_name}
        Ngày ghi nhận biến động sentiment: {change_date}
        Hướng biến động: {direction_vi}
        
        Bình luận tiêu biểu của người dùng vào ngày này:
        {comments_text}
        
        Nhiệm vụ của bạn là viết báo cáo phân tích biến động này gồm 2 phần:
        1. Tiêu đề ngắn gọn (1 câu duy nhất, tối đa 12 từ) tóm tắt xu hướng phản hồi chính của người dùng đối với sản phẩm (Ví dụ: "Người dùng đánh giá cao dung lượng pin của {product_name}" hoặc "Người dùng phàn nàn về lỗi màn hình của {product_name}").
        2. Nội dung phân tích chi tiết (2-3 câu, tối đa 50 từ). Bạn phải đi thẳng vào nội dung phân tích, TUYỆT ĐỐI không sử dụng các câu dẫn nhập rườm rà như "Dưới đây là phân tích...", "Dữ liệu cho thấy...", "Theo thống kê...". Hãy viết trực tiếp theo dạng: "X% người dùng thấy [khía cạnh] của sản phẩm tốt/chưa tốt vì lý do..." hoặc "Khoảng X% bình luận đánh giá cao [khía cạnh] nhờ...".
        
        Hãy trả về kết quả dưới định dạng sau:
        TITLE: <Tiêu đề ngắn gọn của bạn>
        DESC: <Nội dung phân tích chi tiết của bạn>
        """
        try:
            response = self.gemini_gateway.generate(prompt).strip()
            title = "Biến động thảo luận tự nhiên"
            desc = response
            
            for line in response.split("\n"):
                if line.startswith("TITLE:"):
                    title = line.replace("TITLE:", "").strip()
                elif line.startswith("DESC:"):
                    desc = line.replace("DESC:", "").strip()
            
            title = title.replace("**", "").replace("*", "")
            desc = desc.replace("**", "").replace("*", "")
            
            # Dọn dẹp các câu dẫn mở đầu rườm rà
            prefixes_to_remove = [
                "dưới đây là nội dung phân tích dựa trên dữ liệu bạn cung cấp:",
                "dưới đây là phân tích dựa trên dữ liệu bạn cung cấp:",
                "dưới đây là kết quả phân tích:",
                "dữ liệu cho thấy",
                "dữ liệu ngày cho biết",
                "dữ liệu cho biết",
                "dữ liệu ghi nhận",
                "dữ liệu ngày cho thấy",
                "theo dữ liệu phân tích,",
                "theo dữ liệu,",
                "theo thống kê,",
                "vào ngày này,"
            ]
            desc_lower = desc.lower()
            for prefix in prefixes_to_remove:
                if desc_lower.startswith(prefix):
                    desc = desc[len(prefix):].strip()
                    if desc.startswith(",") or desc.startswith(":") or desc.startswith("."):
                        desc = desc[1:].strip()
                    if desc:
                        desc = desc[0].upper() + desc[1:]
                    break
            
            return title, desc
        except Exception as exc:
            logger.error("Error calling Gemini: %s", exc)
            fallback_title = f"Người dùng phản hồi {direction_vi} về sản phẩm"
            fallback_desc = f"Phần lớn ý kiến đánh giá {direction_vi} về các khía cạnh của {product_name} trong ngày này."
            return fallback_title, fallback_desc

    def _save_causal_event(self, product_id: str, change_date: date, direction: str, video: dict, explanation: str) -> None:
        event_id = hashlib.md5(f"{product_id}-{change_date.isoformat()}-{video['video_id']}".encode("utf-8")).hexdigest()
        if self._event_exists(event_id):
            logger.info("Causal event %s already exists. Skipping insertion.", event_id)
            return

        row = {
            "event_id": event_id,
            "product_id": product_id,
            "change_point_date": change_date.isoformat(),
            "event_video_id": video["video_id"],
            "event_video_title": video["title"],
            "event_view_count": video["view_count"],
            "temporal_proximity": float(video["temporal_proximity"]),
            "direction_alignment": float(video["direction_alignment"]),
            "attribution_score": float(video["attribution_score"]),
            "sentiment_direction": direction,
            "explanation_text": explanation,
            "generated_by": (
                self._gemini_gateway.last_model
                if self._gemini_gateway and self._gemini_gateway.last_model
                else "gemini"
            ),
            "detected_at": datetime.now(timezone.utc).isoformat(),
        }
        table_id = f"{self.project_id}.{self.marts_dataset}.causal_events"
        errors = self.bq_client.insert_rows_json(table_id, [row])
        if errors:
            raise RuntimeError(f"Error inserting causal event: {errors}")
        logger.info("Saved causal event %s to database.", event_id)

    def _event_exists(self, event_id: str) -> bool:
        query = f"""
            SELECT COUNT(1) AS cnt
            FROM `{self.project_id}.{self.marts_dataset}.causal_events`
            WHERE event_id = @event_id
        """
        job_config = bigquery.QueryJobConfig(query_parameters=[
            bigquery.ScalarQueryParameter("event_id", "STRING", event_id),
        ])
        rows = list(self.bq_client.query(query, job_config=job_config).result())
        return rows[0].cnt > 0


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-points", type=int, default=10)
    parser.add_argument("--penalty", type=float, default=3.0)
    parser.add_argument("--amplitude", type=float, default=0.25)
    parser.add_argument("--min-coverage", type=float, default=_MIN_COVERAGE)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--product-id", type=str, default=None, help="Filter attribution by product_id")
    args = parser.parse_args()

    PELTAttribution().run_attribution(
        min_points=args.min_points,
        penalty=args.penalty,
        amplitude_threshold=args.amplitude,
        min_coverage=args.min_coverage,
        dry_run=args.dry_run,
        product_id=args.product_id,
    )


if __name__ == "__main__":
    main()
