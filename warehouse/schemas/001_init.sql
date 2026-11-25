
-- DataFlow Nexus
-- Initial transactional database schema

CREATE SCHEMA IF NOT EXISTS nexus;

-- 1. Customers

CREATE TABLE IF NOT EXISTS nexus.customers (
    customer_id BIGINT PRIMARY KEY,
    full_name VARCHAR(150) NOT NULL,
    email VARCHAR(255) UNIQUE NOT NULL,
    city VARCHAR(100),
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 2. Products

CREATE TABLE IF NOT EXISTS nexus.products (
    product_id BIGINT PRIMARY KEY,
    product_name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    unit_price NUMERIC(12, 2) NOT NULL
        CHECK (unit_price >= 0),
    stock_quantity INTEGER NOT NULL
        CHECK (stock_quantity >= 0)
);

-- 3. Orders

CREATE TABLE IF NOT EXISTS nexus.orders (
    order_id BIGINT PRIMARY KEY,
    customer_id BIGINT NOT NULL
        REFERENCES nexus.customers(customer_id),
    order_date TIMESTAMPTZ NOT NULL,
    status VARCHAR(30) NOT NULL
        CHECK (
            status IN (
                'pending',
                'completed',
                'cancelled',
                'shipped',
                'returned'
            )
        ),
    total_amount NUMERIC(14, 2) NOT NULL
        CHECK (total_amount >= 0)
);

-- 4. Order Items

CREATE TABLE IF NOT EXISTS nexus.order_items (
    order_item_id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL
        REFERENCES nexus.orders(order_id),
    product_id BIGINT NOT NULL
        REFERENCES nexus.products(product_id),
    quantity INTEGER NOT NULL
        CHECK (quantity > 0),
    unit_price NUMERIC(12, 2) NOT NULL
        CHECK (unit_price >= 0)
);

-- 5. Payments

CREATE TABLE IF NOT EXISTS nexus.payments (
    payment_id BIGINT PRIMARY KEY,
    order_id BIGINT NOT NULL
        REFERENCES nexus.orders(order_id),
    payment_method VARCHAR(50) NOT NULL,
    payment_status VARCHAR(30) NOT NULL
        CHECK (
            payment_status IN (
                'pending',
                'successful',
                'failed',
                'refunded'
            )
        ),
    amount NUMERIC(14, 2) NOT NULL
        CHECK (amount >= 0)
);

-- Indexes for query performance

CREATE INDEX IF NOT EXISTS idx_orders_customer
ON nexus.orders(customer_id);

CREATE INDEX IF NOT EXISTS idx_orders_date
ON nexus.orders(order_date);

CREATE INDEX IF NOT EXISTS idx_order_items_order
ON nexus.order_items(order_id);

CREATE INDEX IF NOT EXISTS idx_order_items_product
ON nexus.order_items(product_id);

CREATE INDEX IF NOT EXISTS idx_payments_order
ON nexus.payments(order_id);

CREATE INDEX IF NOT EXISTS idx_products_category
ON nexus.products(category);
