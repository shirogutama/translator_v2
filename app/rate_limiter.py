from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from _info import __token__

def authenticated(request: Request) -> bool:
    """Check if the request is authenticated using Bearer token."""
    token = request.headers.get("Authorization")
    return token == f"Bearer {__token__}"

def get_key(request: Request) -> str:
    """Generate a unique key for rate limiting based on authentication status."""
    if authenticated(request):
        return get_remote_address(request) + "_authenticated"
    return get_remote_address(request) + "_unauthenticated"

def get_rate_limit(request: Request) -> str:
    """Define rate limits based on authentication status."""
    if authenticated(request):
        return "10/second"  # Keep existing rate for authenticated users
    return "3/minute"  # Set 3 requests per minute for unauthenticated users

# Initialize limiter with the key function
limiter = Limiter(key_func=get_key)