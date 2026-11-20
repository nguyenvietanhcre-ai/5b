CREATE TABLE family_carts (
    family_id INTEGER PRIMARY KEY REFERENCES family_accounts(id),
    revision INTEGER NOT NULL CHECK(revision >= 0)
);

CREATE TABLE family_cart_items (
    family_id INTEGER NOT NULL REFERENCES family_carts(family_id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    plan TEXT NOT NULL CHECK(plan IN ('VIP','VIP+')),
    period TEXT NOT NULL CHECK(period IN ('month','year')),
    referral_code TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK(revision > 0),
    PRIMARY KEY (family_id,student_id)
);

CREATE TABLE family_cart_orders (
    id INTEGER PRIMARY KEY,
    family_id INTEGER NOT NULL REFERENCES family_accounts(id),
    reference TEXT NOT NULL COLLATE NOCASE UNIQUE,
    amount INTEGER NOT NULL CHECK(amount > 0),
    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending','paid','cancelled')),
    created_at TEXT NOT NULL,
    bank_id TEXT,
    bank_account TEXT,
    bank_name TEXT,
    quote_hash TEXT NOT NULL CHECK(length(quote_hash)=64),
    cart_revision INTEGER NOT NULL CHECK(cart_revision > 0),
    purchaser_json TEXT NOT NULL,
    checkout_snapshot_json TEXT NOT NULL,
    paid_at TEXT,
    confirmed_source TEXT CHECK(confirmed_source IN ('staff','sepay')),
    receipt_id INTEGER UNIQUE REFERENCES payment_receipts(id),
    cancelled_at TEXT
);
CREATE UNIQUE INDEX family_cart_one_pending ON family_cart_orders(family_id) WHERE status='pending';
CREATE INDEX family_cart_order_history ON family_cart_orders(family_id,id DESC);
CREATE INDEX family_cart_order_repeat ON family_cart_orders(family_id,quote_hash);

ALTER TABLE payment_orders ADD COLUMN family_cart_order_id INTEGER REFERENCES family_cart_orders(id);
DROP INDEX payment_order_pending;
CREATE UNIQUE INDEX payment_order_pending ON payment_orders(account_id,coalesce(fee_id,0))
    WHERE status='pending' AND family_cart_order_id IS NULL;
CREATE UNIQUE INDEX payment_orders_family_cart_grant ON payment_orders(family_cart_order_id,account_id)
    WHERE family_cart_order_id IS NOT NULL;

CREATE TABLE family_cart_order_items (
    order_id INTEGER NOT NULL REFERENCES family_cart_orders(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    cart_item_revision INTEGER NOT NULL CHECK(cart_item_revision > 0),
    item_json TEXT NOT NULL,
    referrer_student_id INTEGER REFERENCES students(id),
    grant_order_id INTEGER UNIQUE REFERENCES payment_orders(id),
    PRIMARY KEY (order_id,student_id)
);
CREATE INDEX family_cart_reservation ON family_cart_order_items(account_id,order_id);

ALTER TABLE payment_receipts ADD COLUMN family_cart_order_id INTEGER REFERENCES family_cart_orders(id);
CREATE UNIQUE INDEX payment_receipts_settled_family_cart ON payment_receipts(family_cart_order_id)
    WHERE status='processed' AND family_cart_order_id IS NOT NULL;
CREATE INDEX payment_receipts_family_cart ON payment_receipts(family_cart_order_id,id DESC);

CREATE TRIGGER family_cart_order_snapshot_immutable BEFORE UPDATE OF family_id,reference,amount,created_at,
    bank_id,bank_account,bank_name,quote_hash,cart_revision,purchaser_json,checkout_snapshot_json ON family_cart_orders
BEGIN SELECT RAISE(ABORT,'Family cart order evidence is immutable'); END;

CREATE TRIGGER family_cart_order_close_once BEFORE UPDATE ON family_cart_orders WHEN OLD.status<>'pending'
BEGIN SELECT RAISE(ABORT,'Closed family cart orders are immutable'); END;

CREATE TRIGGER family_cart_order_line_evidence_immutable BEFORE UPDATE OF order_id,student_id,account_id,
    cart_item_revision,item_json,referrer_student_id ON family_cart_order_items
BEGIN SELECT RAISE(ABORT,'Family cart order line evidence is immutable'); END;

CREATE TRIGGER family_cart_order_line_grant_once BEFORE UPDATE OF grant_order_id ON family_cart_order_items
WHEN OLD.grant_order_id IS NOT NULL OR NOT EXISTS(
    SELECT 1 FROM payment_orders p WHERE p.id=NEW.grant_order_id AND p.family_cart_order_id=NEW.order_id
    AND p.account_id=NEW.account_id AND p.status='paid')
BEGIN SELECT RAISE(ABORT,'Family cart order line grant can be linked once'); END;

CREATE TRIGGER family_cart_grant_owns_line BEFORE INSERT ON payment_orders
WHEN NEW.family_cart_order_id IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM family_cart_order_items i JOIN family_cart_orders o ON o.id=i.order_id
    WHERE i.order_id=NEW.family_cart_order_id AND i.account_id=NEW.account_id AND o.status='pending'
    AND i.grant_order_id IS NULL AND NEW.kind='vip' AND NEW.purchase_type='subscription' AND NEW.fee_id IS NULL)
BEGIN SELECT RAISE(ABORT,'Family cart grant must correspond to its pending line'); END;

CREATE TRIGGER family_cart_grant_closed_immutable BEFORE UPDATE ON payment_orders
WHEN OLD.family_cart_order_id IS NOT NULL AND OLD.status='paid'
BEGIN SELECT RAISE(ABORT,'Confirmed family cart grants are immutable'); END;
