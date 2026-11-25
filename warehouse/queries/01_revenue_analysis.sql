
-- DataFlow Nexus
-- Completed order value and average order value

SELECT
    COUNT(*) AS completed_orders,
    ROUND(SUM(total_amount), 2) AS completed_order_value,
    ROUND(AVG(total_amount), 2) AS average_order_value
FROM nexus.orders
WHERE status = 'completed';
