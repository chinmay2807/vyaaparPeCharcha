"""FastAPI request schemas. Domain output is intentionally returned as plain JSON."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ApiModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    def payload(self) -> dict[str, Any]:
        return self.model_dump(by_alias=True, exclude_none=True)


class CustomerCreate(ApiModel):
    name: str
    aliases: list[str] = Field(default_factory=list)
    phone: str | None = None
    address: str | None = None
    credit_limit_paise: int = Field(0, alias="creditLimitPaise", ge=0)


class UploadCreate(ApiModel):
    content_type: str = Field(alias="contentType")
    size_bytes: int = Field(alias="sizeBytes", gt=0, le=15 * 1024 * 1024)


class VoiceSubmit(ApiModel):
    audio_key: str | None = Field(None, alias="audioKey")
    transcript: str | None = None
    language_hint: str | None = Field(None, alias="languageHint")
    filename: str | None = None
    content_type: str | None = Field(None, alias="contentType")


class RevisionRequest(ApiModel):
    revision: int = Field(ge=1)


class ClarificationRequest(RevisionRequest):
    answer: Any


class DraftEditRequest(RevisionRequest):
    customer_id: str | None = Field(None, alias="customerId")
    delivery_date: str | None = Field(None, alias="deliveryDate")
    items: list[dict[str, Any]] | None = None
    collection_amount_paise: int | None = Field(None, alias="collectionAmountPaise", ge=0)


class ConfirmRequest(RevisionRequest):
    spoken_confirmation: bool = Field(False, alias="spokenConfirmation")
    language: str = "hi-IN"


class MobileConfirmRequest(RevisionRequest):
    spoken_confirmation: bool = Field(True, alias="spokenConfirmation")
    language: str = "hi-IN"
