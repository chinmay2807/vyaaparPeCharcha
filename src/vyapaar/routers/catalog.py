from typing import Annotated

from fastapi import APIRouter, Depends, Query

from ..dependencies import get_idempotency_key, get_merchant_id, get_service
from ..schemas import AliasCreate, CustomerCreate, SkuCreate
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


@router.get("/skus")
def skus(service: ServiceDep, merchant: MerchantDep, query: str = Query("")):
    return service.skus(merchant, query)


@router.post("/skus", status_code=201)
def create_sku(body: SkuCreate, service: ServiceDep, merchant: MerchantDep, key: KeyDep):
    return service.create_sku(merchant, key, body.payload())


@router.post("/skus/{sku_id}/aliases")
def add_alias(sku_id: str, body: AliasCreate, service: ServiceDep,
              merchant: MerchantDep, key: KeyDep):
    return service.add_alias(merchant, sku_id, key, body.payload())
