from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.security import create_access_token, get_current_user
from app.schemas import TokenResponse, UserLogin, UserRegister, UserResponse
from app.services.auth import AuthService, RoleRegistrationForbidden

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserRegister, db: AsyncSession = Depends(get_db_session)):
    auth_service = AuthService(db)
    try:
        user = await auth_service.register_user(user_data)
        return user
    except RoleRegistrationForbidden as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.post("/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: AsyncSession = Depends(get_db_session)):
    auth_service = AuthService(db)
    try:
        token = await auth_service.login(credentials)
        return token
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(user: dict = Depends(get_current_user)):
    """Issue a fresh access token for an already-valid token."""
    token = create_access_token(
        data={
            "sub": user["sub"],
            "email": user.get("email", ""),
            "role": user.get("role", "ENTREPRENEUR"),
        }
    )
    return TokenResponse(access_token=token, token_type="bearer", expires_in=86400)


@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    return {"message": "Successfully logged out"}
