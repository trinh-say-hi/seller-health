{% macro region_of(state_col) %}
CASE
    WHEN {{ state_col }} IN ('AC','AM','AP','PA','RO','RR','TO') THEN 'Norte'
    WHEN {{ state_col }} IN ('AL','BA','CE','MA','PB','PE','PI','RN','SE') THEN 'Nordeste'
    WHEN {{ state_col }} IN ('DF','GO','MS','MT') THEN 'Centro-Oeste'
    WHEN {{ state_col }} IN ('ES','MG','RJ','SP') THEN 'Sudeste'
    WHEN {{ state_col }} IN ('PR','RS','SC') THEN 'Sul'
    ELSE 'Khong ro'
END
{% endmacro %}
