from fastapi import APIRouter, status, Depends
from typing import Annotated
from fastapi.security import OAuth2PasswordRequestForm
from app.modules.users.models import Role
from app.modules.users.schemas import ReadUser, CreateUserStaff, Token, UserUpdate, PatientAccountCreate
from app.modules.users.dependencies import UserServiceDep, CurrentUserDep, AdminDep

auth_router = APIRouter(prefix="/auth", tags=["auth"])

@auth_router.post("/register", response_model=ReadUser, status_code=status.HTTP_201_CREATED)
async def register(data: CreateUserStaff, service: UserServiceDep, admin: AdminDep) -> ReadUser:
    return await service.register_user(data)

@auth_router.post("/login", response_model=Token, status_code=status.HTTP_200_OK)
async def login(
        form_data: Annotated[OAuth2PasswordRequestForm,Depends()],
        service: UserServiceDep
) -> Token:
    return await service.login_user(mobile=form_data.username, password=form_data.password)

@auth_router.get("/me", response_model=ReadUser, status_code=status.HTTP_200_OK)
async def me(user: CurrentUserDep) -> ReadUser:
    return ReadUser.model_validate(user)

@auth_router.patch("/me/edit", response_model=ReadUser, status_code=status.HTTP_200_OK)
async def me_edit(data: UserUpdate, service: UserServiceDep, user: CurrentUserDep) -> ReadUser:
    return await service.update_staff_user(user.id, data)

@auth_router.post("/register/patient", response_model=ReadUser, status_code=status.HTTP_201_CREATED)
async def register_patient(data: PatientAccountCreate, service: UserServiceDep, admin: AdminDep) -> ReadUser:
    return await service.create_patient_account(data)