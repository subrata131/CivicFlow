import os
from datetime import datetime, timedelta, timezone
from pathlib import Path
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
import bcrypt

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")
# Keep the original development key so existing local demo tokens remain valid.
# Set SECRET_KEY in .env before deployment.
SECRET_KEY = os.getenv("SECRET_KEY", "CHANGE-THIS-SECRET-KEY-BEFORE-DEPLOYMENT-2026")
ALGORITHM = "HS256"
bearer = HTTPBearer(auto_error=False)


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:72], hashed.encode("utf-8"))
    except (ValueError, TypeError, AttributeError):
        return False


def create_token(subject: str, role: str, user_id: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {"sub": subject, "role": role, "user_id": user_id,
               "iat": now, "exp": now + timedelta(hours=12)}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)


def current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer),
):
    token = credentials.credentials if credentials else None
    if not token:
        # Backward-compatible cookie support; avoid query-string tokens.
        token = request.cookies.get("civic_token")
    if not token:
        raise HTTPException(401, "Authentication required. Please log in.",
                            headers={"WWW-Authenticate": "Bearer"})
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        if not payload.get("sub") or payload.get("role") not in ("citizen", "admin") or not payload.get("user_id"):
            raise HTTPException(401, "Invalid authentication token")
        return payload
    except JWTError:
        raise HTTPException(401, "Invalid or expired token. Please log in again.",
                            headers={"WWW-Authenticate": "Bearer"})


def require_admin(user=Depends(current_user)):
    if user.get("role") != "admin":
        raise HTTPException(403, "Administrator access required")
    return user


def require_citizen(user=Depends(current_user)):
    if user.get("role") != "citizen":
        raise HTTPException(403, "Citizen access required")
    return user
