import uuid
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.modules.users.models import Role, User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db_session = session

    async def add(self, user: User) -> User:
        self.db_session.add(user)
        return await self.save(user)

    async def save(self, user: User) -> User:
        await self.db_session.flush()
        await self.db_session.refresh(user)
        return user

    async def get_by_id(self, user_id: uuid.UUID) -> User | None:
        return await self.db_session.get(User, user_id)

    async def get_for_update(self, user_id: uuid.UUID) -> User | None:
        stmt = (
            select(User)
            .where(User.id == user_id)
            .with_for_update(of=User)
        )
        return await self.db_session.scalar(stmt)

    async def get_by_email(self, email: str) -> User | None:
        if not email:
            return None
        stmt = select(User).where(func.lower(User.email) == email.lower())
        return await self.db_session.scalar(stmt)

    async def get_by_patient_id(self, patient_id: uuid.UUID) -> User | None:
        stmt = select(User).where(User.patient_id == patient_id)
        return await self.db_session.scalar(stmt)

    async def get_by_mobile_number(self, mobile_number: str) -> User | None:
        stmt = select(User).where(User.mobile_number == mobile_number)
        return await self.db_session.scalar(stmt)

    async def search(
        self,
        q: str | None,
        role: Role | None,
        is_active: bool | None,
        page: int,
        page_size: int,
    ) -> tuple[list[User], int]:
        base = select(User)
        if q:
            pattern = f"%{q}%"
            base = base.where(
                or_(
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.email.ilike(pattern),
                    User.mobile_number.ilike(pattern),
                )
            )
        if role is not None:
            base = base.where(User.role == role)
        if is_active is not None:
            base = base.where(User.is_active.is_(is_active))
        total = await self.db_session.scalar(
            select(func.count()).select_from(base.subquery())
        )
        stmt = (
            base.order_by(User.created_at.desc(), User.id)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = (await self.db_session.scalars(stmt)).all()
        return list(items), total or 0
