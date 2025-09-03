
# myXL Vercel API (Unofficial)

> Wraps your existing Python CLI into an HTTP API deployable on Vercel.

## Endpoints (POST)

- `/api/otp/request` — `{ "contact": "628..." }` → `{ "subscriber_id": "..." }`
- `/api/otp/verify` — `{ "contact": "628...", "code": "123456" }` → tokens JSON (access_token, id_token, refresh_token, ...)
- `/api/token/refresh` — `{ "refresh_token": "..." }` → tokens JSON
- `/api/profile` — `{ "access_token": "...", "id_token": "..." }` → profile data
- `/api/balance` — `{ "access_token": "...", "id_token": "..." }` → balance object
- `/api/packages/details` — `{ "access_token": "...", "id_token": "..." }` → quota details
- `/api/packages/family` — `{ "tokens": { ... }, "family_code": "..." }` → options under a family
- `/api/packages/option` — `{ "tokens": { ... }, "package_option_code": "..." }` → single package detail
- `/api/pay/methods` — `{ "tokens": { ... }, "token_confirmation": "...", "payment_target": "..." }`
- `/api/pay/qris/code` — `{ "tokens": { ... }, "token_confirmation": "...", "payment_target": "..." }`

## Environment Variables (set in Vercel Dashboard → Settings → Environment Variables)

- `API_KEY` — required. Your key used for AX signing.
- Optional: override crypto endpoints if Cloudflare blocks Vercel IPs:
  - `XDATA_DECRYPT_URL`
  - `XDATA_ENCRYPT_SIGN_URL`
  - `PAYMENT_SIGN_URL`
  - `BOUNTY_SIGN_URL`
  - `AX_SIGN_URL`
- `CORS_ALLOW_ORIGINS` — comma-separated origins. Defaults to `*`.

## Deploy (Quick)

1. Push this folder to a Git repo (GitHub, GitLab, etc.).
2. Import to Vercel → select project → it will auto-detect Python.
3. Add `API_KEY` (and optional overrides) in Project → Settings → Environment Variables.
4. Deploy. Test with:
   ```sh
   curl -X POST https://<your-domain>/api/otp/request -H 'content-type: application/json' -d '{"contact":"628xxxx"}'
   ```

> Note: Vercel storage is ephemeral. This API is **stateless** (no local files). You must pass tokens in request bodies, or use a database / KV if you want persistence.
