"""Record a server-confirmed VIP purchase once and apply its database triggers."""

import sqlite3
from contextlib import closing


def record_vip_purchase(path, account_id, payment_ref, months, confirmed_at):
    if not payment_ref or not isinstance(months, int) or isinstance(months, bool) or not 1 <= months <= 120:
        raise ValueError('Invalid confirmed VIP purchase')
    with closing(sqlite3.connect(path, timeout=15)) as connection:
        connection.execute('PRAGMA foreign_keys = ON')
        connection.execute('BEGIN IMMEDIATE')
        with connection:
            existing = connection.execute(
                'SELECT id, account_id, months FROM vip_purchases WHERE payment_ref = ?', (payment_ref,)
            ).fetchone()
            if existing:
                if existing[1:] != (account_id, months):
                    raise ValueError('Payment reference already belongs to another purchase')
                return {'purchase_id': existing[0], 'created': False}
            purchase_id = connection.execute(
                'INSERT INTO vip_purchases (account_id, payment_ref, months, confirmed_at) VALUES (?, ?, ?, ?)',
                (account_id, payment_ref, months, confirmed_at)
            ).lastrowid
    return {'purchase_id': purchase_id, 'created': True}
