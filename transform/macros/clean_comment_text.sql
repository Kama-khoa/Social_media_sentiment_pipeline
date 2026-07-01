{% macro clean_comment_text(column_name) -%}
NULLIF(
  TRIM(
    REGEXP_REPLACE(
      REGEXP_REPLACE(
        REGEXP_REPLACE(
          REGEXP_REPLACE(
            REGEXP_REPLACE(
              REGEXP_REPLACE(
                REGEXP_REPLACE(
                  REGEXP_REPLACE(
                    REGEXP_REPLACE(
                      REGEXP_REPLACE(
                        REGEXP_REPLACE(
                          REGEXP_REPLACE(
                            REGEXP_REPLACE(
                              REPLACE(
                                REPLACE(
                                  REPLACE(
                                    REPLACE(
                                      REPLACE(
                                        COALESCE(CAST({{ column_name }} AS STRING), ''),
                                        '&amp;', '&'
                                      ),
                                      '&quot;', '"'
                                    ),
                                    '&#39;', "'"
                                  ),
                                  '&lt;', '<'
                                ),
                                '&gt;', '>'
                              ),
                              r'[\x{200B}\x{200C}\x{200D}\x{FEFF}]', ' '
                            ),
                            r'\b(?:https?://|www\.)\S+', ' '
                          ),
                          r'(?i)(^|[[:space:]])(:-?\)+|=\)+|:-?D|=D)([[:space:]]|$)',
                          ' cam_xuc_cuoi '
                        ),
                        r'(?i)(^|[[:space:]])(:-?\(+|T_T|;_;)([[:space:]]|$)',
                        ' cam_xuc_buon '
                      ),
                      r'(^|[[:space:]])(?:[0-9]{1,2}:)?[0-9]{1,2}:[0-9]{2}([[:space:]]|$)',
                      ' '
                    ),
                    r'(^|\s)@[\p{L}\p{N}_.-]+',
                    ' '
                  ),
                  r'(^|\s)#[\p{L}\p{N}_]+',
                  ' '
                ),
                r'[\x{1F1E6}-\x{1F1FF}\x{1F300}-\x{1FAFF}\x{2600}-\x{27BF}\x{FE0F}]',
                ' '
              ),
              r'[^\p{L}\p{N}\s.,!?:;_]',
              ' '
            ),
            r'[[:space:]]+',
            ' '
          ),
          r'^[[:space:]]+',
          ''
        ),
        r'[[:space:]]+$',
        ''
      ),
      r'[[:space:]]+',
      ' '
    )
  ),
  ''
)
{%- endmacro %}
