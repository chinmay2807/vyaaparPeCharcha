"""Shared FastAPI dependencies."""

from typing import Annotated

from fastapi import Header, Request

from .service import Service


def get_service(request: Request) -> Service:
    return request.app.state.service


def get_merchant_id(
    x_merchant_id: Annotated[str, Header(alias="X-Merchant-Id")] = "mer_demo",
) -> str:
    return x_merchant_id


def get_idempotency_key(
    idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None,
) -> str:
    return idempotency_key or ""
