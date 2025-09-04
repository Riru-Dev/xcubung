from datetime import datetime, timezone
import json
import uuid
import base64
import qrcode
import time
import requests

from api_request import send_api_request
from crypto_helper import (
    API_KEY,
    build_encrypted_field,
    decrypt_xdata,
    encryptsign_xdata,
    java_like_timestamp,
    get_x_signature_payment,
    get_x_signature_bounty
)


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


def settlement_multipayment(
    api_key: str,
    tokens: dict,
    token_payment: str,
    ts_to_sign: int,
    payment_target: str,
    price: int,
    wallet_number: str,
    payment_method: str,
    item_name: str = "",
):
    path = "payments/api/v8/settlement-multipayment/ewallet"
    settlement_payload = {
        "akrab": {"akrab_members": [], "akrab_parent_alias": "", "members": []},
        "can_trigger_rating": False,
        "total_discount": 0,
        "coupon": "",
        "payment_for": "BUY_PACKAGE",
        "topup_number": "",
        "is_enterprise": False,
        "autobuy": {
            "is_using_autobuy": False,
            "activated_autobuy_code": "",
            "autobuy_threshold_setting": {"label": "", "type": "", "value": 0},
        },
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
        "items": [
            {
                "item_code": payment_target,
                "product_type": "",
                "item_price": price,
                "item_name": item_name,
                "tax": 0,
            }
        ],
        "verification_token": token_payment,
        "payment_method": payment_method,
        "timestamp": int(time.time()),  # awalnya pakai time.time()
    }

    # encrypt + sign
    encrypted_payload = encryptsign_xdata(
        api_key=api_key,
        method="POST",
        path=path,
        id_token=tokens["id_token"],
        payload=settlement_payload,
    )

    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = xtime // 1000
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()

    # override timestamp -> ts_to_sign
    settlement_payload["timestamp"] = ts_to_sign
    body = encrypted_payload["encrypted_body"]

    # signature khusus payment
    x_sig = get_x_signature_payment(
        api_key, tokens["access_token"], ts_to_sign, payment_target, token_payment, payment_method
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
    except Exception:
        return {"error": "decrypt_failed", "raw": resp.text}


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
        method,
    )


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
        "autobuy": {
            "is_using_autobuy": False,
            "activated_autobuy_code": "",
            "autobuy_threshold_setting": {"label": "", "type": "", "value": 0},
        },
        "access_token": tokens["access_token"],
        "is_myxl_wallet": False,
        "additional_data": {"original_price": price},
        "total_amount": price,
        "total_fee": 0,
        "is_use_point": False,
        "lang": "en",
        "items": [{"item_code": payment_target, "product_type": "", "item_price": price, "item_name": item_name, "tax": 0}],
        "verification_token": token_payment,
        "payment_method": "QRIS",
        "timestamp": int(time.time()),
    }

    encrypted_payload = encryptsign_xdata(api_key, "POST", path, tokens["id_token"], payload)

    xtime = int(encrypted_payload["encrypted_body"]["xtime"])
    sig_time_sec = xtime // 1000
    x_requested_at = datetime.fromtimestamp(sig_time_sec, tz=timezone.utc).astimezone()

    payload["timestamp"] = ts_to_sign
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
        dec = decrypt_xdata(api_key, resp.json())
        if dec["status"] != "SUCCESS":
            return {"error": "settlement_failed", "raw": dec}
        return dec["data"]["transaction_code"]
    except Exception:
        return {"error": "decrypt_failed", "raw": resp.text}


def show_qris_payment(api_key, tokens, package_option_code, token_confirmation, price):
    pm_data = get_payment_methods(api_key, tokens, token_confirmation, package_option_code)
    if "error" in pm_data:
        return pm_data

    token_payment = pm_data["token_payment"]
    ts_to_sign = pm_data["timestamp"]

    txid = settlement_qris(api_key, tokens, token_payment, ts_to_sign, package_option_code, price, "")
    if not txid:
        return {"error": "failed to create qris transaction"}

    # ambil QR
    path = "payments/api/v8/pending-detail"
    payload = {"transaction_id": txid, "is_enterprise": False, "lang": "en", "status": ""}
    res = send_api_request(api_key, path, payload, tokens["id_token"], "POST")

    if res.get("status") != "SUCCESS":
        return {"error": "failed to fetch qris", "raw": res}

    return {"transaction_id": txid, "qr_code": res["data"]["qr_code"]}
