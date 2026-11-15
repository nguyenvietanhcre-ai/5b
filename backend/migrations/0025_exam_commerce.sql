ALTER TABLE exam_products ADD COLUMN grade INTEGER NOT NULL DEFAULT 5 CHECK(grade BETWEEN 1 AND 5);
ALTER TABLE exam_products ADD COLUMN duration_minutes INTEGER NOT NULL DEFAULT 30 CHECK(duration_minutes BETWEEN 1 AND 180);
ALTER TABLE payment_orders ADD COLUMN purchase_type TEXT NOT NULL DEFAULT 'subscription' CHECK(purchase_type IN ('subscription','tuition','exam'));
ALTER TABLE payment_orders ADD COLUMN exam_product_slug TEXT;
ALTER TABLE payment_orders ADD COLUMN exam_title TEXT;
ALTER TABLE payment_orders ADD COLUMN exam_payload_json TEXT;
UPDATE payment_orders SET purchase_type='tuition' WHERE kind='tuition';
CREATE TABLE exam_order_attempts (
    order_id INTEGER PRIMARY KEY REFERENCES payment_orders(id),
    exam_id INTEGER NOT NULL UNIQUE REFERENCES exams(id)
);
