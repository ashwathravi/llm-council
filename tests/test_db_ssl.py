
import ssl
from backend.database import configure_ssl_context

def test_verify_full_is_secure():
    """
    Asserts that sslmode=verify-full results in a SECURE SSL context.
    """
    query_params = {"sslmode": "verify-full", "other": "value"}
    connect_args, updated_params = configure_ssl_context(query_params)

    # Check ssl context
    ctx = connect_args.get("ssl")
    assert ctx is not None
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is True

    # Check query params updated
    assert "sslmode" not in updated_params
    assert updated_params["other"] == "value"

def test_verify_ca_is_secure_cert_only():
    """
    Asserts that sslmode=verify-ca verifies certificate but not hostname.
    """
    query_params = {"sslmode": "verify-ca"}
    connect_args, updated_params = configure_ssl_context(query_params)

    ctx = connect_args.get("ssl")
    assert ctx is not None
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is False

def test_require_is_secure():
    """
    Asserts that sslmode=require is now secure (CERT_REQUIRED) but without hostname check.
    """
    query_params = {"sslmode": "require"}
    connect_args, updated_params = configure_ssl_context(query_params)

    ctx = connect_args.get("ssl")
    assert ctx is not None
    assert ctx.verify_mode == ssl.CERT_REQUIRED
    assert ctx.check_hostname is False

def test_sslrootcert_loading():
    """
    Asserts that sslrootcert is correctly handled and loaded into the context.
    """
    from unittest.mock import patch, MagicMock

    query_params = {"sslmode": "verify-ca", "sslrootcert": "/path/to/ca.crt"}

    with patch("ssl.SSLContext.load_verify_locations") as mock_load:
        connect_args, updated_params = configure_ssl_context(query_params)

        ctx = connect_args.get("ssl")
        assert ctx is not None
        mock_load.assert_called_once_with(cafile="/path/to/ca.crt")
        assert "sslrootcert" not in updated_params

def test_no_sslmode():
    """
    Asserts that no sslmode results in no SSL context.
    """
    query_params = {"other": "value"}
    connect_args, updated_params = configure_ssl_context(query_params)

    assert "ssl" not in connect_args
    assert updated_params == query_params
