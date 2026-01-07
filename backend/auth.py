"""Authentication module for Google Sign-In and JWT management."""

import os
import sys
import jwt
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta
from google.oauth2 import id_token
from google.auth.transport import requests
from fastapi import HTTPException, status, Header, Depends
from pydantic import BaseModel
from .config import APP_ORIGIN

# Setup logging
logger = logging.getLogger(__name__)

# Secret key for signing session JWTs
# Security: Enforce secure key in production
jwt_secret = os.getenv("JWT_SECRET_KEY")

if jwt_secret:
    SECRET_KEY = jwt_secret
else:
    if APP_ORIGIN == "local":
        SECRET_KEY = "dev_secret_key_change_in_production"
        # Log warning (and print to stderr to ensure visibility during startup)
        logger.warning("JWT_SECRET_KEY is not set. Using insecure default key.")
        print(
            "WARNING: JWT_SECRET_KEY is not set. Using insecure default key. "
            "This is unsafe for production!",
            file=sys.stderr
        )
    else:
        # In production (Render, Replit, etc.), fail fast if no secret is set
        raise RuntimeError(
            f"CRITICAL SECURITY ERROR: JWT_SECRET_KEY is missing in {APP_ORIGIN} environment. "
            "You must set a secure random string for JWT_SECRET_KEY to start the application."
        )

ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60 * 24 * 7  # 7 days

# Google Client ID from environment or hardcoded fallback (for dev)
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "154618380883-hlmnd78sufsgvrmvk39ht872brk4o32r.apps.googleusercontent.com")


class Token(BaseModel):
    access_token: str
    token_type: str
    user: Dict[str, Any]


class GoogleLoginRequest(BaseModel):
    id_token: str


def verify_google_token(token: str) -> Dict[str, Any]:
    """Verify Google ID token and return user info."""
    try:
        id_info = id_token.verify_oauth2_token(
            token, requests.Request(), GOOGLE_CLIENT_ID
        )
        return id_info
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
            headers={"WWW-Authenticate": "Bearer"},
        )


def create_access_token(data: Dict[str, Any]) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def get_current_user_id(authorization: str = Header(None)) -> str:
    """Dependency to get current user ID from JWT."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication scheme",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token payload",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user_id
        
    except (ValueError, jwt.PyJWTError):
        # ValueError: from split() if header is malformed
        # PyJWTError: from jwt.decode() if token is invalid
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
