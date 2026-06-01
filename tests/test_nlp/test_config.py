from __future__ import annotations

from nlp.config import NLPConfig, load_nlp_config


def test_load_nlp_config_reads_nlp_section(tmp_path) -> None:
    config_path = tmp_path / "pipeline_config.yaml"
    config_path.write_text(
        "nlp:\n  confidence_threshold: 0.82\n  gemini_batch_size: 25\n",
        encoding="utf-8",
    )

    assert load_nlp_config(config_path) == NLPConfig(
        confidence_threshold=0.82,
        gemini_batch_size=25,
    )


def test_load_nlp_config_uses_defaults_when_nlp_section_is_missing(tmp_path) -> None:
    config_path = tmp_path / "pipeline_config.yaml"
    config_path.write_text("crawl: {}\n", encoding="utf-8")

    assert load_nlp_config(config_path) == NLPConfig(
        confidence_threshold=0.70,
        gemini_batch_size=50,
    )
