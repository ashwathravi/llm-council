## 2024-05-23 - Hardcoded Secrets in Auth Module
**Vulnerability:** The `backend/auth.py` module contained a hardcoded fallback value for `SECRET_KEY`.
**Learning:** Hardcoded fallbacks are convenient for development but dangerous if they accidentally slip into production, as they allow attackers to forge session tokens.
**Prevention:** Enforce environment variable presence in production environments and fail startup if missing. Use distinct default values or warnings for local development only.

## 2024-05-27 - Hardcoded Google Client ID
**Vulnerability:** The `backend/auth.py` module contained a hardcoded fallback value for `GOOGLE_CLIENT_ID`.
**Learning:** Hardcoding third-party client IDs binds the application to a specific developer's account and can mask configuration errors in production.
**Prevention:** Require explicit configuration of all external service credentials and identifiers via environment variables. Fail fast with a clear error if missing.

## 2024-05-23 - Insecure SSL Context Configuration
**Vulnerability:** The backend database connection logic explicitly disabled hostname checking and certificate verification (`ssl.CERT_NONE`) even when `sslmode=verify-full` was requested.
**Learning:** Checking for a security flag (like `verify-full`) is not enough; the implementation must actually enforce the security checks. Legacy code or "quick fixes" for local dev/self-signed certs can silently undermine security in production if they override strict modes.
**Prevention:** Use a dedicated helper function (like `configure_ssl_context`) to map configuration flags to explicit security settings. Ensure "strict" modes like `verify-full` use secure defaults (`ssl.create_default_context()`).
