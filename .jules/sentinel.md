## 2024-05-23 - Hardcoded Secrets in Auth Module
**Vulnerability:** The `backend/auth.py` module contained a hardcoded fallback value for `SECRET_KEY`.
**Learning:** Hardcoded fallbacks are convenient for development but dangerous if they accidentally slip into production, as they allow attackers to forge session tokens.
**Prevention:** Enforce environment variable presence in production environments and fail startup if missing. Use distinct default values or warnings for local development only.

## 2024-05-27 - Hardcoded Google Client ID
**Vulnerability:** The `backend/auth.py` module contained a hardcoded fallback value for `GOOGLE_CLIENT_ID`.
**Learning:** Hardcoding third-party client IDs binds the application to a specific developer's account and can mask configuration errors in production.
**Prevention:** Require explicit configuration of all external service credentials and identifiers via environment variables. Fail fast with a clear error if missing.
