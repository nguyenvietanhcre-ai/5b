"""Record an admin's assisted SVip referral reward once, without extending VIP."""
from .platform_api import APIError, stamp


def confirm_support(db, user, identity, body):
    from .learning_update import membership
    from .staff_api import audit, number, require_admin
    require_admin(user)
    expected = number(body, 'referrerAccountId')
    referral = db.execute('SELECT r.*,a.deleted_at FROM account_referrals r '
                          'JOIN accounts a ON a.id=r.inviter_account_id WHERE r.id=?', (identity,)).fetchone()
    if not referral:
        raise APIError('Không tìm thấy lượt giới thiệu.', 404)
    if referral['inviter_account_id'] != expected:
        raise APIError('Người giới thiệu đã chọn không khớp dữ liệu. Tải lại bảng để kiểm tra.', 409)
    previous = db.execute('SELECT * FROM referral_reward_confirmations WHERE referral_id=?', (identity,)).fetchone()
    if previous:
        return {'saved': True, 'referralId': identity, 'supportConfirmedAt': previous['confirmed_at'],
                'supportConfirmedBy': previous['confirmed_by'], 'replayed': True}
    qualified = db.execute('SELECT 1 FROM vip_purchases WHERE id=? AND account_id=?',
                           (referral['qualifying_purchase_id'], referral['invitee_account_id'])).fetchone()
    if (referral['reward_status'] != 'customer_service' or not referral['first_vip_upgraded_at'] or
            not qualified or referral['deleted_at'] is not None or
            membership(db, {'account_id': expected}) != 'SVip'):
        raise APIError('Chỉ xác nhận phần thưởng cần hỗ trợ của người giới thiệu SVip đã đủ điều kiện.', 409)
    confirmed = stamp()
    db.execute('INSERT INTO referral_reward_confirmations(referral_id,confirmed_by,confirmed_at) VALUES (?,?,?)',
               (identity, user['id'], confirmed))
    audit(db, user, 'confirm', 'referral_reward', identity, 'Đã hỗ trợ nhận thưởng cho người giới thiệu ' + str(expected))
    return {'saved': True, 'referralId': identity, 'supportConfirmedAt': confirmed,
            'supportConfirmedBy': user['id'], 'replayed': False}
