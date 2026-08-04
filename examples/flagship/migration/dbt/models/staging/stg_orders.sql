{{ config(materialized='view', contract={'enforced': true}) }}
        -- Evidence claims are enumerated in migration/evidencegraph-manifest.json.
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
        FROM {{ source('commerce', 'raw_orders_next') }}
