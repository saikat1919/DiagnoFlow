import asyncio
from getpass import getpass
from app.db.session import SessionLocal
from app.modules.users.models import User, Role
from app.modules.users.repositories import UserRepository
from app.modules.patients.models import Patient
from app.core.security import hash_password


async def create_system_admin() -> None:
    first_name = input("First name: ").strip()
    last_name = input("Last name: ").strip()
    mobile_number = input("Mobile number: ").strip()
    email = input("Email: ").strip().lower()

    password = getpass("Password (minimum 8 characters): ")
    confirm_password = getpass("Confirm password: ")

    if not all((first_name, last_name, mobile_number, email)):
        print("Error: All fields are required.")
        return

    if len(password) < 8:
        print("Error: Password must be at least 8 characters long.")
        return

    if password != confirm_password:
        print("Error: Passwords do not match.")
        return

    async with SessionLocal() as session:
        repo = UserRepository(session)

        existing_email = await repo.get_by_email(email)
        existing_mobile = await repo.get_by_mobile_number(mobile_number)

        if existing_email:
            print(f"Error: A user with email '{email}' already exists.")
            return

        if existing_mobile:
            print(
                f"Error: A user with mobile number "
                f"'{mobile_number}' already exists."
            )
            return

        admin = User(
            first_name=first_name,
            last_name=last_name,
            mobile_number=mobile_number,
            email=email,
            password=hash_password(password),
            role=Role.SYSTEM_ADMIN,
            is_active=True,
            patient_id=None,
        )

        try:
            session.add(admin)
            await session.commit()
            await session.refresh(admin)

            print("\nSystem admin created successfully!")
            print(f"ID: {admin.id}")
            print(f"Name: {admin.first_name} {admin.last_name}")
            print(f"Email: {admin.email}")
            print(f"Mobile: {admin.mobile_number}")
            print(f"Role: {admin.role.value}")

        except Exception:
            await session.rollback()
            raise


if __name__ == "__main__":
    asyncio.run(create_system_admin())
