from typing import Annotated

from fastapi import APIRouter, Depends

from ..dependencies import get_idempotency_key, get_merchant_id, get_service
from ..schemas import ReconciliationCreate, RevisionRequest
from ..service import Service

router = APIRouter(prefix="/v1/reconciliation-documents", tags=["reconciliation"])
ServiceDep = Annotated[Service, Depends(get_service)]
MerchantDep = Annotated[str, Depends(get_merchant_id)]
KeyDep = Annotated[str, Depends(get_idempotency_key)]


@router.post("", status_code=201)
def create_document(body: ReconciliationCreate, service: ServiceDep,
                    merchant: MerchantDep, key: KeyDep):
    return service.create_reconciliation(merchant, key, body.payload())


@router.get("/{document_id}")
def get_document(document_id: str, service: ServiceDep, merchant: MerchantDep):
    return service.reconciliation(merchant, document_id)


@router.post("/{document_id}/apply")
def apply_document(document_id: str, body: RevisionRequest, service: ServiceDep,
                   merchant: MerchantDep, key: KeyDep):
    return service.apply_reconciliation(merchant, document_id, key, body.payload())
