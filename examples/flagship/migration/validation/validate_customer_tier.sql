-- Native DuckDB validation. Zero rows is the only passing result.
SELECT
    n.order_id,
    n.segment_code,
    c.customer_tier AS expected,
    s.customer_tier AS actual
FROM raw_orders_next AS n
LEFT JOIN raw_orders_current AS c USING (order_id)
LEFT JOIN stg_orders_compat AS s USING (order_id)
WHERE s.customer_tier IS NULL
   OR s.customer_tier NOT IN ('bronze', 'silver', 'gold')
   OR s.customer_tier <> c.customer_tier;
