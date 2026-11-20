"""Versioned draft notices for the local website review; no regulatory approval claim."""
import hashlib
import json
from pathlib import Path
from .platform_api import APIError, stamp

VERSION = '2026-11-17-draft1'
SLUGS = ('dieu-khoan', 'bao-ve-du-lieu', 'thanh-toan-va-cung-cap', 'huy-va-hoan-tien', 'khieu-nai')

def validate_consent(body):
    consent = body.get('legalConsent')
    if not isinstance(consent, dict) or consent.get('accepted') is not True or consent.get('version') != VERSION:
        raise APIError('Người đại diện cần đọc và đồng ý điều khoản, thông báo dữ liệu đang hiển thị.')
    result = {}
    for key, maximum in (('name', 120), ('contact', 180)):
        value = consent.get(key)
        if not isinstance(value, str) or not 2 <= len(value.strip()) <= maximum or any(ord(c)<32 for c in value):
            raise APIError('Hãy điền tên và thông tin liên hệ của người đại diện, không dùng thông tin liên hệ riêng của trẻ.')
        result[key] = value.strip()
    if consent.get('role') not in ('parent', 'guardian'):
        raise APIError('Hãy xác nhận vai trò phụ huynh hoặc người đại diện.')
    result['role'] = consent['role']
    return result

def record_consent(db, account_id, body):
    consent = validate_consent(body)
    folder = Path(__file__).resolve().parent.parent/'frontend'/'legal'
    documents = {slug: (folder/slug/'index.html').read_text(encoding='utf-8') for slug in SLUGS}
    raw = json.dumps(documents, ensure_ascii=False, sort_keys=True)
    digest = hashlib.sha256(raw.encode()).hexdigest()
    prior = db.execute('SELECT content_sha256 FROM website_policy_snapshots WHERE version=?', (VERSION,)).fetchone()
    if prior and prior[0] != digest:
        raise APIError('Bản chính sách vừa đổi; cần phát hành phiên bản mới trước khi nhận đồng ý.',409)
    db.execute('INSERT OR IGNORE INTO website_policy_snapshots VALUES(?,?,?,?)',(VERSION,raw,digest,stamp()))
    db.execute('INSERT INTO website_account_consents(account_id,version,representative_name,representative_contact,representative_role,accepted_at) VALUES(?,?,?,?,?,?)',
               (account_id, VERSION, consent['name'],consent['contact'],consent['role'],stamp()))

def public_info(db):
    from .website_support import get_business
    business = get_business(db)
    values=business['business']
    aliases={label:values.get(key,'') for label,key in {
        'businessName':'legal_name','taxId':'tax_code','registrationNumber':'registration_number','representative':'representative','address':'address',
        'supportEmail':'email','supportPhone':'phone','privacyEmail':'email','complaintEmail':'email'}.items()}
    return {**business, **aliases, 'version': VERSION, 'draft': True,
            'notice':'Bản thử nghiệm trên localhost; chính sách chờ chủ quản duyệt.',
            'documents': {slug:'/'+slug+'/' for slug in SLUGS}}
