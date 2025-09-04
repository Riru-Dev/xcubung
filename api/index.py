
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import os

# Import project modules
import crypto_helper as ch
from api_request import get_otp, submit_otp, get_new_token, get_profile, get_balance, send_api_request, get_family, get_families, get_package
from purchase_api import get_payment_methods, get_qris_code, settlement_qris, settlement_multipayment, settlement_bounty

# Allow overriding crypto endpoints and API_KEY at runtime
ch.API_KEY = os.getenv("API_KEY", ch.API_KEY)
ch.XDATA_ENCRYPT_SIGN_URL = os.getenv("XDATA_ENCRYPT_SIGN_URL", ch.XDATA_ENCRYPT_SIGN_URL)
ch.XDATA_DECRYPT_URL = os.getenv("XDATA_DECRYPT_URL", ch.XDATA_DECRYPT_URL)
ch.PAYMENT_SIGN_URL = os.getenv("PAYMENT_SIGN_URL", ch.PAYMENT_SIGN_URL)
ch.BOUNTY_SIGN_URL = os.getenv("BOUNTY_SIGN_URL", ch.BOUNTY_SIGN_URL)
ch.AX_SIGN_URL = os.getenv("AX_SIGN_URL", ch.AX_SIGN_URL)

def _api_key() -> str:
    key = os.getenv("API_KEY", ch.API_KEY)
    if not key:
        raise HTTPException(status_code=500, detail="Missing API_KEY. Set it in your Vercel environment.")
    return key

app = FastAPI(title="myXL Unofficial API", version="0.1.0", root_path="/api")

# CORS: open by default; lock down by setting CORS_ALLOW_ORIGINS env (comma-separated)
origins = os.getenv("CORS_ALLOW_ORIGINS", "*")
allow_origins = [o.strip() for o in origins.split(",")] if origins else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class OTPRequest(BaseModel):
    contact: str = Field(description="MSISDN starting with 628...")

class OTPVerify(BaseModel):
    contact: str
    code: str = Field(min_length=6, max_length=6, description="6-digit OTP code")

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

@app.get("/")
def root():
    return {"ok": True, "name": "myXL API", "version": "0.1.0"}

@app.post("/otp/request")
def request_otp(body: OTPRequest):
    sub_id = get_otp(body.contact)
    if not sub_id:
        raise HTTPException(status_code=400, detail="Failed to request OTP. Check the number format (start with 628).")
    return sub_id

@app.post("/otp/verify")
def verify_otp(body: OTPVerify):
    res = submit_otp(_api_key(), body.contact, body.code)
    if not res:
        raise HTTPException(status_code=400, detail="OTP verification failed.")
    # Pass through token payload (access_token, id_token, refresh_token, etc.)
    return res

@app.post("/token/refresh")
def refresh_token(body: RefreshRequest):
    res = get_new_token(body.refresh_token)
    if not res:
        raise HTTPException(status_code=400, detail="Refresh token invalid or expired.")
    return res

@app.post("/profile")
def profile(tokens: Tokens):
    data = get_profile(_api_key(), tokens.access_token, tokens.id_token)
    if data is None:
        raise HTTPException(status_code=400, detail="Failed to fetch profile.")
    return data

@app.post("/balance")
def balance(tokens: Tokens):
    bal = get_balance(_api_key(), tokens.id_token)
    if bal is None:
        raise HTTPException(status_code=400, detail="Failed to fetch balance.")
    return bal

@app.post("/packages/details")
def packages_details(tokens: Tokens):
    # This calls: api/v8/packages/quota-details
    path = "api/v8/packages/quota-details"
    payload = {"is_enterprise": False, "lang": "en"}
    res = send_api_request(_api_key(), path, payload, tokens.id_token, "POST")
    return res

@app.post("/packages/family")
def packages_by_family(body: FamilyRequest):
    data = get_family(_api_key(), body.tokens.model_dump(), body.family_code)
    if data is None:
        raise HTTPException(status_code=400, detail="Failed to fetch packages for family_code.")
    return data

@app.post("/packages/option")
def package_details(body: PackageDetailsRequest):
    data = get_package(_api_key(), body.tokens.model_dump(), body.package_option_code)
    if data is None:
        raise HTTPException(status_code=400, detail="Failed to fetch package details.")
    return data

# --- Payments (optional) ---
class PaymentInit(BaseModel):
    tokens: Tokens
    token_confirmation: str
    payment_target: str

@app.post("/pay/methods")
def pay_methods(body: PaymentInit):
    res = get_payment_methods(_api_key(), body.tokens.model_dump(), body.token_confirmation, body.payment_target)
    if res is None:
        raise HTTPException(status_code=400, detail="Failed to get payment methods.")
    return res

class QRRequest(BaseModel):
    tokens: Tokens
    token_confirmation: str
    payment_target: str

@app.post("/pay/qris/code")
def pay_qris_code(body: QRRequest):
    res = get_qris_code(_api_key(), body.tokens.model_dump(), body.token_confirmation, body.payment_target)
    if res is None:
        raise HTTPException(status_code=400, detail="Failed to get QRIS code.")
    return res
