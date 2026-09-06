"""Convenience endpoints optimized for an Android client on the same LAN."""

from __future__ import annotations

import hashlib
import os
import re
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile

from ..dependencies import get_idempotency_key, get_merchant_id, get_service
from ..schemas import ClarificationRequest, MobileConfirmRequest
from ..service import ApiError, Service

router = APIRouter(prefix="/v1/mobile", tags=["Android / LAN"])
ServiceDep = Annotated[Service, Depends(get_service)]
MerchantDep = Annotated[str, Depends(get_merchant_id)]
KeyDep = Annotated[str, Depends(get_idempotency_key)]
MAX_AUDIO_BYTES = 15 * 1024 * 1024
SUPPORTED_AUDIO_TYPES = {
    "audio/webm", "video/webm", "audio/mpeg", "audio/mp3", "audio/mpeg3",
    "audio/x-mpeg-3", "audio/x-mp3", "audio/mp4", "audio/x-m4a", "audio/wav",
    "audio/x-wav", "audio/wave", "audio/3gpp", "audio/aac", "audio/x-aac",
    "audio/aiff", "audio/x-aiff", "audio/ogg", "audio/opus", "audio/flac",
    "audio/x-flac", "audio/amr", "audio/x-ms-wma",
}


def _child_key(key: str, purpose: str) -> str:
    return hashlib.sha256(f"{key}:{purpose}".encode()).hexdigest()[:32]


def _url(request: Request, route_name: str, **params: str) -> str:
    configured = os.getenv("APP_BASE_URL", "").rstrip("/")
    path = request.app.url_path_for(route_name, **params)
    return f"{configured}{path}" if configured else str(request.url_for(route_name, **params))


def _links(request: Request, job_id: str) -> dict[str, str]:
    return {
        "self": _url(request, "mobile_get_job", job_id=job_id),
        "clarify": _url(request, "mobile_clarify", job_id=job_id),
        "confirm": _url(request, "mobile_confirm", job_id=job_id),
    }


@router.get("/config")
def mobile_config(request: Request):
    return {
        "apiBaseUrl": os.getenv("APP_BASE_URL", str(request.base_url)).rstrip("/"),
        "maxAudioBytes": MAX_AUDIO_BYTES,
        "supportedAudioTypes": sorted(SUPPORTED_AUDIO_TYPES),
        "confirmationRequired": True,
    }


@router.get("/sync")
def sync(service: ServiceDep, merchant: MerchantDep):
    return service.sync(merchant)


@router.post("/voice-jobs", status_code=202, name="mobile_submit_audio")
async def submit_audio(
    request: Request,
    service: ServiceDep,
    merchant: MerchantDep,
    key: KeyDep,
    audio: UploadFile = File(...),
    language_hint: str | None = Form(None),
):
    if not re.fullmatch(r"[A-Za-z0-9._:-]{8,200}", key):
        raise ApiError(400, "IDEMPOTENCY_KEY_REQUIRED", "A valid Idempotency-Key is required")
    content_type = (audio.content_type or "application/octet-stream").lower()
    if content_type not in SUPPORTED_AUDIO_TYPES:
        raise ApiError(415, "UNSUPPORTED_AUDIO", "Unsupported Android recording format")
    content = await audio.read(MAX_AUDIO_BYTES + 1)
    if not content or len(content) > MAX_AUDIO_BYTES:
        raise ApiError(400, "INVALID_AUDIO_SIZE", "Audio must be between 1 byte and 15 MB")

    upload = service.create_upload(
        merchant, _child_key(key, "create-upload"),
        {"contentType": content_type, "sizeBytes": len(content)},
    )
    service.put_upload(
        merchant, upload["uploadId"], _child_key(key, "put-upload"), content, content_type,
    )
    job = service.submit_voice(
        merchant, key,
        {"audioKey": upload["audioKey"], "filename": audio.filename or "recording",
         "contentType": content_type, "languageHint": language_hint},
    )
    return {**job, "links": _links(request, job["id"])}


@router.get("/voice-jobs/{job_id}", name="mobile_get_job")
def get_job(job_id: str, request: Request, service: ServiceDep, merchant: MerchantDep):
    job = service.voice_job(merchant, job_id)
    return {**job, "links": _links(request, job_id)}


@router.post("/voice-jobs/{job_id}/clarifications", name="mobile_clarify")
def clarify(job_id: str, request: Request, body: ClarificationRequest,
            service: ServiceDep, merchant: MerchantDep, key: KeyDep):
    job = service.clarify(merchant, job_id, key, body.payload())
    return {**job, "links": _links(request, job_id)}


@router.post("/voice-jobs/{job_id}/confirm", name="mobile_confirm")
def confirm(job_id: str, request: Request, body: MobileConfirmRequest,
            service: ServiceDep, merchant: MerchantDep, key: KeyDep):
    payload = service.confirm(merchant, job_id, key, body.payload())
    voice = dict(payload.get("voiceConfirmation") or {})
    voice.pop("audioBase64", None)
    invoice_id = payload["invoice"]["id"]
    order_id = payload["order"]["id"]
    artifacts = {
        "invoice": {
            "url": _url(request, "download_invoice", invoice_id=invoice_id),
            "contentType": "application/pdf",
            "filename": f'{payload["invoice"]["invoiceNumber"]}.pdf',
        },
        "audio": ({
            "url": _url(request, "download_confirmation_audio", order_id=order_id),
            "contentType": voice.get("contentType"),
            "language": voice.get("language"),
        } if voice.get("status") == "READY" else voice),
    }
    payload["voiceConfirmation"] = voice
    return {**payload, "artifacts": artifacts}
