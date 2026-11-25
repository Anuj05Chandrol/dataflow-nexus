
-- Product category sales performance

SELECT
    p.category,
    SUM(oi.quantity) AS units_sold,
    ROUND(
        SUM(oi.quantity * oi.unit_price),
        2
    ) AS sales_value
FROM nexus.order_items oi
JOIN nexus.products p
    ON oi.product_id = p.product_id
JOIN nexus.orders o
    ON oi.order_id = o.order_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY sales_value DESC;
