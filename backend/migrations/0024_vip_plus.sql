ALTER TABLE accounts ADD COLUMN vip_plus_expires_at TEXT;
ALTER TABLE payment_orders ADD COLUMN subscription_plan TEXT NOT NULL DEFAULT 'VIP' CHECK(subscription_plan IN ('VIP','VIP+'));

CREATE TABLE video_series (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    position INTEGER NOT NULL UNIQUE
);
INSERT INTO video_series VALUES ('giai-de-10-phut','Giải đề 10p',1);
INSERT INTO video_series VALUES ('cau-phan-loai','Giải câu phân loại học sinh',2);
INSERT INTO video_series VALUES ('meo-lam-bai','Mẹo làm bài',3);
CREATE TABLE series_videos (
    id INTEGER PRIMARY KEY,
    series_slug TEXT NOT NULL REFERENCES video_series(slug),
    position INTEGER NOT NULL CHECK(position>0),
    title TEXT NOT NULL,
    media_url TEXT NOT NULL,
    published INTEGER NOT NULL DEFAULT 0 CHECK(published IN (0,1)),
    UNIQUE(series_slug,position)
);

-- Products are published only after their price and actual content are supplied.
CREATE TABLE exam_products (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    price INTEGER NOT NULL CHECK(price>0),
    question_version_ids_json TEXT NOT NULL,
    published INTEGER NOT NULL DEFAULT 0 CHECK(published IN (0,1))
);

CREATE TABLE premium_sets (
    slug TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    track TEXT NOT NULL CHECK(track IN ('super-hard','classification','olympiad','school')),
    school TEXT,
    grade INTEGER NOT NULL CHECK(grade BETWEEN 1 AND 5),
    duration_minutes INTEGER NOT NULL CHECK(duration_minutes BETWEEN 1 AND 180),
    question_version_ids_json TEXT NOT NULL,
    published INTEGER NOT NULL DEFAULT 0 CHECK(published IN (0,1))
);
