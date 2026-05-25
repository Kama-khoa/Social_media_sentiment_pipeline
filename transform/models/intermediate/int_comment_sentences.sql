{{ config(
    materialized='incremental',
    unique_key='sentence_id'
) }}

{% call set_sql_header(config) %}

-- UDF thay thế từ viết tắt/từ lóng theo từ điển chuẩn
CREATE TEMP FUNCTION replace_slang(text STRING, slangs ARRAY<STRUCT<slang STRING, standard_word STRING>>)
RETURNS STRING
LANGUAGE js AS """
  if (!text || !slangs || slangs.length === 0) return text;
  
  // Caching RegExp object to avoid compiling 200+ regexes per row
  if (typeof global_slang_cache === 'undefined') {
      const vn_chars = "a-zA-Z0-9_àáảãạăắằẳẵặâấầẩẫậèéẻẽẹêếềểễệìíỉĩịòóỏõọôốồổỗộơớờởỡợùúủũụưứừửữựỳýỷỹỵđÀÁẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÈÉẺẼẸÊẾỀỂỄỆÌÍỈĨỊÒÓỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÙÚỦŨỤƯỨỪỬỮỰỲÝỶỸỴĐ";
      let sorted = [...slangs].sort((a, b) => b.slang.length - a.slang.length);
      
      let map = {};
      let patterns = [];
      function escapeRegExp(str) { return str.replace(/[.*+?^${}()|[\\]\\\\]/g, '\\\\$&'); }
      
      for (let s of sorted) {
          if (!s.slang) continue;
          let es = escapeRegExp(s.slang.toLowerCase());
          map[es] = s.standard_word;
          patterns.push(es);
      }
      
      let bigPattern = "(?<![" + vn_chars + "])(" + patterns.join("|") + ")(?![" + vn_chars + "])";
      global_slang_cache = {
          regex: new RegExp(bigPattern, "gi"),
          map: map
      };
  }
  
  return text.replace(global_slang_cache.regex, (match) => {
      let lowerMatch = match.toLowerCase();
      return global_slang_cache.map[lowerMatch] || match;
  });
""";
{% endcall %}

WITH stg_comments AS (
    SELECT * FROM {{ ref('stg_youtube_comments') }}
    {% if is_incremental() %}
    WHERE _dbt_loaded_at > (SELECT MAX(_dbt_processed_at) FROM {{ this }})
    {% endif %}
),

-- Chuẩn bị mảng từ điển slang
slangs_pre AS (
    SELECT ARRAY_AGG(STRUCT(slang, standard_word)) AS slang_arr
    FROM {{ ref('vn_slang_dictionary') }}
),

-- Tách câu bằng Native SQL thay vì JS UDF (nhanh hơn rất nhiều)
-- REGEXP_REPLACE thêm dấu '|' sau mỗi dấu ngắt câu hoặc xuống dòng, sau đó SPLIT bằng '|'
split_comments AS (
    SELECT
        c.comment_id,
        c.video_id,
        c.channel_id,
        c.data_quality_score,
        c.published_at,
        c._dbt_loaded_at,
        TRIM(s) AS sentence_text,
        OFFSET + 1 AS sentence_index,
        sp.slang_arr
    FROM stg_comments c
    CROSS JOIN slangs_pre sp
    CROSS JOIN UNNEST(SPLIT(REGEXP_REPLACE(c.text_original, r'([.!?\n]+)', r'\1|'), '|')) AS s WITH OFFSET
    WHERE TRIM(s) != ''
)

SELECT
    CONCAT(comment_id, '_', sentence_index) AS sentence_id,
    comment_id,
    video_id,
    channel_id,
    sentence_index,
    sentence_text,
    replace_slang(LOWER(sentence_text), slang_arr) AS sentence_text_normalized,
    TRUE AS is_vietnamese,
    ARRAY_LENGTH(SPLIT(sentence_text, ' ')) AS word_count,
    data_quality_score,
    published_at,
    CURRENT_TIMESTAMP() AS _dbt_processed_at
FROM split_comments
