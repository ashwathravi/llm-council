## 2024-05-23 - Hardcoded Secrets in Auth Module
**Vulnerability:** The `backend/auth.py` module contained a hardcoded fallback value for `SECRET_KEY`.
**Learning:** Hardcoded fallbacks are convenient for development but dangerous if they accidentally slip into production, as they allow attackers to forge session tokens.
**Prevention:** Enforce environment variable presence in production environments and fail startup if missing. Use distinct default values or warnings for local development only.

## 2024-05-27 - Hardcoded Google Client ID
**Vulnerability:** The `backend/auth.py` module contained a hardcoded fallback value for `GOOGLE_CLIENT_ID`.
**Learning:** Hardcoded third-party client IDs binds the application to a specific developer's account and can mask configuration errors in production.
**Prevention:** Require explicit configuration of all external service credentials and identifiers via environment variables. Fail fast with a clear error if missing.

## 2024-05-23 - Insecure SSL Context Configuration
**Vulnerability:** The backend database connection logic explicitly disabled hostname checking and certificate verification (`ssl.CERT_NONE`) even when `sslmode=verify-full` was requested.
**Learning:** Checking for a security flag (like `verify-full`) is not enough; the implementation must actually enforce the security checks. Legacy code or "quick fixes" for local dev/self-signed certs can silently undermine security in production if they override strict modes.
**Prevention:** Use a dedicated helper function (like `configure_ssl_context`) to map configuration flags to explicit security settings. Ensure "strict" modes like `verify-full` use secure defaults (`ssl.create_default_context()`).

## 2024-05-27 - Information Leakage in Error Responses
**Vulnerability:** The backend API leaked internal exception details (including potential secrets or stack traces) directly to the client in `list_models` and `send_message_stream` endpoints.
**Learning:** Catch-all exception handlers that return `str(e)` to the client are a common source of information leakage. While convenient for debugging, they expose internal state and potential vulnerabilities to attackers.
**Prevention:** Implement a global exception handler or specific try/except blocks that log the detailed error internally but return a generic "Internal Server Error" message to the client.

## 2024-05-28 - Rate Limit Bypass via Store Flooding
**Vulnerability:** The in-memory rate limiter's cleanup strategy was to `clear()` the entire store when full, allowing attackers to reset everyone's rate limits by flooding the store with unique IPs.
**Learning:** "Fail Open" error handling (like clearing security state on error/full) can be weaponized to bypass security controls. Simple in-memory caches need bounded eviction strategies.
**Prevention:** Implement robust eviction policies (like FIFO/LRU) that degrade gracefully (e.g., evict oldest entries) instead of resetting global state.

## 2024-05-30 - Missing Content Security Policy
**Vulnerability:** The application lacked a `Content-Security-Policy` header, allowing potential XSS attacks to execute scripts from arbitrary domains or inline.
**Learning:** Modern frontend frameworks like React often rely on inline scripts or styles during development (and sometimes production), making strict CSP implementation challenging. Omitting CSP entirely leaves the application vulnerable.
**Prevention:** Implement a pragmatic CSP that whitelists specific trusted domains (e.g., Google Auth) and uses 'unsafe-inline' only where strictly necessary, while blocking all other external script sources and object embeddings.
