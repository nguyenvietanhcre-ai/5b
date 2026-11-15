ALTER TABLE video_series ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE video_series ADD COLUMN archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1));
ALTER TABLE series_videos ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE series_videos ADD COLUMN archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1));
ALTER TABLE exam_products ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE exam_products ADD COLUMN archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1));
ALTER TABLE premium_sets ADD COLUMN revision INTEGER NOT NULL DEFAULT 1;
ALTER TABLE premium_sets ADD COLUMN archived INTEGER NOT NULL DEFAULT 0 CHECK(archived IN (0,1));
INSERT OR IGNORE INTO system_settings(name,value_json,updated_at) VALUES ('premium','{"videos_open":true,"sales_open":true,"advanced_open":true}',strftime('%Y-%m-%dT%H:%M:%SZ','now'));
