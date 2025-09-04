from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os

# Import project modules
import crypto_helper as ch
from api_request import (
    get_otp, submit_otp, get_new_token, get_profile,
    get_balance, send_api_request, get_family, get_package, purchase_package
)
from purchase_api import (
    get_payment_methods,
    get_qris_code,
    show_qris_payment,
    show_multipayment
)

# Allow overriding crypto endpoints and API_KEY at runtime
ch.API_KEY = os.getenv("API_KEY", ch.API_KEY)
ch.XDATA_ENCRYPT_SIGN_URL = os.getenv("XDATA_ENCRYPT_SIGN_URL", ch.XDATA_ENCRYPT_SIGN_URL)
ch.XDATA_DECRYPT_URL = os.getenv("XDATA_DECRYPT_URL", ch.XDATA_DECRYPT_URL)
ch.PAYMENT_SIGN_URL = os.getenv("PAYMENT_SIGN_URL", ch.PAYMENT_SIGN_URL)
ch.BOUNTY_SIGN_URL = os.getenv("BOUNTY_SIGN_URL", ch.BOUNTY_SIGN_URL)
ch.AX_SIGN_URL = os.getenv("AX_SIGN_URL", ch.AX_SIGN_URL)

def _api_key() -> str:
    return os.getenv("API_KEY", ch.API_KEY)

# === Wrapper biar server gak crash ===
def safe_call(func, *args, **kwargs):
    try:
        return func(*args, **kwargs)   # kalau XL API balikin dict → dilepas raw
    except Exception as e:
        return {"error": str(e)}       # kalau error Python → balikin JSON aman

# === App setup ===
app = FastAPI(title="myXL Unofficial API", version="0.1.0", root_path="/api")

# CORS
origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = [o.strip() for o in origins.split(",")] if origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ==== Schemas ====
class OTPRequest(BaseModel):
    contact: str = Field(description="MSISDN starting with 628...")

class OTPVerify(BaseModel):
    contact: str
    code: str = Field(min_length=6, max_length=6)

class RefreshRequest(BaseModel):
    refresh_token: str

class Tokens(BaseModel):
    access_token: str
    id_token: str
    refresh_token: str | None = None

class FamilyRequest(BaseModel):
    tokens: Tokens
    family_code: str

class PackageDetailsRequest(BaseModel):
    tokens: Tokens
    package_option_code: str

class PurchaseInitRequest(BaseModel):
    tokens: Tokens
    package_option_code: str
    price_override: int | None = None

class PaymentInit(BaseModel):
    tokens: Tokens
    token_confirmation: str
    payment_target: str

class QRRequest(BaseModel):
    tokens: Tokens
    token_confirmation: str
    payment_target: str
    
class PurchasePayRequest(BaseModel):
    tokens: Tokens
    package_option_code: str
    token_payment: str
    token_confirmation: str
    price_override: int | None = None
    method: str = "BALANCE"
    wallet_number: str | None = ""   # <--- tambahin ini

# ==== Routes ====
@app.get("/")
def root():
    return {"ok": True, "name": "myXL API", "version": "0.1.0"}

@app.post("/otp/request")
def request_otp(body: OTPRequest):
    return safe_call(get_otp, body.contact)

@app.post("/otp/verify")
def verify_otp(body: OTPVerify):
    return safe_call(submit_otp, _api_key(), body.contact, body.code)

@app.post("/token/refresh")
def refresh_token(body: RefreshRequest):
    return safe_call(get_new_token, body.refresh_token)

@app.post("/profile")
def profile(tokens: Tokens):
    return safe_call(get_profile, _api_key(), tokens.access_token, tokens.id_token)

@app.post("/balance")
def balance(tokens: Tokens):
    return safe_call(get_balance, _api_key(), tokens.id_token)

@app.post("/packages/details")
def packages_details(tokens: Tokens):
    path = "api/v8/packages/quota-details"
    payload = {"is_enterprise": False, "lang": "en"}
    return safe_call(send_api_request, _api_key(), path, payload, tokens.id_token, "POST")

@app.post("/packages/family")
def packages_by_family(body: FamilyRequest):
    return safe_call(get_family, _api_key(), body.tokens.model_dump(), body.family_code)

@app.post("/packages/option")
def package_details(body: PackageDetailsRequest):
    return safe_call(get_package, _api_key(), body.tokens.model_dump(), body.package_option_code)

@app.post("/packages/purchase/init")
def purchase_init(body: PurchaseInitRequest):
    package_details = safe_call(
        get_package,
        _api_key(),
        body.tokens.model_dump(),
        body.package_option_code
    )

    if not package_details or "token_confirmation" not in package_details:
        return {"error": "Failed to init purchase"}

    return {
        "status": "INIT",
        "data": {
            "package_details": package_details
        }
    }

@app.post("/pay/methods")
def pay_methods(body: PaymentInit):
    return safe_call(
        get_payment_methods,
        _api_key(),
        body.tokens.model_dump(),
        body.token_confirmation,
        body.payment_target
    )

@app.post("/packages/purchase/pay")
def purchase_pay(body: PurchasePayRequest):
    if body.method == "BALANCE":
        return safe_call(
            purchase_package,
            _api_key(),
            body.tokens.model_dump(),
            body.package_option_code,
            body.price_override
        )
    elif body.method == "QRIS":
        return safe_call(
            show_qris_payment,
            _api_key(),
            body.tokens.model_dump(),
            body.package_option_code,
            body.token_confirmation,
            body.price_override or 0
        )
    elif body.method in ["DANA", "OVO", "GOPAY", "SHOPEEPAY"]:
        return safe_call(
            show_multipayment,
            _api_key(),
            body.tokens.model_dump(),
            body.package_option_code,
            body.token_confirmation,
            body.price_override or 0,
            body.method,
            body.wallet_number or ""
        )
    else:
        return {"error": f"Payment method {body.method} belum diimplementasi."}

@app.post("/pay/qris/code")
def pay_qris_code(body: QRRequest):
    return safe_call(get_qris_code, _api_key(), body.tokens.model_dump(), body.token_confirmation, body.payment_target)
