SELECT
    customer_id,
    customer_tier,
    SUM(amount_usd) AS lifetime_value_usd
FROM {{ ref('stg_orders') }}
GROUP BY customer_id, customer_tier

