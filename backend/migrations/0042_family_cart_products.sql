CREATE TABLE family_cart_product_items (
    family_id INTEGER NOT NULL REFERENCES family_carts(family_id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    type TEXT NOT NULL CHECK(type IN ('credits','tuition','exam')),
    product_key TEXT NOT NULL,
    product_ref TEXT NOT NULL,
    quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 10 AND (type='credits' OR quantity=1)),
    revision INTEGER NOT NULL CHECK(revision>0),
    item_json TEXT NOT NULL CHECK(json_valid(item_json)),
    PRIMARY KEY(family_id,student_id,product_key)
);

CREATE TABLE family_cart_product_order_items (
    id INTEGER PRIMARY KEY,
    order_id INTEGER NOT NULL REFERENCES family_cart_orders(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    type TEXT NOT NULL CHECK(type IN ('credits','tuition','exam')),
    product_key TEXT NOT NULL,
    product_ref TEXT NOT NULL,
    fee_id INTEGER REFERENCES class_fees(id),
    content_key TEXT,
    quantity INTEGER NOT NULL CHECK(quantity BETWEEN 1 AND 10 AND (type='credits' OR quantity=1)),
    cart_item_revision INTEGER NOT NULL CHECK(cart_item_revision>0),
    item_json TEXT NOT NULL CHECK(json_valid(item_json)),
    pin_json TEXT NOT NULL CHECK(json_valid(pin_json)),
    applied_at TEXT,
    UNIQUE(order_id,student_id,product_key),
    CHECK((type='tuition')=(fee_id IS NOT NULL)),
    CHECK((type='exam')=(content_key IS NOT NULL))
);
CREATE INDEX family_cart_product_fee ON family_cart_product_order_items(fee_id,order_id) WHERE type='tuition';
CREATE INDEX family_cart_product_exam ON family_cart_product_order_items(account_id,order_id,product_ref,content_key) WHERE type='exam';

CREATE TRIGGER family_cart_product_owns_line BEFORE INSERT ON family_cart_product_order_items
WHEN NEW.applied_at IS NOT NULL OR NOT EXISTS(
    SELECT 1 FROM family_cart_orders o JOIN family_children c ON c.family_id=o.family_id
    JOIN students s ON s.id=c.student_id WHERE o.id=NEW.order_id AND o.status='pending'
    AND c.student_id=NEW.student_id AND s.account_id=NEW.account_id)
BEGIN SELECT RAISE(ABORT,'Family cart product must belong to a pending order and its beneficiary'); END;

CREATE TRIGGER family_cart_product_evidence_immutable BEFORE UPDATE OF order_id,student_id,account_id,
    type,product_key,product_ref,fee_id,content_key,quantity,cart_item_revision,item_json,pin_json ON family_cart_product_order_items
BEGIN SELECT RAISE(ABORT,'Family cart product evidence is immutable'); END;

CREATE TRIGGER family_cart_product_apply_once BEFORE UPDATE OF applied_at ON family_cart_product_order_items
WHEN OLD.applied_at IS NOT NULL OR NEW.applied_at IS NULL OR NOT EXISTS(
    SELECT 1 FROM family_cart_orders o WHERE o.id=NEW.order_id AND o.status='pending')
BEGIN SELECT RAISE(ABORT,'Family cart product may be applied once'); END;

CREATE TRIGGER family_cart_paid_requires_products BEFORE UPDATE OF status ON family_cart_orders
WHEN NEW.status='paid' AND EXISTS(SELECT 1 FROM family_cart_product_order_items i
    WHERE i.order_id=NEW.id AND i.applied_at IS NULL)
BEGIN SELECT RAISE(ABORT,'Family cart requires all products to be applied'); END;

ALTER TABLE class_fees ADD COLUMN cart_quote_revision INTEGER NOT NULL DEFAULT 0 CHECK(cart_quote_revision>=0);
CREATE TRIGGER family_cart_fee_revision AFTER UPDATE OF class_id,student_id,month,amount,paid_at,source,
    session_fee,charged_count,free_count,absent_count,pending_count,sessions_json,calculation_id,calculated_at ON class_fees
WHEN NEW.class_id IS NOT OLD.class_id OR NEW.student_id IS NOT OLD.student_id OR NEW.month IS NOT OLD.month
    OR NEW.amount IS NOT OLD.amount OR NEW.paid_at IS NOT OLD.paid_at OR NEW.source IS NOT OLD.source
    OR NEW.session_fee IS NOT OLD.session_fee OR NEW.charged_count IS NOT OLD.charged_count
    OR NEW.free_count IS NOT OLD.free_count OR NEW.absent_count IS NOT OLD.absent_count
    OR NEW.pending_count IS NOT OLD.pending_count OR NEW.sessions_json IS NOT OLD.sessions_json
    OR NEW.calculation_id IS NOT OLD.calculation_id OR NEW.calculated_at IS NOT OLD.calculated_at
BEGIN UPDATE class_fees SET cart_quote_revision=OLD.cart_quote_revision+1 WHERE id=NEW.id; END;

ALTER TABLE payment_orders ADD COLUMN family_cart_product_line_id INTEGER REFERENCES family_cart_product_order_items(id);
CREATE UNIQUE INDEX payment_orders_cart_product_grant ON payment_orders(family_cart_product_line_id)
    WHERE family_cart_product_line_id IS NOT NULL;

CREATE TRIGGER family_cart_exam_grant_owns_line BEFORE INSERT ON payment_orders
WHEN NEW.family_cart_product_line_id IS NOT NULL AND NOT EXISTS(
    SELECT 1 FROM family_cart_product_order_items i JOIN family_cart_orders o ON o.id=i.order_id
    WHERE i.id=NEW.family_cart_product_line_id AND i.account_id=NEW.account_id AND o.status='pending'
    AND i.type='exam' AND i.product_ref=NEW.exam_product_slug AND i.applied_at IS NULL
    AND NEW.family_cart_order_id IS NULL AND NEW.status='paid' AND NEW.kind='vip'
    AND NEW.purchase_type='exam' AND NEW.fee_id IS NULL AND NEW.amount=json_extract(i.item_json,'$.amount'))
BEGIN SELECT RAISE(ABORT,'Exam grant must correspond to its pending family cart line'); END;

CREATE TRIGGER family_cart_exam_grant_immutable BEFORE UPDATE ON payment_orders
WHEN OLD.family_cart_product_line_id IS NOT NULL OR NEW.family_cart_product_line_id IS NOT NULL
BEGIN SELECT RAISE(ABORT,'Confirmed family cart exam grants are immutable'); END;
