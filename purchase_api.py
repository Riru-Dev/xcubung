from datetime import datetime, timezone
import json, uuid, base64, qrcode, time, requests

from api_request import send_api_request
from crypto_helper import (
    API_KEY,
    build_encrypted_field,
    decrypt_xdata,
    encryptsign_xdata,
    java_like_timestamp,
    get_x_signature_payment,
    get_x_signature_bounty,
)

# =======================
# Get Payment Methods
# =======================
def get_payment_methods(api_key: str, tokens: dict, token_confirmation: str, payment_target: str):
    path = "payments/api/v8/payment-methods-option"
    payload = {
        "payment_type": "PURCHASE",
        "is_enterprise": False,
        "payment_target": payment_target,
        "lang": "en",
        "is_referral": False,
        "token_confirmation": token_confirmation,
    }
    res = send_api_request(api_key, path, payload, tokens["id_token"], "POST")
    if res.get("status") != "SUCCESS":
        return {"error": "Failed to fetch payment methods", "raw": res}
    return res["data"]

# =======================
# Multipayment Settlement
# =======================
def settlement_multipayment(
    api_key: str,
    tokens: dict,
    token_payment: str,
    ts_to_sign: int,
    payment_target: str,
    price: int,
    wallet_number: str,
    item_name: str = "",
    payment_method: str = "DANA",
):
    path = "payments/api/v8/settlement-multipayment/ewallet"
    payload = {
        "akrab": {"akrab_members": [], "akrab_parent_alias": "", "members": []},
        "can_trigger_rating": False,
        "total_discount": 0,
        "coupon": "",
        "payment_for": "BUY_PACKAGE",
        "topup_number": "",
        "is_enterprise": False,
        "autobuy": {"is_using_autobuy": False, "activated_autobuy_code": "", "autobuy_threshold_setting": {"label": "", "type": "", "value": 0}},
        "cc_payment_type": "",
        "access_token": tokens["access_token"],
        "is_myxl_wallet": False,
        "wallet_number": wallet_number,
        "additional_data": {
            "original_price": price,
            "is_spend_limit_temporary": False,
            "migration_type": "",
            "spend_limit_amount": 0,
            "is_spend_limit": False,
            "tax": 0,
            "benefit_type": "",
            "quota_bonus": 0,
            "cashtag": "",
            "is_family_plan": False,
            "combo_details": [],
            "is_switch_plan": False,
            "discount_recurring": 0,
            "has_bonus": False,
            "discount_promo": 0,
        },
        "total_amount": price,
        "total_fee": 0,
        "is_use_point": False,
        "lang": "en",
        "items": [{"item_code": payment_target, "product_type": "", "item_price": price, "item_name": item_name, "tax": 0}],
        "verification_token": token_payment,
        "payment_method": payment_method,
        "timestamp": ts_to_sign,  # harus dari /pay/methods
    }

    encrypted_payload = encryptsign_xdata(api_key, "POST", path, tokens["id_token"], payload)
    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = xtime // 1000
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()

    body = encrypted_payload["encrypted_body"]
    x_sig = get_x_signature_payment(api_key, tokens["access_token"], ts_to_sign, payment_target, token_payment, payment_method)

    headers = {
        "host": "api.myxl.xlaxiata.co.id",
        "content-type": "application/json; charset=utf-8",
        "user-agent": "myXL / 8.6.0(1179)",
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }

    url = f"https://api.myxl.xlaxiata.co.id/{path}"
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)

    try:
        return decrypt_xdata(api_key, resp.json())
    except Exception as e:
        return {"error": str(e), "raw": resp.text}

def show_multipayment(api_key, tokens, package_option_code, token_confirmation, price, method, wallet_number=""):
    pm_data = get_payment_methods(api_key, tokens, token_confirmation, package_option_code)
    if "error" in pm_data:
        return pm_data

    token_payment = pm_data["token_payment"]
    ts_to_sign = pm_data["timestamp"]

    return settlement_multipayment(
        api_key,
        tokens,
        token_payment,
        ts_to_sign,
        package_option_code,
        price,
        wallet_number,
        "",
        method,
    )

# =======================
# QRIS Settlement
# =======================
def settlement_qris(api_key, tokens, token_payment, ts_to_sign, payment_target, price, item_name=""):
    path = "payments/api/v8/settlement-multipayment/qris"
    payload = {
        "akrab": {"akrab_members": [], "akrab_parent_alias": "", "members": []},
        "can_trigger_rating": False,
        "total_discount": 0,
        "coupon": "",
        "payment_for": "BUY_PACKAGE",
        "topup_number": "",
        "is_enterprise": False,
        "access_token": tokens["access_token"],
        "is_myxl_wallet": False,
        "additional_data": {"original_price": price, "is_spend_limit_temporary": False, "migration_type": "", "spend_limit_amount": 0, "is_spend_limit": False, "tax": 0, "benefit_type": "", "quota_bonus": 0, "cashtag": "", "is_family_plan": False, "combo_details": [], "is_switch_plan": False, "discount_recurring": 0, "has_bonus": False, "discount_promo": 0},
        "total_amount": price,
        "total_fee": 0,
        "is_use_point": False,
        "lang": "en",
        "items": [{"item_code": payment_target, "product_type": "", "item_price": price, "item_name": item_name, "tax": 0}],
        "verification_token": token_payment,
        "payment_method": "QRIS",
        "timestamp": ts_to_sign,
    }

    encrypted_payload = encryptsign_xdata(api_key, "POST", path, tokens["id_token"], payload)
    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = xtime // 1000
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()

    body = encrypted_payload["encrypted_body"]
    x_sig = get_x_signature_payment(api_key, tokens["access_token"], ts_to_sign, payment_target, token_payment, "QRIS")

    headers = {
        "host": "api.myxl.xlaxiata.co.id",
        "content-type": "application/json; charset=utf-8",
        "user-agent": "myXL / 8.6.0(1179)",
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }

    url = f"https://api.myxl.xlaxiata.co.id/{path}"
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)

    try:
        return decrypt_xdata(api_key, resp.json())
    except Exception as e:
        return {"error": str(e), "raw": resp.text}

def get_qris_code(api_key, tokens, transaction_id: str):
    path = "payments/api/v8/pending-detail"
    payload = {"transaction_id": transaction_id, "is_enterprise": False, "lang": "en", "status": ""}
    res = send_api_request(api_key, path, payload, tokens["id_token"], "POST")
    if res.get("status") != "SUCCESS":
        return {"error": "Failed to fetch QRIS code", "raw": res}
    return res["data"]

def show_qris_payment(api_key, tokens, package_option_code, token_confirmation, price):
    pm_data = get_payment_methods(api_key, tokens, token_confirmation, package_option_code)
    if "error" in pm_data:
        return pm_data

    token_payment = pm_data["token_payment"]
    ts_to_sign = pm_data["timestamp"]

    trx = settlement_qris(api_key, tokens, token_payment, ts_to_sign, package_option_code, price, "")
    if not trx:
        return {"error": "Failed to create QRIS transaction"}

    qris = get_qris_code(api_key, tokens, trx["data"]["transaction_code"])
    return qris
    
def settlement_bounty(
    api_key: str,
    tokens: dict,
    token_confirmation: str,
    ts_to_sign: int,
    payment_target: str,
    price: int,
    item_name: str = "",
):
    path = "api/v8/personalization/bounties-exchange"
    payload = {
        "total_discount": 0,
        "is_enterprise": False,
        "payment_token": "",
        "token_payment": "",
        "activated_autobuy_code": "",
        "cc_payment_type": "",
        "is_myxl_wallet": False,
        "pin": "",
        "ewallet_promo_id": "",
        "members": [],
        "total_fee": 0,
        "fingerprint": "",
        "autobuy_threshold_setting": {"label": "", "type": "", "value": 0},
        "is_use_point": False,
        "lang": "en",
        "payment_method": "BALANCE",
        "timestamp": ts_to_sign,
        "points_gained": 0,
        "can_trigger_rating": False,
        "akrab_members": [],
        "akrab_parent_alias": "",
        "referral_unique_code": "",
        "coupon": "",
        "payment_for": "REDEEM_VOUCHER",
        "with_upsell": False,
        "topup_number": "",
        "stage_token": "",
        "authentication_id": "",
        "encrypted_payment_token": build_encrypted_field(urlsafe_b64=True),
        "token": "",
        "token_confirmation": token_confirmation,
        "access_token": tokens["access_token"],
        "wallet_number": "",
        "encrypted_authentication_id": build_encrypted_field(urlsafe_b64=True),
        "additional_data": {
            "original_price": 0,
            "is_spend_limit_temporary": False,
            "migration_type": "",
            "akrab_m2m_group_id": "",
            "spend_limit_amount": 0,
            "is_spend_limit": False,
            "mission_id": "",
            "tax": 0,
            "benefit_type": "",
            "quota_bonus": 0,
            "cashtag": "",
            "is_family_plan": False,
            "combo_details": [],
            "is_switch_plan": False,
            "discount_recurring": 0,
            "is_akrab_m2m": False,
            "balance_type": "",
            "has_bonus": False,
            "discount_promo": 0,
        },
        "total_amount": 0,
        "is_using_autobuy": False,
        "items": [
            {
                "item_code": payment_target,
                "product_type": "",
                "item_price": price,
                "item_name": item_name,
                "tax": 0,
            }
        ],
    }

    encrypted_payload = encryptsign_xdata(
        api_key=api_key, method="POST", path=path, id_token=tokens["id_token"], payload=payload
    )

    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = xtime // 1000
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()

    body = encrypted_payload["encrypted_body"]

    x_sig = get_x_signature_bounty(
        api_key=api_key,
        access_token=tokens["access_token"],
        sig_time_sec=ts_to_sign,
        package_code=payment_target,
        token_payment=token_confirmation,
    )

    headers = {
        "host": "api.myxl.xlaxiata.co.id",
        "content-type": "application/json; charset=utf-8",
        "user-agent": "myXL / 8.6.0(1179)",
        "x-api-key": API_KEY,
        "authorization": f"Bearer {tokens['id_token']}",
        "x-hv": "v3",
        "x-signature-time": str(sig_time_sec),
        "x-signature": x_sig,
        "x-request-id": str(uuid.uuid4()),
        "x-request-at": java_like_timestamp(x_requested_at),
        "x-version-app": "8.6.0",
    }

    url = f"https://api.myxl.xlaxiata.co.id/{path}"
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)

    try:
        return decrypt_xdata(api_key, resp.json())
    except Exception as e:
        return {"error": str(e), "raw": resp.text}