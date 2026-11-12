DROP TRIGGER vip_purchase_apply;
CREATE TABLE notification_broadcasts (
    id INTEGER PRIMARY KEY,
    staff_id INTEGER NOT NULL REFERENCES staff_users(id),
    request_key TEXT NOT NULL,
    title TEXT NOT NULL,
    body TEXT NOT NULL,
    audience TEXT NOT NULL CHECK (audience IN ('all','Free','VIP','SVip','class')),
    class_id INTEGER REFERENCES online_classes(id),
    audience_label TEXT NOT NULL,
    sender_name TEXT NOT NULL,
    sender_role TEXT NOT NULL CHECK (sender_role IN ('admin','teacher')),
    recipient_count INTEGER NOT NULL CHECK (recipient_count > 0),
    created_at TEXT NOT NULL,
    UNIQUE(staff_id, request_key),
    CHECK ((audience='class' AND class_id IS NOT NULL) OR (audience<>'class' AND class_id IS NULL))
);
CREATE INDEX notification_broadcasts_staff ON notification_broadcasts(staff_id,created_at DESC,id DESC);
CREATE TABLE notification_broadcast_recipients (
    broadcast_id INTEGER NOT NULL REFERENCES notification_broadcasts(id),
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    PRIMARY KEY (broadcast_id, account_id)
);
CREATE TABLE notifications_new (
    id INTEGER PRIMARY KEY,
    account_id INTEGER NOT NULL REFERENCES accounts(id),
    referral_id INTEGER UNIQUE REFERENCES account_referrals(id),
    kind TEXT NOT NULL CHECK (kind IN ('referral_vip_reward','referral_contact_support','vip_subscription_success','vip_renewal_success','staff_message')),
    title TEXT NOT NULL DEFAULT 'Thông báo từ 5BMath',
    body TEXT NOT NULL,
    sender_name TEXT NOT NULL DEFAULT '5BMath',
    sender_role TEXT NOT NULL DEFAULT 'system' CHECK (sender_role IN ('system','admin','teacher')),
    sender_staff_id INTEGER REFERENCES staff_users(id),
    broadcast_id INTEGER REFERENCES notification_broadcasts(id),
    purchase_id INTEGER UNIQUE REFERENCES vip_purchases(id),
    created_at TEXT NOT NULL,
    read_at TEXT,
    UNIQUE(broadcast_id, account_id)
);
INSERT INTO notifications_new(id,account_id,referral_id,kind,title,body,created_at,read_at)
SELECT id,account_id,referral_id,kind,
       CASE kind WHEN 'referral_vip_reward' THEN 'Nhận thưởng giới thiệu thành công'
                 ELSE 'Phần thưởng giới thiệu cần hỗ trợ' END,
       body,created_at,read_at FROM notifications;
DROP TABLE notifications;
ALTER TABLE notifications_new RENAME TO notifications;
CREATE INDEX notifications_inbox ON notifications(account_id,created_at DESC,id DESC);
CREATE INDEX notifications_unread ON notifications(account_id,id) WHERE read_at IS NULL;
CREATE INDEX notifications_priority ON notifications(account_id,(read_at IS NOT NULL),created_at DESC,id DESC);

CREATE TRIGGER vip_purchase_apply
AFTER INSERT ON vip_purchases
BEGIN
    UPDATE accounts
    SET vip_expires_at = strftime('%Y-%m-%dT%H:%M:%SZ',
        printf('%s-%02dT%s',
            strftime('%Y-%m', CASE WHEN vip_expires_at > NEW.confirmed_at THEN vip_expires_at ELSE NEW.confirmed_at END, '+7 hours', 'start of month', printf('+%d months', NEW.months)),
            MIN(
                CAST(strftime('%d', CASE WHEN vip_expires_at > NEW.confirmed_at THEN vip_expires_at ELSE NEW.confirmed_at END, '+7 hours') AS INTEGER),
                CAST(strftime('%d', CASE WHEN vip_expires_at > NEW.confirmed_at THEN vip_expires_at ELSE NEW.confirmed_at END, '+7 hours', 'start of month', printf('+%d months', (NEW.months) + 1), '-1 day') AS INTEGER)
            ),
            strftime('%H:%M:%S', CASE WHEN vip_expires_at > NEW.confirmed_at THEN vip_expires_at ELSE NEW.confirmed_at END, '+7 hours')
        ), '-7 hours')
    WHERE id = NEW.account_id;

    UPDATE account_referrals
    SET first_vip_upgraded_at = NEW.confirmed_at,
        qualifying_purchase_id = NEW.id,
        reward_status = CASE WHEN EXISTS (
            SELECT 1 FROM access_entitlements
            WHERE account_id = inviter_account_id AND kind = 'internal'
              AND starts_at <= NEW.confirmed_at
              AND (ends_at IS NULL OR ends_at > NEW.confirmed_at)
        ) THEN 'customer_service' ELSE 'granted' END,
        reward_granted_at = CASE WHEN EXISTS (
            SELECT 1 FROM access_entitlements
            WHERE account_id = inviter_account_id AND kind = 'internal'
              AND starts_at <= NEW.confirmed_at
              AND (ends_at IS NULL OR ends_at > NEW.confirmed_at)
        ) THEN NULL ELSE NEW.confirmed_at END
    WHERE invitee_account_id = NEW.account_id AND first_vip_upgraded_at IS NULL
      AND NOT EXISTS (SELECT 1 FROM vip_purchases WHERE account_id = NEW.account_id AND id <> NEW.id);

    UPDATE accounts
    SET vip_expires_at = strftime('%Y-%m-%dT%H:%M:%SZ',
        printf('%s-%02dT%s',
            strftime('%Y-%m', CASE WHEN vip_expires_at > NEW.confirmed_at THEN vip_expires_at ELSE NEW.confirmed_at END, '+7 hours', 'start of month', printf('+%d months', 1)),
            MIN(
                CAST(strftime('%d', CASE WHEN vip_expires_at > NEW.confirmed_at THEN vip_expires_at ELSE NEW.confirmed_at END, '+7 hours') AS INTEGER),
                CAST(strftime('%d', CASE WHEN vip_expires_at > NEW.confirmed_at THEN vip_expires_at ELSE NEW.confirmed_at END, '+7 hours', 'start of month', printf('+%d months', (1) + 1), '-1 day') AS INTEGER)
            ),
            strftime('%H:%M:%S', CASE WHEN vip_expires_at > NEW.confirmed_at THEN vip_expires_at ELSE NEW.confirmed_at END, '+7 hours')
        ), '-7 hours')
    WHERE id = (
        SELECT inviter_account_id FROM account_referrals
        WHERE qualifying_purchase_id = NEW.id AND reward_status = 'granted'
    );

    UPDATE account_referrals
    SET reward_vip_expires_at = (SELECT vip_expires_at FROM accounts WHERE id = inviter_account_id)
    WHERE qualifying_purchase_id = NEW.id AND reward_status = 'granted';

    INSERT INTO notifications (account_id,referral_id,kind,title,body,sender_name,sender_role,created_at)
    SELECT inviter_account_id,id,
        CASE reward_status WHEN 'granted' THEN 'referral_vip_reward' ELSE 'referral_contact_support' END,
        CASE reward_status WHEN 'granted' THEN 'Nhận thưởng giới thiệu thành công' ELSE 'Phần thưởng giới thiệu cần hỗ trợ' END,
        CASE reward_status
            WHEN 'granted' THEN 'Bạn vừa nhận 1 tháng VIP từ chương trình giới thiệu. Thời hạn VIP đã được cộng dồn đến ' ||
                strftime('%d/%m/%Y %H:%M',reward_vip_expires_at,'+7 hours') || ' (giờ Việt Nam).'
            ELSE 'Bạn có phần thưởng từ chương trình giới thiệu. Vui lòng liên hệ bộ phận chăm sóc khách hàng để nhận thưởng dành cho tài khoản nội bộ.'
        END,
        '5BMath','system',NEW.confirmed_at
    FROM account_referrals WHERE qualifying_purchase_id=NEW.id;

    INSERT INTO notifications (account_id,kind,title,body,sender_name,sender_role,purchase_id,created_at)
    SELECT NEW.account_id,
        CASE WHEN (SELECT count(*) FROM vip_purchases WHERE account_id=NEW.account_id)=1
             THEN 'vip_subscription_success' ELSE 'vip_renewal_success' END,
        CASE WHEN (SELECT count(*) FROM vip_purchases WHERE account_id=NEW.account_id)=1
             THEN 'Đăng ký VIP thành công' ELSE 'Gia hạn VIP thành công' END,
        CASE WHEN (SELECT count(*) FROM vip_purchases WHERE account_id=NEW.account_id)=1
             THEN 'Bạn đã đăng ký VIP thành công. Thời hạn VIP đến '
             ELSE 'Bạn đã gia hạn VIP thành công. Thời hạn VIP mới đến ' END ||
             strftime('%d/%m/%Y %H:%M',vip_expires_at,'+7 hours') || ' (giờ Việt Nam).',
        '5BMath','system',NEW.id,NEW.confirmed_at
    FROM accounts WHERE id=NEW.account_id;
END;
