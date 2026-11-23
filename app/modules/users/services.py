import uuid
from app.modules.users.models import User, Role
from app.modules.users.repositories import UserRepository
from app.modules.users.schemas import (CreateUserStaff,
                                       ReadUser, UserUpdate, Token)
from app.core.exceptions.errors import (ConflictError,
                                        UnauthorizedError,
                                        NotFoundError,
                                        ForbiddenError)
from app.core.security import (hash_password,
                               verify_password,
                               create_access_token,
                               decode_access_token)

class UserService:
    def __init__(self, repo: UserRepository) -> None:
        self.repo = repo

    async def register_user(self, data: CreateUserStaff) -> ReadUser:
        email = data.email.lower()
        if (await self.repo.get_by_email(email)
                or await self.repo.get_by_mobile_number(data.mobile_number)):
            raise ConflictError("User", email)

        user = User(
            email=email,
            first_name=data.first_name,
            last_name=data.last_name,
            mobile_number=data.mobile_number,
            password=hash_password(data.password),
            role=data.role,
        )
        return ReadUser.model_validate(await self.repo.add(user))

    async def login_user(self, mobile: str, password: str) -> Token:
        user = await self.repo.get_by_mobile_number(mobile)
        if user is None or not verify_password(password, user.password):
            raise UnauthorizedError("Incorrect mobile number or password")
        if not user.is_active:
            raise UnauthorizedError("Account is disabled")
        return Token(access_token=create_access_token(user.id))

    async def get_user_by_token(self, token: str) -> User:
        payload = decode_access_token(token)
        if payload is None:
            raise UnauthorizedError("Invalid or expired token")

        user: User | None = await self.repo.get_by_id(payload["sub"])

        if user is None or not user.is_active:
            raise UnauthorizedError("Invalid or expired token")

        return user

    async def update_staff_user(self, user_id: uuid.UUID, data: UserUpdate) -> ReadUser:
        user = await self.repo.get_by_id(user_id)
        if user is None:
            raise NotFoundError("User", str(user_id))
        if user.role == Role.PATIENT:
            raise ForbiddenError("Patient accounts can't be updated here.")

        updated_data = data.model_dump(exclude_unset=True)

        new_data = {
            key: value for key, value in updated_data.items() if value is not None
        }

        if "email" in new_data:
            new_data["email"] = new_data["email"].lower()
            existing = await self.repo.get_by_email(new_data["email"])
            if existing is not None and existing.id != user.id:
                raise ConflictError("User", new_data["email"])

        if "mobile_number" in new_data:
            existing = await self.repo.get_by_mobile_number(new_data["mobile_number"])
            if existing is not None and existing.id != user.id:
                raise ConflictError("User", new_data["mobile_number"])

        for key, value in new_data.items():
            setattr(user, key, value)

        return ReadUser.model_validate(await self.repo.save(user))