CREATE TABLE raw_orders_current (
    order_id BIGINT,
    customer_id BIGINT,
    amount_usd DECIMAL(12, 2),
    customer_tier VARCHAR,
    segment_code VARCHAR,
    ordered_at TIMESTAMP
);

INSERT INTO raw_orders_current VALUES
    (1001, 501, 120.00, 'gold', 'G', '2026-08-01 10:00:00'),
    (1002, 502, 42.50, 'silver', 'S', '2026-08-01 10:05:00'),
    (1003, 501, 18.25, 'gold', 'G', '2026-08-01 11:00:00'),
    (1004, 503, 9.99, 'bronze', 'B', '2026-08-01 12:00:00');

CREATE TABLE raw_orders_next AS
SELECT order_id, customer_id, amount_usd, segment_code, ordered_at
FROM raw_orders_current;

