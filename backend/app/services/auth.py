import logging
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import create_access_token, hash_password, verify_password
from app.models import User
from app.schemas import TokenResponse, UserLogin, UserRegister

logger = logging.getLogger(__name__)


class RoleRegistrationForbidden(Exception):
    """Raised when a caller attempts to self-register a privileged role."""


class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def register_user(self, user_data: UserRegister) -> User:
        # Public self-service registration may only create ENTREPRENEUR accounts.
        # Officer/Admin roles must be provisioned through a trusted path (e.g. the
        # demo seed or an admin), never by a caller-supplied role on this endpoint.
        if (user_data.role.value if hasattr(user_data.role, "value") else str(user_data.role)).upper() != "ENTREPRENEUR":
            raise RoleRegistrationForbidden("Only ENTREPRENEUR accounts can self-register")

        result = await self.db.execute(
            select(User).where(User.email == user_data.email)
        )
        if result.scalar_one_or_none():
            raise ValueError("User already exists with this email")

        user = User(
            email=user_data.email,
            name=user_data.name,
            phone=user_data.phone,
            password_hash=hash_password(user_data.password),
            role=user_data.role,
            is_active=True,
        )

        self.db.add(user)
        await self.db.commit()
        await self.db.refresh(user)

        logger.info(f"New user registered: {user.email} ({user.role})")
        return user

    async def login(self, credentials: UserLogin) -> TokenResponse:
        result = await self.db.execute(
            select(User).where(User.email == credentials.email)
        )
        user = result.scalar_one_or_none()

        if not user or not verify_password(credentials.password, user.password_hash):
            raise ValueError("Invalid email or password")

        if not user.is_active:
            raise ValueError("Account is deactivated")

        token = create_access_token(
            data={"sub": str(user.id), "email": user.email, "role": user.role.value}
        )

        logger.info(f"User logged in: {user.email}")
        return TokenResponse(
            access_token=token,
            token_type="bearer",
            expires_in=86400,
        )

    async def get_user_by_id(self, user_id: UUID) -> User:
        result = await self.db.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_user_by_email(self, email: str) -> User:
        result = await self.db.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
