from typing import Annotated
from fastapi import Depends
from app.db.session import SessionDep
from app.modules.medicines.repositories import MedicineRepository
from app.modules.medicines.services import MedicineService


def get_medicine_repository(session: SessionDep) -> MedicineRepository:
    return MedicineRepository(session)

MedicineRepositoryDep = Annotated[MedicineRepository, Depends(get_medicine_repository)]

def get_medicine_service(repo: MedicineRepositoryDep) -> MedicineService:
    return MedicineService(repo)

MedicineServiceDep = Annotated[MedicineService, Depends(get_medicine_service)]