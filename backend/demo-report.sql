WITH demo_cases(number, title, account_code, detail) AS (
    VALUES
        (1, 'Cộng dồn một tháng lịch', 'DEMO-01', 'VIP đang tới 31/01/2027 được cộng thành 28/02/2027.'),
        (2, 'Gửi lại cùng lần nâng cấp', 'DEMO-01', 'Sự kiện DEMO-FIRST-B được gửi hai lần, người mời nhận đúng một thưởng và một thông báo.'),
        (3, 'Người được mời gia hạn tiếp', 'DEMO-01', 'DEMO-02 mua VIP hai lần; lần gia hạn tiếp theo giữ nguyên số thưởng của người mời.'),
        (4, 'Tài khoản Thường nhận thưởng', 'DEMO-03', 'Tài khoản Thường nhận một tháng từ ngày cấp thưởng khi DEMO-04 mua VIP lần đầu.'),
        (5, 'Tài khoản nội bộ nhận hướng dẫn', 'DEMO-05', 'Khi DEMO-03 mua VIP lần đầu, người mời nội bộ nhận thông báo liên hệ chăm sóc khách hàng.')
)
SELECT json_object(
    'status', 'ok',
    'sample_date', '2026-11-11',
    'cases', json((
        SELECT json_group_array(json_object(
            'number', c.number, 'title', c.title, 'account_code', a.account_code,
            'detail', c.detail, 'vip_expires_at', a.vip_expires_at,
            'reward_vip_expires_at', (
                SELECT r.reward_vip_expires_at FROM account_referrals r
                WHERE r.inviter_account_id = a.id AND r.reward_status = 'granted'
                ORDER BY r.reward_granted_at, r.id LIMIT 1
            ),
            'reward_count', (SELECT COUNT(*) FROM account_referrals r WHERE r.inviter_account_id = a.id AND r.reward_status = 'granted'),
            'notifications', json((
                SELECT json_group_array(json_object('kind', n.kind, 'body', n.body, 'created_at', n.created_at))
                FROM notifications n WHERE n.account_id = a.id
            ))
        ))
        FROM demo_cases c JOIN accounts a ON a.account_code = c.account_code AND a.is_demo = 1
        ORDER BY c.number
    )),
    'questions', json((
        SELECT json_group_array(json_object(
            'code', q.question_code, 'title', t.title,
            'prompt', json(v.prompt_json), 'solution', json(v.solution_steps_json)
        ))
        FROM questions q
        JOIN question_versions v ON v.question_id = q.id AND v.revision = 1
        JOIN topics t ON t.id = q.topic_id
        WHERE q.question_code IN ('DEMO-Q-01', 'DEMO-Q-02', 'DEMO-Q-03', 'DEMO-Q-04', 'DEMO-Q-05')
    )),
    'assets', json((
        SELECT json_group_array(json_object(
            'id', a.id, 'url', a.url, 'width', a.width, 'height', a.height, 'alt', a.alt_text
        )) FROM media_assets a WHERE a.storage_key = 'demo/rectangle.svg'
    ))
) AS report;
