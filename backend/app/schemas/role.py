import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class RoleCreate(BaseModel):
    name: str = Field(..., min_length=1)
    description: str | None = None

    model_config = ConfigDict(extra="forbid")


class RoleUpdate(BaseModel):
    description: str | None = None
    is_active: bool | None = None

    model_config = ConfigDict(extra="forbid")


class RoleRead(BaseModel):
    id: uuid.UUID
    name: str
    description: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
