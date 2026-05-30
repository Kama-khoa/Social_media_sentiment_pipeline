import unittest
from unittest.mock import patch, MagicMock
from datetime import date, datetime
import pandas as pd
import numpy as np
import pytest

from analytics.pelt_attribution import PELTAttribution

def test_fetch_sentiment_timeseries():
    with patch("analytics.pelt_attribution.bigquery.Client") as mock_bq_class, \
         patch("analytics.pelt_attribution.genai.Client"), \
         patch("analytics.pelt_attribution.load_config") as mock_load_config:
        
        mock_config = MagicMock()
        mock_config.gcp.project_id = "test-project"
        mock_config.gcp.dataset = "test-dataset"
        mock_load_config.return_value = mock_config

        mock_bq_client = MagicMock()
        mock_bq_class.return_value = mock_bq_client

        mock_df = pd.DataFrame([
            {"ranking_date": date(2025, 1, 1), "product_id": "prod-1", "product_name": "Product 1", "category": "Cat 1", "total_mentions": 10, "positive_count": 8, "negative_count": 1, "neutral_count": 1, "avg_sentiment": 0.7}
        ])
        mock_bq_client.query.return_value.to_dataframe.return_value = mock_df

        attribution = PELTAttribution()
        result = attribution.fetch_sentiment_timeseries()

        assert not result.empty
        assert len(result) == 1
        assert result.iloc[0]["product_id"] == "prod-1"

def test_run_attribution():
    with patch("analytics.pelt_attribution.bigquery.Client") as mock_bq_class, \
         patch("analytics.pelt_attribution.genai.Client") as mock_genai_class, \
         patch("analytics.pelt_attribution.load_config") as mock_load_config, \
         patch("analytics.pelt_attribution.rpt.Pelt") as mock_pelt_class:

        mock_config = MagicMock()
        mock_config.gcp.project_id = "test-project"
        mock_config.gcp.dataset = "test-dataset"
        mock_config.gemini_api_key = "test-key"
        mock_load_config.return_value = mock_config

        mock_bq_client = MagicMock()
        mock_bq_class.return_value = mock_bq_client

        mock_genai_client = MagicMock()
        mock_genai_class.return_value = mock_genai_client

        mock_algo = MagicMock()
        mock_algo.predict.return_value = [7, 15]
        mock_pelt_class.return_value.fit.return_value = mock_algo

        dates = [date(2025, 1, i) for i in range(1, 16)]
        avg_sentiments = [0.1] * 7 + [0.7] * 8
        product_df = pd.DataFrame({
            "ranking_date": dates,
            "product_id": ["prod-1"] * 15,
            "product_name": ["Product 1"] * 15,
            "category": ["Cat 1"] * 15,
            "total_mentions": [10] * 15,
            "positive_count": [5] * 15,
            "negative_count": [2] * 15,
            "neutral_count": [3] * 15,
            "avg_sentiment": avg_sentiments
        })

        mock_bq_client.query.return_value.to_dataframe.return_value = product_df

        mock_videos = [
            {"video_id": "vid-1", "title": "Review Product 1", "view_count": 100000, "published_at": datetime(2025, 1, 8, 12, 0, 0)}
        ]
        
        mock_bq_client.query.return_value.result.side_effect = [
            mock_videos,
            [MagicMock(avg_sentiment=0.8)],
            [MagicMock(sentence_text="Bình luận tốt")],
            [MagicMock(cnt=0)]
        ]

        mock_genai_client.models.generate_content.return_value.text = "Giải thích từ Gemini"

        attribution = PELTAttribution()
        attribution.run_attribution(min_points=10)

        assert mock_bq_client.insert_rows_json.called
        call_args = mock_bq_client.insert_rows_json.call_args[0]
        assert call_args[0] == "test-project.test-dataset.causal_events"
        row = call_args[1][0]
        assert row["product_id"] == "prod-1"
        assert row["event_video_id"] == "vid-1"
        assert row["sentiment_direction"] == "POSITIVE"
        assert row["explanation_text"] == "Giải thích từ Gemini"
