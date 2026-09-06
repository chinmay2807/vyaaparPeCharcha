from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_idempotency_key, get_merchant_id, get_service
from ..schemas import CustomerCreate
from ..service import Service

router = APIRouter(prefix="/v1", tags=["catalog"])
ServiceDep = Annotated[Service, Depends(get_service)]
MerchantDep = Annotated[str, Depends(get_merchant_id)]
KeyDep = Annotated[str, Depends(get_idempotency_key)]


@router.get("/customers")
def customers(service: ServiceDep, merchant: MerchantDep, query: str = Query("")):
    return service.customers(merchant, query)


@router.post("/customers", status_code=201)
def create_customer(body: CustomerCreate, service: ServiceDep, merchant: MerchantDep, key: KeyDep):
    return service.create_customer(merchant, key, body.payload())
