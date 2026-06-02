import xml.etree.ElementTree as ET
from xml.dom import minidom

tables = {
    # Layer 0
    "channel_config": [
        "* channel_id : STRING",
        "channel_name : STRING",
        "channel_url : STRING",
        "channel_handle : STRING",
        "subscriber_count : INT64",
        "is_active : BOOL",
        "is_historically_scanned : BOOL",
        "historical_scan_completed_at : TIMESTAMP",
        "created_at : TIMESTAMP",
        "last_updated_at : TIMESTAMP"
    ],
    "keyword_config": [
        "* keyword_id : STRING",
        "keyword_text : STRING",
        "search_cluster : STRING",
        "is_active : BOOL",
        "created_at : TIMESTAMP"
    ],
    "product_config": [
        "* product_id : STRING",
        "product_name : STRING",
        "brand : STRING",
        "category : STRING",
        "release_year : INT64",
        "is_active : BOOL",
        "created_at : TIMESTAMP",
        "updated_at : TIMESTAMP"
    ],
    "product_aliases": [
        "* alias_id : STRING",
        "product_id : STRING <<FK>>",
        "alias_text : STRING",
        "alias_type : STRING",
        "is_active : BOOL",
        "created_at : TIMESTAMP"
    ],
    "product_details": [
        "* product_id : STRING <<FK>>",
        "specs : JSON",
        "description : STRING",
        "official_url : STRING",
        "image_url : STRING",
        "updated_at : TIMESTAMP",
        "updated_by : STRING"
    ],
    "video_crawl_state": [
        "* video_id : STRING <<FK>>",
        "channel_id : STRING <<FK>>",
        "keyword_id : STRING <<FK>>",
        "search_mode : STRING",
        "published_at : TIMESTAMP",
        "maturity_stage : STRING",
        "comment_count : INT64",
        "total_comments_crawled : INT64",
        "is_comment_complete : BOOL",
        "crawl_status : STRING",
        "updated_at : TIMESTAMP"
    ],
    # Layer 1
    "raw_videos": [
        "* video_id : STRING",
        "channel_id : STRING <<FK>>",
        "title : STRING",
        "description : STRING",
        "view_count : INT64",
        "like_count : INT64",
        "comment_count : INT64",
        "duration_seconds : INT64",
        "tags : STRING[]",
        "thumbnail_url : STRING",
        "published_at : TIMESTAMP",
        "search_mode : STRING",
        "keyword_matched : STRING",
        "gcs_partition_date : STRING",
        "crawled_at : TIMESTAMP"
    ],
    "raw_comments": [
        "* comment_id : STRING",
        "video_id : STRING <<FK>>",
        "channel_id : STRING <<FK>>",
        "parent_comment_id : STRING",
        "author_channel_id : STRING",
        "author_display_name : STRING",
        "text_original : STRING",
        "text_display : STRING",
        "like_count : INT64",
        "reply_count : INT64",
        "is_reply : BOOL",
        "crawl_type : STRING",
        "published_at : TIMESTAMP",
        "updated_at : TIMESTAMP",
        "crawled_at : TIMESTAMP",
        "gcs_partition_date : STRING"
    ],
    "raw_sentiment_results": [
        "* result_id : STRING",
        "sentence_id : STRING",
        "comment_id : STRING <<FK>>",
        "video_id : STRING <<FK>>",
        "aspect_label : STRING",
        "segment_text : STRING",
        "sentiment_label : STRING",
        "confidence_score : FLOAT64",
        "inference_model : STRING",
        "dag_run_id : STRING",
        "processed_at : TIMESTAMP"
    ],
    # Layer 2
    "stg_youtube_videos": [
        "* video_id : STRING",
        "channel_id : STRING <<FK>>",
        "title : STRING",
        "description : STRING",
        "keyword_matched : STRING",
        "view_count : INT64",
        "like_count : INT64",
        "comment_count : INT64",
        "data_quality_score : FLOAT64",
        "published_at : TIMESTAMP"
    ],
    "stg_youtube_comments": [
        "* comment_id : STRING",
        "video_id : STRING <<FK>>",
        "channel_id : STRING",
        "parent_comment_id : STRING",
        "author_channel_id : STRING",
        "text_original : STRING",
        "like_count : INT64",
        "reply_count : INT64",
        "is_reply : BOOL",
        "data_quality_score : FLOAT64",
        "published_at : TIMESTAMP"
    ],
    # Layer 3
    "int_comment_sentences": [
        "* sentence_id : STRING",
        "comment_id : STRING <<FK>>",
        "video_id : STRING <<FK>>",
        "channel_id : STRING <<FK>>",
        "sentence_index : INT64",
        "sentence_text : STRING",
        "sentence_text_normalized : STRING",
        "is_vietnamese : BOOL",
        "word_count : INT64",
        "data_quality_score : FLOAT64",
        "published_at : TIMESTAMP",
        "_dbt_processed_at : TIMESTAMP"
    ],
    "int_sentiment_results": [
        "* result_id : STRING",
        "sentence_id : STRING <<FK>>",
        "comment_id : STRING <<FK>>",
        "video_id : STRING <<FK>>",
        "aspect_label : STRING",
        "segment_text : STRING",
        "sentiment_label : STRING",
        "confidence_score : FLOAT64",
        "inference_model : STRING",
        "dag_run_id : STRING",
        "processed_at : TIMESTAMP"
    ],
    "finetune_dataset": [
        "* sample_id : STRING",
        "sentence_id : STRING <<FK>>",
        "sentence_text : STRING",
        "tokens_json : STRING",
        "bio_tags_json : STRING",
        "aspect_labels_json : STRING",
        "sentiment_label : STRING",
        "annotation_source : STRING",
        "split : STRING",
        "is_validated : BOOL",
        "annotated_at : TIMESTAMP"
    ],
    "int_video_product_mentions": [
        "* video_id : STRING <<FK>>",
        "* product_id : STRING <<FK>>",
        "role : STRING",
        "match_source : STRING",
        "confidence_score : FLOAT64",
        "_dbt_processed_at : TIMESTAMP"
    ],
    "int_sentence_product_targets": [
        "* sentence_id : STRING <<FK>>",
        "video_id : STRING <<FK>>",
        "product_id : STRING <<FK>>",
        "target_source : STRING",
        "target_confidence : FLOAT64",
        "target_sentiment_label : STRING",
        "resolution_status : STRING",
        "_dbt_processed_at : TIMESTAMP"
    ],
    "int_product_resolution_candidates": [
        "* candidate_id : STRING",
        "source_type : STRING",
        "source_id : STRING",
        "candidate_text : STRING",
        "status : STRING",
        "resolved_product_id : STRING <<FK>>",
        "created_at : TIMESTAMP"
    ],
    # Layer 4
    "dim_products": [
        "* product_id : STRING",
        "product_name : STRING",
        "brand : STRING",
        "category : STRING",
        "release_year : INT64",
        "is_active : BOOL",
        "created_at : TIMESTAMP"
    ],
    "fact_product_mentions": [
        "* mention_id : STRING",
        "product_id : STRING <<FK>>",
        "video_id : STRING <<FK>>",
        "channel_id : STRING <<FK>>",
        "comment_id : STRING <<FK>>",
        "sentence_id : STRING <<FK>>",
        "aspect_label : STRING",
        "sentiment_label : STRING",
        "confidence_score : FLOAT64",
        "mention_date : DATE"
    ],
    "agg_daily_product_ranking": [
        "* ranking_id : STRING",
        "product_id : STRING <<FK>>",
        "ranking_date : DATE",
        "category : STRING",
        "bayesian_score : FLOAT64",
        "controversy_index : FLOAT64",
        "controversy_label : STRING",
        "total_mentions : INT64",
        "positive_count : INT64",
        "negative_count : INT64",
        "neutral_count : INT64",
        "rank_position : INT64"
    ],
    "causal_events": [
        "* event_id : STRING",
        "product_id : STRING <<FK>>",
        "change_point_date : DATE",
        "event_video_id : STRING <<FK>>",
        "temporal_proximity : FLOAT64",
        "attribution_score : FLOAT64",
        "sentiment_direction : STRING",
        "explanation_text : STRING"
    ]
}

edges = [
    ("product_config", "product_aliases", "1", "N"),
    ("product_config", "product_details", "1", "1"),
    ("channel_config", "raw_videos", "1", "N"),
    ("channel_config", "stg_youtube_videos", "1", "N"),
    ("raw_videos", "raw_comments", "1", "N"),
    ("stg_youtube_videos", "stg_youtube_comments", "1", "N"),
    ("stg_youtube_videos", "video_crawl_state", "1", "1"),
    ("keyword_config", "video_crawl_state", "1", "N"),
    ("raw_videos", "int_comment_sentences", "1", "N"),
    ("raw_comments", "int_comment_sentences", "1", "N"),
    ("int_comment_sentences", "finetune_dataset", "1", "1"),
    ("int_comment_sentences", "int_sentiment_results", "1", "N"),
    ("int_comment_sentences", "int_sentence_product_targets", "1", "N"),
    ("dim_products", "fact_product_mentions", "1", "N"),
    ("dim_products", "int_video_product_mentions", "1", "N"),
    ("stg_youtube_videos", "fact_product_mentions", "1", "N"),
    ("stg_youtube_comments", "fact_product_mentions", "1", "N"),
    ("dim_products", "agg_daily_product_ranking", "1", "N"),
    ("dim_products", "causal_events", "1", "N")
]

mxGraphModel = ET.Element("mxGraphModel")
root = ET.SubElement(mxGraphModel, "root")
ET.SubElement(root, "mxCell", id="0")
ET.SubElement(root, "mxCell", id="1", parent="0")

x = 50
y = 50
col = 0
for table_name, cols in tables.items():
    html_content = f"<b>{table_name}</b><hr>" + "<br>".join(cols)
    h = 40 + len(cols) * 15
    cell = ET.SubElement(root, "mxCell", id=table_name, value=html_content)
    cell.set("style", "rounded=1;whiteSpace=wrap;html=1;align=left;spacingLeft=10;verticalAlign=top;spacingTop=5;fillColor=#dae8fc;strokeColor=#6c8ebf;")
    cell.set("vertex", "1")
    cell.set("parent", "1")
    geo = ET.SubElement(cell, "mxGeometry", x=str(x), y=str(y), width="250", height=str(h))
    geo.set("as", "geometry")
    
    col += 1
    x += 300
    if col >= 5:
        col = 0
        x = 50
        y += 400

edge_id = 1
for src, dst, t_src, t_dst in edges:
    cell = ET.SubElement(root, "mxCell", id=f"edge_{edge_id}")
    edge_style = "edgeStyle=orthogonalEdgeStyle;rounded=1;orthogonalLoop=1;jettySize=auto;html=1;"
    if t_dst == "N":
        edge_style += "endArrow=ERmany;endFill=0;"
    else:
        edge_style += "endArrow=ERone;endFill=0;"
    
    if t_src == "N":
        edge_style += "startArrow=ERmany;startFill=0;"
    else:
        edge_style += "startArrow=ERone;startFill=0;"
        
    cell.set("style", edge_style)
    cell.set("edge", "1")
    cell.set("parent", "1")
    cell.set("source", src)
    cell.set("target", dst)
    geo = ET.SubElement(cell, "mxGeometry", relative="1")
    geo.set("as", "geometry")
    edge_id += 1

xmlstr = minidom.parseString(ET.tostring(mxGraphModel)).toprettyxml(indent="  ")
with open(r"f:\Studies\Đồ án tốt nghiệp\Social_media_sentiment_pipeline\docs\schema_erd.drawio", "w", encoding="utf-8") as f:
    f.write(xmlstr)

print("Generated docs/schema_erd.drawio")
