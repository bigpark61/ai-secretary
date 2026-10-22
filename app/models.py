from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class DataRecordFields(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    production_volume: float = Field(ge=0)
    defect_rate: float = Field(ge=0, le=100)
    energy_consumption: float = Field(ge=0)
    energy_efficiency: float = Field(ge=0)
    downtime_percentage: float = Field(ge=0, le=100)
    maintenance_hours: float = Field(ge=0)
    energy_per_unit: float = Field(ge=0)


class DataRecordCreate(DataRecordFields):
    id: str | None = Field(default=None, min_length=1, max_length=128)
    source_record_id: int | None = Field(default=None, ge=1)


class DataRecordUpdate(DataRecordFields):
    source_record_id: int | None = Field(default=None, ge=1)


class ConversationMessage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=4000)


class ConversationCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str | None = Field(default=None, max_length=120)
    messages: list[ConversationMessage] = Field(min_length=1, max_length=200)


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(min_length=1, max_length=4000)
    conversation_id: str | None = Field(default=None, min_length=1, max_length=128)
