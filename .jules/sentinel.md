## 2024-05-23 - Hardcoded Secrets in Auth Module
**Vulnerability:** The `backend/auth.py` module contained a hardcoded fallback value for `SECRET_KEY`.
**Learning:** Hardcoded fallbacks are convenient for development but dangerous if they accidentally slip into production, as they allow attackers to forge session tokens.
**Prevention:** Enforce environment variable presence in production environments and fail startup if missing. Use distinct default values or warnings for local development only.
