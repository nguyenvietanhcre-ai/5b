CREATE TABLE website_business (
    id INTEGER PRIMARY KEY CHECK(id=1),
    payload_json TEXT NOT NULL DEFAULT '{}',
    revision INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);
INSERT INTO website_business(id,updated_at) VALUES(1,CURRENT_TIMESTAMP);
CREATE TABLE website_policy_drafts (
    id INTEGER PRIMARY KEY,
    version TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    content TEXT NOT NULL,
    draft INTEGER NOT NULL DEFAULT 1 CHECK(draft=1),
    created_at TEXT NOT NULL,
    staff_id INTEGER REFERENCES staff_users(id)
);
INSERT INTO website_policy_drafts(version,title,content,created_at)
VALUES('2026-11-17-draft1','Bộ chính sách website — bản nháp','Chờ chủ quản xác nhận thông tin kinh doanh, điều kiện hủy/hoàn tiền, thời gian phản hồi và lưu giữ dữ liệu. Chưa phải chính sách đã duyệt.',CURRENT_TIMESTAMP);
CREATE TABLE website_support_requests (
    id INTEGER PRIMARY KEY,
    ticket TEXT NOT NULL UNIQUE,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    kind TEXT NOT NULL CHECK(kind IN ('support','order','refund','data_access','data_correct','data_delete','consent_withdraw')),
    subject TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'received' CHECK(status IN ('received','reviewing','waiting_user','resolved','rejected')),
    order_id INTEGER REFERENCES payment_orders(id),
    revision INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX website_support_owner ON website_support_requests(account_id,id);
CREATE TABLE website_support_events (
    id INTEGER PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES website_support_requests(id),
    actor TEXT NOT NULL CHECK(actor IN ('user','admin')),
    staff_id INTEGER REFERENCES staff_users(id),
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE TABLE website_refund_records (
    id INTEGER PRIMARY KEY,
    request_id INTEGER NOT NULL REFERENCES website_support_requests(id),
    order_id INTEGER NOT NULL REFERENCES payment_orders(id),
    amount INTEGER NOT NULL CHECK(amount>0),
    reference TEXT NOT NULL UNIQUE,
    manual_status TEXT NOT NULL CHECK(manual_status='completed_manual'),
    staff_id INTEGER NOT NULL REFERENCES staff_users(id),
    created_at TEXT NOT NULL
);
