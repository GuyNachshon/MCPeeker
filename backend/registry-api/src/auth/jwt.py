"""JWT authentication middleware for Registry API.

Reference: FR-031 (RBAC authentication)
"""
from datetime import datetime, timedelta
from typing import Optional

import jwt
from fastapi import HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext


# Password hashing context (bcrypt)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# HTTP Bearer token scheme
security = HTTPBearer()


class JWTHandler:
    """JWT token handler for authentication."""

    def __init__(self, secret_key: str, algorithm: str = "HS256", expiration_minutes: int = 1440):
        """Initialize JWT handler.

        Args:
            secret_key: Secret key for signing tokens
            algorithm: JWT algorithm (default: HS256)
            expiration_minutes: Token expiration in minutes (default: 24 hours)
        """
        self.secret_key = secret_key
        self.algorithm = algorithm
        self.expiration_minutes = expiration_minutes

    def create_access_token(self, user_id: str, email: str, role: str) -> str:
        """Create a JWT access token.

        Args:
            user_id: User ID (UUID)
            email: User email
            role: User role (developer, analyst, admin)

        Returns:
            str: Encoded JWT token
        """
        expires_at = datetime.utcnow() + timedelta(minutes=self.expiration_minutes)

        payload = {
            "id": user_id,
            "email": email,
            "role": role,
            "exp": expires_at,
            "iat": datetime.utcnow(),
        }

        return jwt.encode(payload, self.secret_key, algorithm=self.algorithm)

    def decode_access_token(self, token: str) -> dict:
        """Decode and validate a JWT access token.

        Args:
            token: JWT token string

        Returns:
            dict: Decoded token payload

        Raises:
            HTTPException: If token is invalid or expired
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired"
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token"
            )


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password.

    Args:
        plain_password: Plain text password
        hashed_password: Bcrypt hashed password

    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt.

    Args:
        password: Plain text password

    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials,
    jwt_handler: JWTHandler
) -> dict:
    """Extract and validate user from JWT token.

    This function is used as a FastAPI dependency.

    Args:
        request: FastAPI request object
        credentials: Bearer token credentials
        jwt_handler: JWT handler instance

    Returns:
        dict: User data from token payload

    Raises:
        HTTPException: If authentication fails
    """
    token = credentials.credentials
    user = jwt_handler.decode_access_token(token)

    # Attach user to request state for RBAC checks
    request.state.user = user

    return user


# Middleware to extract JWT from Authorization header
class JWTAuthMiddleware:
    """Middleware to validate JWT tokens on all requests."""

    def __init__(self, jwt_handler: JWTHandler, excluded_paths: Optional[list] = None):
        """Initialize JWT auth middleware.

        Args:
            jwt_handler: JWT handler instance
            excluded_paths: Paths to exclude from authentication
        """
        self.jwt_handler = jwt_handler
        self.excluded_paths = excluded_paths or ["/health", "/metrics", "/docs", "/openapi.json"]

    async def __call__(self, request: Request, call_next):
        """Process request and validate JWT token.

        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint

        Returns:
            Response from next middleware/endpoint
        """
        # Skip authentication for excluded paths
        if request.url.path in self.excluded_paths:
            return await call_next(request)

        # Extract Authorization header
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid Authorization header"
            )

        # Extract and validate token
        token = auth_header.split("Bearer ")[1]
        user = self.jwt_handler.decode_access_token(token)

        # Attach user to request state
        request.state.user = user

        return await call_next(request)
