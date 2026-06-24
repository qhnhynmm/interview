from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_hr_user
from app.core.security import create_access_token, hash_password, verify_password
from app.database import get_db
from app.models.user import User, UserRole
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserPublic

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register(body: RegisterRequest, db: Session = Depends(get_db)) -> TokenResponse:
    username = body.username.strip()
    email = str(body.email).strip().lower()

    existing = db.scalar(
        select(User).where((User.email == email) | (User.username == username))
    )
    if existing:
        if existing.email == email:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already taken")

    user = User(
        username=username,
        email=email,
        hashed_password=hash_password(body.password),
        role=UserRole.hr,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Account already exists") from None

    db.refresh(user)
    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> TokenResponse:
    email = str(body.email).strip().lower()
    user = db.scalar(select(User).where(User.email == email))

    # Same message for unknown email and wrong password (frontend expects neutral 401).
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect email or password")

    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled")

    token = create_access_token(user_id=user.id, role=user.role.value)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserPublic)
def me(current_user: User = Depends(get_current_user)) -> User:
    return current_user


@router.get("/me/hr", response_model=UserPublic)
def me_hr(current_user: User = Depends(require_hr_user)) -> User:
    """Example protected route — HR-only. Use require_hr_user on interview endpoints later."""
    return current_user