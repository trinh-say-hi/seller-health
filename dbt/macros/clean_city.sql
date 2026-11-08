{% macro clean_city(col) %}
CASE 
    WHEN trim(regexp_replace(trim(regexp_split_to_array(lower(strip_accents(regexp_replace(trim(replace({{ col }}, '´', '''')), '\s+', ' ', 'g'))), '\s*[/\\,]\s*|\s+-\s+')[1]), '[\s-](ac|al|am|ap|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to)$', '')) IS NULL 
      OR trim(regexp_replace(trim(regexp_split_to_array(lower(strip_accents(regexp_replace(trim(replace({{ col }}, '´', '''')), '\s+', ' ', 'g'))), '\s*[/\\,]\s*|\s+-\s+')[1]), '[\s-](ac|al|am|ap|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to)$', '')) = '' 
      OR regexp_matches(trim(regexp_replace(trim(regexp_split_to_array(lower(strip_accents(regexp_replace(trim(replace({{ col }}, '´', '''')), '\s+', ' ', 'g'))), '\s*[/\\,]\s*|\s+-\s+')[1]), '[\s-](ac|al|am|ap|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to)$', '')), '[0-9@]') 
    THEN NULL 
    ELSE trim(regexp_replace(trim(regexp_split_to_array(lower(strip_accents(regexp_replace(trim(replace({{ col }}, '´', '''')), '\s+', ' ', 'g'))), '\s*[/\\,]\s*|\s+-\s+')[1]), '[\s-](ac|al|am|ap|ba|ce|df|es|go|ma|mg|ms|mt|pa|pb|pe|pi|pr|rj|rn|ro|rr|rs|sc|se|sp|to)$', '')) 
END
{% endmacro %}
