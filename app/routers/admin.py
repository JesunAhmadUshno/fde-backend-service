"""Admin-only user management. Every route requires the admin role;
non-admin callers receive 403."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_db, require_admin
from app.models import User
from app.schemas import RoleUpdateIn, UserOut

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/users", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> list[User]:
    result = await db.execute(select(User).order_by(User.created_at))
    return list(result.scalars().all())


@router.patch("/users/{user_id}/role", response_model=UserOut)
async def set_user_role(
    user_id: str,
    body: RoleUpdateIn,
    db: AsyncSession = Depends(get_db),
    admin: User = Depends(require_admin),
) -> User:
    target = await db.get(User, user_id)
    if target is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="user not found")
    target.role = body.role
    await db.commit()
    await db.refresh(target)
    return target
