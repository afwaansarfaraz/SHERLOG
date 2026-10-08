-- Sherlog Demo SaaS Database Initialization Script
CREATE TABLE IF NOT EXISTS orders (
    id SERIAL PRIMARY KEY,
    customer_id VARCHAR(64) NOT NULL,
    total_amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(32) NOT NULL DEFAULT 'PENDING',
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS order_items (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    product_id VARCHAR(64) NOT NULL,
    quantity INT NOT NULL,
    price NUMERIC(10, 2) NOT NULL
);

CREATE TABLE IF NOT EXISTS payments (
    id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    amount NUMERIC(10, 2) NOT NULL,
    currency VARCHAR(3) NOT NULL DEFAULT 'USD',
    status VARCHAR(32) NOT NULL,
    transaction_id VARCHAR(128),
    created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_order ON payments(order_id);

-- Seed initial test orders
INSERT INTO orders (customer_id, total_amount, currency, status) VALUES
    ('cust_alpha_01', 129.50, 'USD', 'COMPLETED'),
    ('cust_beta_02', 450.00, 'USD', 'COMPLETED'),
    ('cust_gamma_03', 89.99, 'USD', 'COMPLETED')
ON CONFLICT DO NOTHING;

INSERT INTO order_items (order_id, product_id, quantity, price) VALUES
    (1, 'prod_item_99', 2, 64.75),
    (2, 'prod_item_12', 1, 450.00),
    (3, 'prod_item_44', 1, 89.99)
ON CONFLICT DO NOTHING;

INSERT INTO payments (order_id, amount, currency, status, transaction_id) VALUES
    (1, 129.50, 'USD', 'CONFIRMED', 'tx_alpha_9941'),
    (2, 450.00, 'USD', 'CONFIRMED', 'tx_beta_3312'),
    (3, 89.99, 'USD', 'CONFIRMED', 'tx_gamma_8819')
ON CONFLICT DO NOTHING;
