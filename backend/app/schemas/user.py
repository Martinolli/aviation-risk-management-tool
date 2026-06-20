import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class UserCreate(BaseModel):
    email: str
    display_name: str = Field(..., min_length=1)

    model_config = ConfigDict(extra="forbid")


class UserUpdate(BaseModel):
    display_name: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class UserRead(BaseModel):
    id: uuid.UUID
    email: str
    display_name: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
