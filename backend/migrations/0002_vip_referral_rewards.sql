CREATE TRIGGER vip_purchases_immutable_update
BEFORE UPDATE ON vip_purchases
BEGIN
    SELECT RAISE(ABORT, 'Confirmed VIP purchases are immutable');
END;

CREATE TRIGGER vip_purchases_immutable_delete
BEFORE DELETE ON vip_purchases
BEGIN
    SELECT RAISE(ABORT, 'Confirmed VIP purchases are immutable');
END;

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

    INSERT INTO notifications (account_id, referral_id, kind, body, created_at)
    SELECT inviter_account_id, id,
        CASE reward_status WHEN 'granted' THEN 'referral_vip_reward' ELSE 'referral_contact_support' END,
        CASE reward_status
            WHEN 'granted' THEN 'Bạn vừa nhận 1 tháng VIP từ chương trình giới thiệu. Thời hạn VIP đã được cộng dồn vào tài khoản.'
            ELSE 'Bạn có phần thưởng từ chương trình giới thiệu. Vui lòng liên hệ bộ phận chăm sóc khách hàng để nhận thưởng dành cho tài khoản nội bộ.'
        END,
        NEW.confirmed_at
    FROM account_referrals WHERE qualifying_purchase_id = NEW.id;
END;
