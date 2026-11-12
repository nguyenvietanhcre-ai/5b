"""Synthetic-only HTTP checks for the native Durable Object financial path."""
import hashlib
import hmac
import http.cookiejar
import json
import secrets
import time
from datetime import datetime, timedelta, timezone
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPCookieProcessor, ProxyHandler, Request, build_opener


class Client:
    def __init__(self, origin):
        self.origin, self.csrf = origin, ''
        self.opener = build_opener(ProxyHandler({}), HTTPCookieProcessor(http.cookiejar.CookieJar()))
        self.last_headers = {}

    def call(self, path, body=None, *, expected=200, headers=None):
        request_headers = {'Origin':self.origin,'Content-Type':'application/json','X-CSRF-Token':self.csrf}
        request_headers.update(headers or {})
        raw = body if isinstance(body,bytes) else json.dumps(body,ensure_ascii=False).encode('utf-8') if body is not None else None
        request = Request(self.origin+path,raw,request_headers,method='POST' if body is not None else 'GET')
        try:
            response = self.opener.open(request,timeout=60)
        except HTTPError as error:
            response = error
        with response:
            status, data = response.code, response.read()
            self.last_headers = {key.lower():value for key,value in response.headers.items()}
        if status != expected:
            # Avoid printing response bodies/credentials/row values on failure.
            raise AssertionError('Financial HTTP QA status mismatch: '+str(status)+' expected '+str(expected))
        payload = json.loads(data)
        if payload.get('csrf'):
            self.csrf = payload['csrf']
        return payload


def account_snapshot(state):
    account = state['account']
    return {key:account[key] for key in ('id','membership','vipExpiresAt','notificationTotal','referralTotal','referrals')}


def run_financial_qa(origin, fixture, webhook_secret):
    parsed = urlsplit(origin)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1','localhost') or parsed.path or parsed.query or parsed.fragment:
        raise ValueError('Financial QA is restricted to an isolated loopback runtime')
    if len(webhook_secret) < 32:
        raise ValueError('Synthetic webhook fixture secret is missing')

    def register(invite=''):
        client = Client(origin)
        local = datetime.now(timezone(timedelta(hours=7)))
        school_year = local.year - (local.month < 7)
        state = client.call('/api/v1/auth/register',{'login':'qa-finance-'+secrets.token_hex(9),
            'password':secrets.token_urlsafe(22),'name':'Học sinh kiểm thử','birthYear':school_year-10,'inviteCode':invite})
        return client,state

    def session(client):
        return client.call('/api/v1/session')

    def login(credentials):
        client = Client(origin)
        state = client.call('/api/v1/auth/login',{'login':credentials['login'],'password':credentials['password']})
        return client,state

    webhook_client = Client(origin)

    def event(order):
        return {'id':secrets.randbelow(10**12)+1,'gateway':order['bank'],
                'transactionDate':datetime.now(timezone(timedelta(hours=7))).strftime('%Y-%m-%d %H:%M:%S'),
                'accountNumber':order['bankAccount'],'subAccount':'','code':order['reference'],
                'content':order['reference']+' phụ huynh chuyển giúp','transferType':'in',
                'transferAmount':order['amount'],'description':'Giao dịch giả chỉ dùng QA',
                'referenceCode':'QA-'+secrets.token_hex(9),'accumulated':0}

    def send(receipt, expected=201, *, unsigned=False, tampered=False):
        raw = json.dumps(receipt,ensure_ascii=False,separators=(',',':')).encode('utf-8')
        timestamp = str(int(time.time()))
        signature = hmac.new(webhook_secret.encode('utf-8'),timestamp.encode('ascii')+b'.'+raw,hashlib.sha256).hexdigest()
        headers = {} if unsigned else {'X-SePay-Timestamp':timestamp,'X-SePay-Signature':'sha256='+signature}
        payload = webhook_client.call('/api/webhooks/sepay',raw+b' ' if tampered else raw,expected=expected,headers=headers)
        if expected == 201:
            assert payload == {'success':True}, 'Financial webhook acknowledgement mismatch'
            assert webhook_client.last_headers.get('cache-control') == 'no-store', 'Webhook cache policy mismatch'

    inviter,inviter_state = register()
    buyer,buyer_state = register(inviter_state['state']['inviteCode'])
    stranger,stranger_state = register()
    assert buyer_state['state']['invitedBy'] == inviter_state['state']['inviteCode'], 'Saved referral mismatch'
    before_inviter = account_snapshot(inviter.call('/api/v1/session'))
    before_buyer = account_snapshot(buyer_state)
    before_stranger = account_snapshot(stranger_state)
    order = buyer.call('/api/v1/payments',{})['order']
    assert order['automationEnabled'] is True, 'Synthetic webhook configuration is disabled'
    assert order['account_id'] == buyer_state['account']['id'], 'VIP order owner mismatch'
    receipt = event(order)
    send(receipt,401,unsigned=True)
    send(receipt,401,tampered=True)
    assert account_snapshot(session(buyer)) == before_buyer, 'Unsigned/tampered receipt changed buyer'
    assert account_snapshot(session(inviter)) == before_inviter, 'Unsigned/tampered receipt changed referrer'
    send(receipt)
    after_buyer = account_snapshot(session(buyer))
    after_inviter = account_snapshot(session(inviter))
    assert after_buyer['id'] == before_buyer['id'] and after_buyer['membership'] == 'VIP' and after_buyer['vipExpiresAt'], 'Buyer VIP did not settle'
    assert after_inviter['id'] == before_inviter['id'] and after_inviter['membership'] == 'VIP' and after_inviter['vipExpiresAt'], 'Saved referrer was not rewarded'
    assert after_inviter['referralTotal'] == 1 and len(after_inviter['referrals']) == 1, 'Unexpected referral attribution'
    relation = after_inviter['referrals'][0]
    assert relation['reward_status'] == 'granted' and relation['first_vip_upgraded_at'] and relation['reward_granted_at'], 'First-purchase referral qualification missing'
    assert account_snapshot(session(stranger)) == before_stranger, 'Unrelated account changed'
    assert buyer.call('/api/v1/payments/'+str(order['id']))['order']['status'] == 'paid', 'VIP order not paid'
    send(receipt)
    send({**receipt,'transferAmount':receipt['transferAmount']+1},409)
    assert account_snapshot(session(buyer)) == after_buyer, 'Duplicate/conflicting receipt upgraded buyer twice'
    assert account_snapshot(session(inviter)) == after_inviter, 'Duplicate/conflicting receipt rewarded referrer twice'
    renewal = buyer.call('/api/v1/payments',{})['order']
    assert renewal['id'] != order['id'], 'Renewal reused paid order'
    send(event(renewal))
    assert session(buyer)['account']['vipExpiresAt'] > after_buyer['vipExpiresAt'], 'Renewal did not extend buyer'
    assert account_snapshot(session(inviter)) == after_inviter, 'Renewal rewarded referrer again'
    assert account_snapshot(session(stranger)) == before_stranger, 'Renewal changed unrelated account'

    owner,owner_state = login(fixture['feeOwner'])
    other,other_state = login(fixture['feeOther'])
    before_owner, before_other = account_snapshot(owner_state),account_snapshot(other_state)
    class_id = fixture['classId']
    def fees(client):
        return {row['id']:row for row in client.call('/api/v1/classes/'+str(class_id))['fees']}
    owner_fees,other_fees = fees(owner),fees(other)
    fee_id,next_fee,other_fee = fixture['feeId'],fixture['nextFeeId'],fixture['otherFeeId']
    assert not owner_fees[fee_id]['paid_at'] and not owner_fees[next_fee]['paid_at'] and not other_fees[other_fee]['paid_at'], 'Tuition fixture must begin unpaid'
    other.call('/api/v1/payments',{'feeId':fee_id},expected=404)
    tuition = owner.call('/api/v1/payments',{'feeId':fee_id})['order']
    assert tuition['kind'] == 'tuition' and tuition['account_id'] == before_owner['id'], 'Tuition owner/product mismatch'
    tuition_receipt = event(tuition)
    send(tuition_receipt)
    after_owner,after_other = account_snapshot(session(owner)),account_snapshot(session(other))
    assert after_owner['membership'] == before_owner['membership'] and after_owner['vipExpiresAt'] == before_owner['vipExpiresAt'], 'Tuition unexpectedly grants VIP'
    assert after_other == before_other, 'Tuition unexpectedly qualifies/rewards referral or changes other student'
    paid_fees = fees(owner)
    assert paid_fees[fee_id]['paid_at'], 'Correct tuition fee not completed'
    assert not paid_fees[next_fee]['paid_at'], 'Different tuition month changed'
    assert not fees(other)[other_fee]['paid_at'], 'Different student tuition changed'
    assert owner.call('/api/v1/payments/'+str(tuition['id']))['order']['status'] == 'paid', 'Tuition order not paid'
    send(tuition_receipt)
    assert account_snapshot(session(owner)) == after_owner, 'Tuition replay changed account or notifications'
    assert account_snapshot(session(other)) == after_other, 'Tuition replay changed referrer'
    return {'initialVipCorrectAccount':True,'referralCorrectAccount':True,'unsignedAndTamperedRejected':True,
            'receiptReplayIdempotent':True,'conflictingReplayRejected':True,'renewalRewardsOnlyOnce':True,
            'tuitionCorrectStudentAndMonth':True,'tuitionGrantsNoVipOrReferral':True,'tuitionReplayIdempotent':True}
