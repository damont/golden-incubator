import logging

from fastapi import APIRouter, Depends, HTTPException

from api.schemas.dto.user import LoginRequest, RegisterRequest, UserResponse
from api.schemas.orm.user import User
from api.utils.auth import (
    create_access_token,
    get_current_user,
    hash_password,
    verify_password,
)

logger = logging.getLogger(__name__)
router = APIRouter()


def user_to_response(user: User) -> UserResponse:
    return UserResponse(
        id=str(user.id),
        email=user.email,
        username=user.username,
        role=user.role,
        created_at=user.created_at.isoformat(),
    )


@router.post("/register", response_model=UserResponse, status_code=201)
async def register(data: RegisterRequest):
    existing = await User.find_one(
        {"$or": [{"email": data.email}, {"username": data.username}]}
    )
    if existing:
        raise HTTPException(status_code=400, detail="Email or username already taken")
    user = User(
        email=data.email,
        username=data.username,
        hashed_password=hash_password(data.password),
    )
    await user.insert()
    logger.info("New user registered: %s", data.username)
    return user_to_response(user)


@router.post("/login")
async def login(data: LoginRequest):
    user = await User.find_one(User.username == data.username)
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(str(user.id))
    logger.info("User logged in: %s", data.username)
    return {"access_token": token}


@router.get("/me", response_model=UserResponse)
async def me(user=Depends(get_current_user)):
    return user_to_response(user)
