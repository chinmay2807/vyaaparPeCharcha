from typing import Annotated

from fastapi import APIRouter, Depends, Request, Response

from ..dependencies import get_idempotency_key, get_merchant_id, get_service
from ..invoice import render_invoice
from ..schemas import (
    ClarificationRequest,
    ConfirmRequest,
    DraftEditRequest,
    UploadCreate,
    VoiceSubmit,
)
from ..service import Service

router = APIRouter(prefix="/v1", tags=["voice orders"])
ServiceDep = Annotated[Service, Depends(get_service)]
MerchantDep = Annotated[str, Depends(get_merchant_id)]
KeyDep = Annotated[str, Depends(get_idempotency_key)]


@router.post("/voice-jobs/uploads", status_code=201)
def create_upload(body: UploadCreate, service: ServiceDep, merchant: MerchantDep, key: KeyDep):
    return service.create_upload(merchant, key, body.payload())


@router.put("/voice-jobs/uploads/{upload_id}")
async def put_upload(upload_id: str, request: Request, service: ServiceDep,
                     merchant: MerchantDep, key: KeyDep):
    content = await request.body()
    return service.put_upload(
        merchant, upload_id, key, content,
        request.headers.get("content-type", "application/octet-stream"),
    )


@router.post("/voice-jobs", status_code=202)
def submit_voice(body: VoiceSubmit, service: ServiceDep, merchant: MerchantDep, key: KeyDep):
    return service.submit_voice(merchant, key, body.payload())


@router.get("/voice-jobs/{job_id}")
def get_voice_job(job_id: str, service: ServiceDep, merchant: MerchantDep):
    return service.voice_job(merchant, job_id)


@router.patch("/voice-jobs/{job_id}/draft")
def edit_draft(job_id: str, body: DraftEditRequest, service: ServiceDep,
               merchant: MerchantDep, key: KeyDep):
    return service.edit_draft(merchant, job_id, key, body.payload())


@router.post("/voice-jobs/{job_id}/clarifications")
def clarify(job_id: str, body: ClarificationRequest, service: ServiceDep,
            merchant: MerchantDep, key: KeyDep):
    return service.clarify(merchant, job_id, key, body.payload())


@router.post("/voice-jobs/{job_id}/confirm")
def confirm(job_id: str, body: ConfirmRequest, service: ServiceDep,
            merchant: MerchantDep, key: KeyDep):
    return service.confirm(merchant, job_id, key, body.payload())


@router.post("/voice-jobs/{job_id}/cancel")
def cancel(job_id: str, service: ServiceDep, merchant: MerchantDep, key: KeyDep):
    return service.cancel(merchant, job_id, key, {})


@router.get("/orders/{order_id}")
def get_order(order_id: str, service: ServiceDep, merchant: MerchantDep):
    return service.order(merchant, order_id)


@router.get("/invoices/{invoice_id}/pdf", name="download_invoice")
def invoice_pdf(invoice_id: str, service: ServiceDep, merchant: MerchantDep):
    invoice, order, customer = service.invoice(merchant, invoice_id)
    return Response(
        render_invoice(invoice, order, customer), media_type="application/pdf",
        headers={"Content-Disposition": f'inline; filename="{invoice["invoiceNumber"]}.pdf"'},
    )


@router.get("/orders/{order_id}/confirmation-audio", name="download_confirmation_audio")
def confirmation_audio(order_id: str, service: ServiceDep, merchant: MerchantDep):
    audio, content_type = service.confirmation_audio(merchant, order_id)
    suffix = "wav" if content_type == "audio/wav" else "mp3"
    return Response(
        audio, media_type=content_type,
        headers={"Content-Disposition": f'inline; filename="confirmation-{order_id}.{suffix}"'},
    )


@router.get("/customers/{customer_id}/ledger")
def ledger(customer_id: str, service: ServiceDep, merchant: MerchantDep):
    return service.ledger(merchant, customer_id)
