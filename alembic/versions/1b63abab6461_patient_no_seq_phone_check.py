"""patient_no_seq_phone_check

Revision ID: 1b63abab6461
Revises: 15e2c7d6308a
Create Date: 2026-11-17 17:39:50.457045

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '1b63abab6461'
down_revision: Union[str, Sequence[str], None] = '15e2c7d6308a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE SEQUENCE IF NOT EXISTS patient_no_seq START 1")

    # phone_number: unique -> plain index
    op.drop_index(op.f("ix_patients_phone_number"), table_name="patients")
    op.create_index(op.f("ix_patients_phone_number"), "patients", ["phone_number"], unique=False)

    op.create_check_constraint(
        op.f("ck_users_patient_id_check"),
        "users",
        "(role = 'patient') = (patient_id IS NOT NULL)",
    )

def downgrade() -> None:
    op.drop_constraint(op.f("ck_users_patient_id_check"), "users", type_="check")
    op.drop_index(op.f("ix_patients_phone_number"), table_name="patients")
    op.create_index(op.f("ix_patients_phone_number"), "patients", ["phone_number"], unique=True)
    op.execute("DROP SEQUENCE IF EXISTS patient_no_seq")
