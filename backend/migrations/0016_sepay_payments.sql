ALTER TABLE payment_orders ADD COLUMN kind TEXT NOT NULL DEFAULT 'vip' CHECK(kind IN ('vip','tuition'));
ALTER TABLE payment_orders ADD COLUMN vip_months INTEGER DEFAULT 1 CHECK(vip_months BETWEEN 1 AND 120);
ALTER TABLE payment_orders ADD COLUMN vip_unit_price INTEGER DEFAULT 100000 CHECK(vip_unit_price > 0);
ALTER TABLE payment_orders ADD COLUMN fee_student_id INTEGER REFERENCES students(id);
ALTER TABLE payment_orders ADD COLUMN fee_class_id INTEGER REFERENCES online_classes(id);
ALTER TABLE payment_orders ADD COLUMN fee_month TEXT;
ALTER TABLE payment_orders ADD COLUMN bank_id TEXT;
ALTER TABLE payment_orders ADD COLUMN bank_account TEXT;
ALTER TABLE payment_orders ADD COLUMN bank_name TEXT;
ALTER TABLE payment_orders ADD COLUMN paid_at TEXT;
ALTER TABLE payment_orders ADD COLUMN confirmed_source TEXT CHECK(confirmed_source IN ('staff','sepay'));

UPDATE payment_orders SET kind=CASE WHEN fee_id IS NULL THEN 'vip' ELSE 'tuition' END,
    vip_months=CASE WHEN fee_id IS NULL THEN 1 END,
    vip_unit_price=CASE WHEN fee_id IS NULL THEN 100000 END,
    fee_student_id=(SELECT student_id FROM class_fees WHERE id=fee_id),
    fee_class_id=(SELECT class_id FROM class_fees WHERE id=fee_id),
    fee_month=(SELECT month FROM class_fees WHERE id=fee_id);

CREATE TABLE payment_receipts (
    id INTEGER PRIMARY KEY,
    provider TEXT NOT NULL CHECK(provider='sepay'),
    transaction_id INTEGER NOT NULL CHECK(transaction_id > 0),
    payload_hash TEXT NOT NULL CHECK(length(payload_hash)=64),
    order_id INTEGER REFERENCES payment_orders(id),
    status TEXT NOT NULL CHECK(status IN ('processed','review','ignored')),
    reason TEXT NOT NULL,
    amount INTEGER NOT NULL CHECK(amount > 0),
    reference TEXT NOT NULL,
    bank TEXT NOT NULL,
    bank_account TEXT NOT NULL,
    bank_reference TEXT NOT NULL,
    transaction_at TEXT,
    received_at TEXT NOT NULL,
    UNIQUE(provider,transaction_id)
);
CREATE UNIQUE INDEX payment_receipts_settled_order ON payment_receipts(order_id) WHERE status='processed';
CREATE INDEX payment_receipts_status ON payment_receipts(status,id DESC);
CREATE INDEX payment_receipts_order ON payment_receipts(order_id,id DESC);
ALTER TABLE payment_orders ADD COLUMN receipt_id INTEGER REFERENCES payment_receipts(id);

CREATE TRIGGER payment_receipts_immutable_update BEFORE UPDATE ON payment_receipts
BEGIN SELECT RAISE(ABORT,'Payment receipts are immutable'); END;
CREATE TRIGGER payment_receipts_immutable_delete BEFORE DELETE ON payment_receipts
BEGIN SELECT RAISE(ABORT,'Payment receipts are immutable'); END;
