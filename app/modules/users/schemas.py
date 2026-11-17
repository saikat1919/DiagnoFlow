import uuid
from typing import Annotated
from pydantic import BaseModel, EmailStr, Field, ConfigDict


class CreateUser(BaseModel):
    first_name: str = Field(min_length=1, max_length=50)
    last_name: str = Field(min_length=1, max_length=50)
    mobile_number: str = Field(min_length=11, max_length=11)
    email: EmailStr
    password: str
    role: str