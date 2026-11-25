
-- Monthly completed order trends

SELECT
    DATE_TRUNC('month', order_date) AS month,
    COUNT(*) AS total_orders,
    ROUND(SUM(total_amount), 2) AS order_value
FROM nexus.orders
WHERE status = 'completed'
GROUP BY month
ORDER BY month;
