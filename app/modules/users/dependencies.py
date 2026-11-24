from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from app.modules.users.models import User, Role
from app.db.session import SessionDep
from app.modules.users.services import UserService
from app.modules.patients.repositories import PatientRepository
from app.modules.users.models import User, Role, STAFF_ROLES
from app.modules.users.repositories import UserRepository
from app.core.exceptions.errors import ForbiddenError

def get_user_service(session: SessionDep) -> UserService:
    return UserService(UserRepository(session), PatientRepository(session))

UserServiceDep = Annotated[UserService, Depends(get_user_service)]

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

async def get_current_user(
        token: Annotated[str, Depends(oauth2_scheme)],
        service: UserServiceDep
) -> User:
    return await service.get_user_by_token(token)

CurrentUserDep = Annotated[User, Depends(get_current_user)]

async def require_admin(user: CurrentUserDep) -> User:
    if user.role != Role.SYSTEM_ADMIN:
        raise ForbiddenError("Admin privileges required")
    return user

AdminDep = Annotated[User, Depends(require_admin)]

async def require_staff(user: CurrentUserDep) -> User:
    if user.role != Role.SYSTEM_ADMIN and user.role not in STAFF_ROLES:
        raise ForbiddenError("Staff privileges required")
    return user

StaffDep = Annotated[User, Depends(require_staff)]