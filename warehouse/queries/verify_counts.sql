SELECT 'customers' AS table_name, COUNT(*) AS records
FROM nexus.customers
UNION ALL
SELECT 'products', COUNT(*) FROM nexus.products
UNION ALL
SELECT 'orders', COUNT(*) FROM nexus.orders
UNION ALL
SELECT 'order_items', COUNT(*) FROM nexus.order_items
UNION ALL
SELECT 'payments', COUNT(*) FROM nexus.payments;