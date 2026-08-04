-- EvidenceGraph change EG-042. Source: DataHub document RFC-42.
        CREATE OR REPLACE VIEW stg_orders_compat AS
        SELECT
            order_id,
            customer_id,
            amount_usd,
            CASE segment_code
    WHEN 'B' THEN 'bronze'
    WHEN 'G' THEN 'gold'
    WHEN 'S' THEN 'silver'
    ELSE NULL
END AS customer_tier,
            ordered_at
        FROM raw_orders_next;
