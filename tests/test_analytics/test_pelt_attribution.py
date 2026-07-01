from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pandas as pd

from analytics.pelt_attribution import PELTAttribution


def _config():
    config = MagicMock()
    config.gcp.project_id = "test-project"
    config.gcp.dataset = "test-dataset"
    config.gemini_api_key = "test-key"
    return config


def _daily_frame(days: list[int], sentiments: list[float]) -> pd.DataFrame:
    return pd.DataFrame({
        "ranking_date": [date(2025, 1, day) for day in days],
        "product_id": ["prod-1"] * len(days),
        "product_name": ["Product 1"] * len(days),
        "category": ["Cat 1"] * len(days),
        "total_mentions": [10] * len(days),
        "positive_count": [5] * len(days),
        "negative_count": [2] * len(days),
        "neutral_count": [3] * len(days),
        "avg_sentiment": sentiments,
    })


def test_fetch_sentiment_timeseries_uses_valid_daily_mentions():
    bq_client = MagicMock()
    bq_client.insert_rows_json.return_value = []
    expected = _daily_frame([1], [0.7])
    bq_client.query.return_value.to_dataframe.return_value = expected

    result = PELTAttribution(config=_config(), bq_client=bq_client).fetch_sentiment_timeseries()

    assert result.equals(expected)
    query = bq_client.query.call_args.args[0]
    assert "fact_product_mentions" in query
    assert "aspect_label != 'NONE'" in query


def test_prepare_product_timeseries_interpolates_gap_up_to_two_days():
    frame = _daily_frame([1, 2, 5, 6, 7, 8, 9, 10], [0.1, 0.2, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0])
    attribution = PELTAttribution(config=_config(), bq_client=MagicMock())

    prepared = attribution.prepare_product_timeseries(frame, min_points=8, min_coverage=0.7)

    assert prepared is not None
    assert len(prepared) == 10
    assert prepared["avg_sentiment"].isna().sum() == 0


def test_prepare_product_timeseries_skips_long_gap():
    frame = _daily_frame([1, 2, 3, 7, 8, 9, 10], [0.1] * 7)
    attribution = PELTAttribution(config=_config(), bq_client=MagicMock())

    prepared = attribution.prepare_product_timeseries(frame, min_points=7, min_coverage=0.7)

    assert prepared is None


def test_prepare_product_timeseries_skips_low_coverage():
    frame = _daily_frame([1, 5, 10], [0.1] * 3)
    attribution = PELTAttribution(config=_config(), bq_client=MagicMock())

    prepared = attribution.prepare_product_timeseries(frame, min_points=3, min_coverage=0.7)

    assert prepared is None


@patch("analytics.pelt_attribution.rpt.Pelt")
def test_run_attribution_writes_marts_event_for_viral_candidate(mock_pelt_class):
    bq_client = MagicMock()
    bq_client.insert_rows_json.return_value = []
    genai_client = MagicMock()
    genai_client.models.generate_content.return_value.text = "Giải thích từ Gemini"
    bq_client.query.return_value.to_dataframe.return_value = _daily_frame(list(range(1, 16)), [0.1] * 7 + [0.7] * 8)
    bq_client.query.return_value.result.side_effect = [
        [{"video_id": "vid-1", "title": "Review Product 1", "view_count": 100001, "published_at": datetime(2025, 1, 8, 12)}],
        [MagicMock(avg_sentiment=0.8)],
        [MagicMock(sentence_text="Bình luận tốt")],
        [MagicMock(cnt=0)],
    ]
    mock_pelt_class.return_value.fit.return_value.predict.return_value = [7, 15]

    PELTAttribution(config=_config(), bq_client=bq_client, genai_client=genai_client).run_attribution()

    table_id, rows = bq_client.insert_rows_json.call_args.args
    assert table_id == "test-project.test-dataset_marts.causal_events"
    assert rows[0]["event_video_id"] == "vid-1"
    assert rows[0]["sentiment_direction"] == "POSITIVE"


def test_dry_run_skips_gemini_and_bigquery_write():
    bq_client = MagicMock()
    attribution = PELTAttribution(config=_config(), bq_client=bq_client)
    attribution._query_videos_in_window = MagicMock(return_value=[
        {"video_id": "vid-1", "title": "Review", "view_count": 100001, "published_at": datetime(2025, 1, 8)}
    ])
    attribution._query_video_sentiment = MagicMock(return_value=0.8)

    attribution._attribute_event("prod-1", "Product 1", date(2025, 1, 8), "POSITIVE", dry_run=True)

    assert attribution._genai_client is None
    bq_client.insert_rows_json.assert_not_called()


def test_no_viral_candidate_skips_event():
    bq_client = MagicMock()
    attribution = PELTAttribution(config=_config(), bq_client=bq_client)
    attribution._query_videos_in_window = MagicMock(return_value=[])

    attribution._attribute_event("prod-1", "Product 1", date(2025, 1, 8), "POSITIVE")

    bq_client.insert_rows_json.assert_not_called()


def test_existing_event_is_not_inserted_twice():
    bq_client = MagicMock()
    attribution = PELTAttribution(config=_config(), bq_client=bq_client)
    attribution._event_exists = MagicMock(return_value=True)
    video = {
        "video_id": "vid-1",
        "title": "Review",
        "view_count": 100001,
        "temporal_proximity": 1.0,
        "direction_alignment": 1.0,
        "attribution_score": 1.0,
    }

    attribution._save_causal_event("prod-1", date(2025, 1, 8), "POSITIVE", video, "Explanation")

    bq_client.insert_rows_json.assert_not_called()
