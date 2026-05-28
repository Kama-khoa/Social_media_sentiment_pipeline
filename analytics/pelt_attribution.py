import argparse
import hashlib
import logging
import sys
from datetime import datetime, timezone, date
from pathlib import Path

project_root = str(Path(__file__).parent.parent)
if project_root not in sys.path:
    sys.path.append(project_root)

from google.cloud import bigquery
from google import genai
import numpy as np
import pandas as pd
import ruptures as rpt

from elt.config import load_config

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s")
logger = logging.getLogger("pelt_attribution")

class PELTAttribution:
    def __init__(self, config=None):
        self.config = config or load_config()
        self.bq_client = bigquery.Client(project=self.config.gcp.project_id)
        self.genai_client = genai.Client(api_key=self.config.gemini_api_key)
        self.project_id = self.config.gcp.project_id
        self.dataset = self.config.gcp.dataset

    def fetch_sentiment_timeseries(self) -> pd.DataFrame:
        query = f"""
            SELECT
                r.ranking_date,
                r.product_id,
                p.product_name,
                p.category,
                r.total_mentions,
                r.positive_count,
                r.negative_count,
                r.neutral_count,
                SAFE_DIVIDE(r.positive_count - r.negative_count, r.total_mentions) AS avg_sentiment
            FROM `{self.project_id}.{self.dataset}_marts.agg_daily_product_ranking` r
            JOIN `{self.project_id}.{self.dataset}_marts.dim_products` p ON r.product_id = p.product_id
            WHERE p.is_active = TRUE
            ORDER BY r.product_id, r.ranking_date ASC
        """
        return self.bq_client.query(query).to_dataframe()

    def run_attribution(self, min_points: int = 10, penalty: float = 3.0, amplitude_threshold: float = 0.25):
        df = self.fetch_sentiment_timeseries()
        if df.empty:
            logger.warning("No daily product ranking data found.")
            return

        products = df["product_id"].unique()
        for product_id in products:
            product_df = df[df["product_id"] == product_id].copy()
            if len(product_df) < min_points:
                logger.info(f"Skipping product {product_id}: only {len(product_df)} days of data.")
                continue

            product_name = product_df["product_name"].iloc[0]
            product_df["avg_sentiment"] = product_df["avg_sentiment"].fillna(0.0)
            points = product_df["avg_sentiment"].to_numpy(dtype=np.float64)

            try:
                algo = rpt.Pelt(model="rbf").fit(points)
                change_indices = algo.predict(pen=penalty)
            except Exception as e:
                logger.error(f"Error running PELT for product {product_id}: {e}")
                continue

            for idx in change_indices:
                if idx >= len(points):
                    continue

                before_start = max(0, idx - 7)
                before_end = idx
                after_start = idx
                after_end = min(len(points), idx + 7)

                mean_before = product_df.iloc[before_start:before_end]["avg_sentiment"].mean()
                mean_after = product_df.iloc[after_start:after_end]["avg_sentiment"].mean()
                amplitude = mean_after - mean_before

                if abs(amplitude) <= amplitude_threshold:
                    continue

                direction = "POSITIVE" if amplitude > 0 else "NEGATIVE"
                change_date = product_df.iloc[idx]["ranking_date"]
                if isinstance(change_date, str):
                    change_date = datetime.strptime(change_date, "%Y-%m-%d").date()
                elif isinstance(change_date, datetime):
                    change_date = change_date.date()

                logger.info(f"Detected change point for {product_name} on {change_date}: {direction} (amplitude: {amplitude:.2f})")
                self._attribute_event(product_id, product_name, change_date, direction)

    def _attribute_event(self, product_id: str, product_name: str, change_date: date, direction: str):
        videos = self._query_videos_in_window(product_id, change_date)
        if not videos:
            logger.warning(f"No videos found within window for {product_name} on {change_date}")
            return

        change_dir_val = 1.0 if direction == "POSITIVE" else -1.0
        scored_videos = []

        for video in videos:
            video_id = video["video_id"]
            view_count = video["view_count"] or 0
            published_at = video["published_at"]

            if isinstance(published_at, str):
                pub_date = datetime.fromisoformat(published_at.replace("Z", "+00:00")).date()
            elif isinstance(published_at, datetime):
                pub_date = published_at.date()
            else:
                pub_date = published_at

            days_diff = abs((pub_date - change_date).days)
            temporal_proximity = max(0.0, 1.0 - days_diff / 7.0)

            video_sentiment = self._query_video_sentiment(product_id, video_id)
            if video_sentiment * change_dir_val > 0:
                direction_alignment = 1.0
            elif video_sentiment == 0.0:
                direction_alignment = 0.5
            else:
                direction_alignment = 0.0

            attribution_score = temporal_proximity * 0.5 + direction_alignment * 0.5
            scored_videos.append({
                **video,
                "temporal_proximity": temporal_proximity,
                "direction_alignment": direction_alignment,
                "attribution_score": attribution_score
            })

        scored_videos.sort(key=lambda x: (x["attribution_score"], x["view_count"]), reverse=True)
        best_video = scored_videos[0]

        logger.info(f"Best attributed video for {product_name} on {change_date}: {best_video['title']} (score: {best_video['attribution_score']:.2f})")

        comments = self._query_representative_comments(product_id, best_video["video_id"])
        explanation = self._generate_explanation(product_name, product_id, change_date, direction, best_video, comments)

        self._save_causal_event(product_id, change_date, direction, best_video, explanation)

    def _query_videos_in_window(self, product_id: str, change_date: date) -> list[dict]:
        query = f"""
            SELECT
                v.video_id,
                v.title,
                v.view_count,
                v.published_at
            FROM `{self.project_id}.{self.dataset}_staging.stg_youtube_videos` v
            JOIN `{self.project_id}.{self.dataset}.video_crawl_state` vcs ON v.video_id = vcs.video_id
            WHERE vcs.keyword_id = @product_id
              AND DATE(v.published_at) BETWEEN DATE_SUB(@change_date, INTERVAL 7 DAY) AND DATE_ADD(@change_date, INTERVAL 7 DAY)
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("change_date", "DATE", change_date.isoformat()),
            ]
        )
        rows = self.bq_client.query(query, job_config=job_config).result()
        return [dict(row) for row in rows]

    def _query_video_sentiment(self, product_id: str, video_id: str) -> float:
        query = f"""
            SELECT AVG(CASE 
                WHEN sentiment_label = 'POSITIVE' THEN 1.0
                WHEN sentiment_label = 'NEGATIVE' THEN -1.0
                ELSE 0.0
            END) AS avg_sentiment
            FROM `{self.project_id}.{self.dataset}_marts.fact_product_mentions`
            WHERE video_id = @video_id AND product_id = @product_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
            ]
        )
        rows = list(self.bq_client.query(query, job_config=job_config).result())
        if rows and rows[0].avg_sentiment is not None:
            return float(rows[0].avg_sentiment)
        return 0.0

    def _query_representative_comments(self, product_id: str, video_id: str) -> list[str]:
        query = f"""
            SELECT DISTINCT s.sentence_text
            FROM `{self.project_id}.{self.dataset}_marts.fact_product_mentions` f
            JOIN `{self.project_id}.{self.dataset}_intermediate.int_comment_sentences` s ON f.sentence_id = s.sentence_id
            WHERE f.video_id = @video_id AND f.product_id = @product_id
            LIMIT 5
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("product_id", "STRING", product_id),
                bigquery.ScalarQueryParameter("video_id", "STRING", video_id),
            ]
        )
        rows = self.bq_client.query(query, job_config=job_config).result()
        return [row.sentence_text for row in rows]

    def _generate_explanation(self, product_name: str, product_id: str, change_date: date, direction: str, video: dict, comments: list[str]) -> str:
        direction_vi = "tích cực" if direction == "POSITIVE" else "tiêu cực"
        comments_text = "\n".join([f"- {c}" for c in comments]) if comments else "Không có bình luận mẫu."
        
        prompt = f"""
        Bạn là một chuyên gia phân tích thị trường công nghệ Việt Nam.
        Sản phẩm: {product_name} (ID: {product_id})
        Ngày xảy ra biến động sentiment đột ngột: {change_date}
        Hướng biến động: {direction} (cảm xúc của cộng đồng trở nên {direction_vi} hơn)

        Video YouTube có tương quan cao nhất:
        - Tiêu đề: {video['title']}
        - Lượt xem: {video['view_count']:,}
        - Ngày đăng: {video['published_at']}

        Một số bình luận tiêu biểu của người dùng về sản phẩm này trong video:
        {comments_text}

        Hãy viết một đoạn phân tích ngắn (2-3 câu bằng tiếng Việt) giải thích nguyên nhân dẫn đến sự biến động cảm xúc đột ngột này.
        Yêu cầu:
        1. Viết tự nhiên, súc tích.
        2. Sử dụng các từ ngữ thể hiện tính tương quan một cách khoa học và dè dặt như 'có thể', 'tương quan', 'được ghi nhận', 'cho thấy'.
        3. Tập trung giải thích tại sao video này hoặc các bình luận lại phản ánh/gây ra sự thay đổi cảm xúc đó đối với sản phẩm.
        """
        
        try:
            response = self.genai_client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            return f"Phát hiện sự biến động cảm xúc {direction_vi} có tương quan với video review '{video['title']}'."

    def _save_causal_event(self, product_id: str, change_date: date, direction: str, video: dict, explanation: str):
        event_str = f"{product_id}-{change_date.isoformat()}-{video['video_id']}"
        event_id = hashlib.md5(event_str.encode("utf-8")).hexdigest()

        if self._event_exists(event_id):
            logger.info(f"Causal event {event_id} already exists. Skipping insertion.")
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
            "generated_by": "gemini-2.5-flash",
            "detected_at": datetime.now(timezone.utc).isoformat()
        }

        table_id = f"{self.project_id}.{self.dataset}.causal_events"
        errors = self.bq_client.insert_rows_json(table_id, [row])
        if errors:
            logger.error(f"Error inserting causal event: {errors}")
        else:
            logger.info(f"Saved causal event {event_id} to database.")

    def _event_exists(self, event_id: str) -> bool:
        query = f"""
            SELECT COUNT(1) AS cnt
            FROM `{self.project_id}.{self.dataset}.causal_events`
            WHERE event_id = @event_id
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("event_id", "STRING", event_id)
            ]
        )
        rows = list(self.bq_client.query(query, job_config=job_config).result())
        return rows[0].cnt > 0

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--min-points", type=int, default=10)
    parser.add_argument("--penalty", type=float, default=3.0)
    parser.add_argument("--amplitude", type=float, default=0.25)
    args = parser.parse_args()

    attribution = PELTAttribution()
    attribution.run_attribution(
        min_points=args.min_points,
        penalty=args.penalty,
        amplitude_threshold=args.amplitude
    )

if __name__ == "__main__":
    main()
