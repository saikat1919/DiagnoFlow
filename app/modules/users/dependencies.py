from typing import Annotated
from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
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

async def require_admin_or_receptionist(user: CurrentUserDep) -> User:
    if user.role not in (Role.SYSTEM_ADMIN, Role.RECEPTIONIST):
        raise ForbiddenError("Admin or receptionist privileges required")
    return user

AdminOrReceptionistDep = Annotated[User, Depends(require_admin_or_receptionist)]

async def require_staff(user: CurrentUserDep) -> User:
    if user.role != Role.SYSTEM_ADMIN and user.role not in STAFF_ROLES:
        raise ForbiddenError("Staff privileges required")
    return user

StaffDep = Annotated[User, Depends(require_staff)]

async def require_pharmacy(user: CurrentUserDep) -> User:
    if user.role not in (Role.PHARMACIST, Role.PHARMACY_MANAGER):
        raise ForbiddenError("Pharmacy privileges required")
    return user

PharmacyDep = Annotated[User, Depends(require_pharmacy)]

async def require_admin_or_lab(user: CurrentUserDep) -> User:
    if user.role not in (Role.SYSTEM_ADMIN, Role.LAB_TECHNICIAN):
        raise ForbiddenError("Admin or lab privileges required")
    return user

AdminOrLabDep = Annotated[User, Depends(require_admin_or_lab)]

async def require_pharmacy_manager(user: CurrentUserDep) -> User:
    if user.role != Role.PHARMACY_MANAGER:
        raise ForbiddenError("Pharmacy manager privileges required")
    return user

PharmacyManagerDep = Annotated[User, Depends(require_pharmacy_manager)]

async def require_lab(user: CurrentUserDep) -> User:
    if user.role != Role.LAB_TECHNICIAN:
        raise ForbiddenError("Lab privileges required")
    return user

LabDep = Annotated[User, Depends(require_lab)]

async def require_admin_or_pharmacy(user: CurrentUserDep) -> User:
    if user.role not in (Role.SYSTEM_ADMIN, Role.PHARMACIST, Role.PHARMACY_MANAGER):
        raise ForbiddenError("Admin or pharmacy privileges required")
    return user

AdminOrPharmacyDep = Annotated[User, Depends(require_admin_or_pharmacy)]