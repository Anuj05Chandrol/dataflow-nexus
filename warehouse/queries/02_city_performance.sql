
-- Top 10 cities by completed order value

SELECT
    c.city,
    COUNT(o.order_id) AS total_orders,
    ROUND(SUM(o.total_amount), 2) AS order_value
FROM nexus.orders o
JOIN nexus.customers c
    ON o.customer_id = c.customer_id
WHERE o.status = 'completed'
GROUP BY c.city
ORDER BY order_value DESC
LIMIT 10;
