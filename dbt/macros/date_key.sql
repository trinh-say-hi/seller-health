{% macro date_key(ts_col) %}
CAST(strftime({{ ts_col }}, '%Y%m%d') AS INTEGER)
{% endmacro %}
