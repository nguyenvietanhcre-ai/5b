"""Server-owned subscription prices and immutable paid calendar periods."""
from calendar import monthrange
from datetime import datetime
from . import platform_api as api

PRICES={'VIP':{'month':100000,'year':1000000},'VIP+':{'month':200000,'year':2000000}}

def product(plan,period):
    if not isinstance(plan,str) or plan not in PRICES or not isinstance(period,str) or period not in ('month','year'):
        raise api.APIError('Gói hoặc kỳ đăng ký không hợp lệ.')
    return {'plan':plan,'period':period,'months':12 if period=='year' else 1,'amount':PRICES[plan][period],'monthlyPrice':PRICES[plan]['month']}

def add_months(start,months):
    local=datetime.fromisoformat(start).astimezone(api.VN)
    year,month=divmod(local.year*12+local.month-1+months,12);month+=1
    return api.stamp(local.replace(year=year,month=month,day=min(local.day,monthrange(year,month)[1])))

def active_annual_cycle(db,session):
    current=api.stamp()
    row=db.execute("SELECT id,subscription_plan,subscription_starts_at,subscription_ends_at FROM payment_orders "
        "WHERE account_id=? AND status='paid' AND purchase_type='subscription' AND kind='vip' AND fee_id IS NULL "
        "AND subscription_period='year' AND vip_months=12 AND subscription_starts_at<=? AND subscription_ends_at>? "
        "ORDER BY CASE subscription_plan WHEN 'VIP+' THEN 0 ELSE 1 END,subscription_starts_at DESC,id DESC LIMIT 1",
        (session['account_id'],current,current)).fetchone()
    return {'start':row['subscription_starts_at'],'end':row['subscription_ends_at'],'limit':3600,'dailyLimit':30,'period':'year'} if row else None
