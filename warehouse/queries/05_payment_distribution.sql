
-- Payment method distribution

SELECT
    payment_method,
    COUNT(*) AS transactions,
    ROUND(
        COUNT(*) * 100.0
        / SUM(COUNT(*)) OVER (),
        2
    ) AS percentage
FROM nexus.payments
GROUP BY payment_method
ORDER BY transactions DESC;
