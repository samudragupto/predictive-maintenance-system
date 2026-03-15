"""
Security Utilities
Authentication, authorization, and encryption utilities
"""

import os
import secrets
import hashlib
import base64
import hmac
import json
import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional, Union, Tuple

import requests
from jose import jwt, JWTError
from jwt.algorithms import RSAAlgorithm
from passlib.context import CryptContext
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.config.settings import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

# Password hashing context (Still useful if you implement local auth later)
pwd_context = CryptContext(
    schemes=["bcrypt"],
    deprecated="auto",
    bcrypt__rounds=12
)

# Clerk Configuration
# Replace with your actual Clerk Frontend API URL or set in .env
# This is usually: https://<your-clerk-domain>/.well-known/jwks.json
# You can find the domain in Clerk Dashboard -> API Keys -> Frontend API
# Example: https://distinct-gopher-12.clerk.accounts.dev/.well-known/jwks.json
CLERK_JWKS_URL = os.getenv("CLERK_JWKS_URL", "https://clerk.your-domain.com/.well-known/jwks.json")

security_scheme = HTTPBearer()

class TokenType:
    """Token type constants"""
    ACCESS = "access"
    REFRESH = "refresh"
    API_KEY = "api_key"
    RESET_PASSWORD = "reset_password"
    EMAIL_VERIFICATION = "email_verification"


class SecurityManager:
    """
    Centralized security manager for authentication and authorization
    """
    
    def __init__(self):
        self.settings = get_settings()
        self.secret_key = self.settings.SECRET_KEY
        self.algorithm = self.settings.JWT_ALGORITHM
        
        # Initialize encryption
        self._fernet = self._initialize_fernet()
        
        # Cache for JWKS keys
        self._jwks_cache = None
        
        logger.info("SecurityManager initialized")
    
    def _initialize_fernet(self) -> Fernet:
        """Initialize Fernet encryption with derived key"""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"predictive_maintenance_salt",
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(
            kdf.derive(self.secret_key.encode())
        )
        return Fernet(key)
    
    def verify_clerk_token(self, token: str) -> Dict[str, Any]:
        """
        Verify a Clerk JWT token
        """
        try:
            # 1. Fetch JWKS if not cached
            if not self._jwks_cache:
                try:
                    response = requests.get(CLERK_JWKS_URL, timeout=5)
                    response.raise_for_status()
                    self._jwks_cache = response.json()
                except Exception as e:
                    logger.error(f"Failed to fetch Clerk JWKS: {e}")
                    # In local dev/mock mode, we might want to bypass or mock this
                    if settings.ENVIRONMENT == "development":
                        logger.warning("Dev mode: Bypassing strict Clerk verification (Mock)")
                        # Just decode without verification for dev if needed
                        # return jwt.get_unverified_claims(token)
                        raise HTTPException(status_code=503, detail="Auth service unavailable")
                    raise

            # 2. Get Key ID from token header
            try:
                unverified_header = jwt.get_unverified_header(token)
            except Exception:
                raise Exception("Invalid token format")

            # 3. Find matching key
            rsa_key = {}
            for key in self._jwks_cache["keys"]:
                if key["kid"] == unverified_header["kid"]:
                    rsa_key = {
                        "kty": key["kty"],
                        "kid": key["kid"],
                        "use": key["use"],
                        "n": key["n"],
                        "e": key["e"]
                    }
                    break
            
            if not rsa_key:
                # Force refresh cache next time
                self._jwks_cache = None
                raise Exception("Public key not found")

            # 4. Verify Signature
            try:
                public_key = RSAAlgorithm.from_jwk(json.dumps(rsa_key))
                payload = jwt.decode(
                    token,
                    public_key,
                    algorithms=["RS256"],
                    options={"verify_aud": False} # Clerk tokens don't always have audience
                )
                return payload
            except Exception as e:
                # Fallback for PyJWT vs python-jose differences
                # Or just basic decoding error
                raise Exception(f"Token signature verification failed: {str(e)}")

        except Exception as e:
            logger.error(f"Token verification failed: {e}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid Authentication: {str(e)}",
            )

    # ... (Keep existing hashing/encryption methods for internal use) ...
    def hash_password(self, password: str) -> str:
        return pwd_context.hash(password)
    
    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)
    
    def encrypt_data(self, data: str) -> str:
        return self._fernet.encrypt(data.encode()).decode()
    
    def decrypt_data(self, encrypted_data: str) -> str:
        return self._fernet.decrypt(encrypted_data.encode()).decode()


# Global security manager instance
_security_manager: Optional[SecurityManager] = None

def get_security_manager() -> SecurityManager:
    global _security_manager
    if _security_manager is None:
        _security_manager = SecurityManager()
    return _security_manager


# --- DEPENDENCY FOR ROUTES ---

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security_scheme)):
    """
    FastAPI Dependency to protect routes
    Validates the Bearer token from Clerk
    """
    token = credentials.credentials
    manager = get_security_manager()
    
    # In pure development mode, if you want to skip auth:
    # if settings.DEBUG: return {"sub": "dev_user"}
    
    return manager.verify_clerk_token(token)


# Helper exports
def hash_password(password: str) -> str:
    return get_security_manager().hash_password(password)

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return get_security_manager().verify_password(plain_password, hashed_password)

def encrypt_data(data: str) -> str:
    return get_security_manager().encrypt_data(data)

def decrypt_data(encrypted_data: str) -> str:
    return get_security_manager().decrypt_data(encrypted_data)