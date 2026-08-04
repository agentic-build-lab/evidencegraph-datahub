{{ config(materialized='view', contract={'enforced': true}) }}
SELECT
    order_id,
    customer_id,
    amount_usd,
    customer_tier,
    ordered_at
FROM {{ source('commerce', 'raw_orders_current') }}
