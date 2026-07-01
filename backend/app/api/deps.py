from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import get_settings
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.database import get_db
from app.models.user import User, UserRole

bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")

    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")

    return user


def require_hr_user(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role not in (UserRole.hr, UserRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="HR access required")
    return current_user


def _user_from_raw_token(raw_token: str | None, db: Session) -> User:
    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    payload = decode_access_token(raw_token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token payload")
    user = db.get(User, int(user_id))
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found or inactive")
    return user


def require_hr_user_sse(
    token: str | None = Query(None, description="JWT for EventSource (cannot send Authorization header)"),
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: Session = Depends(get_db),
) -> User:
    """HR auth for SSE — accepts Bearer header or ?token= query param."""
    raw = credentials.credentials if credentials and credentials.scheme.lower() == "bearer" else token
    user = _user_from_raw_token(raw, db)
    if user.role not in (UserRole.hr, UserRole.admin):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="HR access required")
    return user


def require_service_key(
    x_service_key: str | None = Header(None, alias="X-Service-Key"),
) -> None:
    """Gate agent/MCP write endpoints. Skipped when INTERNAL_SERVICE_KEY is unset (dev)."""
    expected = get_settings().internal_service_key.strip()
    if not expected:
        return
    if not x_service_key or x_service_key != expected:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing X-Service-Key",
        )