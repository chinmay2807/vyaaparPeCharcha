"""Deterministic application service: AI proposes, application code commits."""

from __future__ import annotations

import base64
import copy
import hashlib
import json
import re
import uuid
from datetime import date, datetime, timezone
from typing import Any, Callable

from .domain import validate_draft_command
from .providers import ProviderError, create_provider
from .store import JsonStore


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details: Any = None):
        super().__init__(message); self.status = status; self.code = code; self.details = details


def require(condition: Any, status: int, code: str, message: str, details: Any = None) -> None:
    if not condition: raise ApiError(status, code, message, details)


class Service:
    def __init__(self, store: JsonStore, provider: Any = None,
                 now: Callable[[], datetime] = lambda: datetime.now(timezone.utc)):
        self.store, self.provider, self.now = store, provider or create_provider(), now

    def health(self) -> dict[str, Any]:
        live = self.provider and self.provider.__class__.__name__.startswith("Live")
        return {"status": "ok", "service": "vyapaar-api",
                "providerMode": "live-hybrid" if live else "fixture",
                "speechProvider": "sarvam" if live else "offline",
                "reasoningProvider": "azure-openai" if live else "offline"}

    def customers(self, merchant: str, query: str = "") -> dict[str, Any]:
        self._ensure_merchant(merchant)
        return {"customers": [self._public_customer(x) for x in self._search("customers", merchant, query, "name")]}

    def create_customer(self, merchant: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        require(str(body.get("name", "")).strip(), 400, "INVALID_CUSTOMER", "name is required")
        def action(s: dict[str, Any]) -> dict[str, Any]:
            self._merchant(s, merchant); identifier = f"cus_{s['sequences']['customer']}"; s["sequences"]["customer"] += 1
            customer = {"id": identifier, "merchantId": merchant, "name": str(body["name"]).strip(),
                        "aliases": self._strings(body.get("aliases", [])), "phone": body.get("phone"),
                        "address": body.get("address"), "creditLimitPaise": self._integer(body.get("creditLimitPaise"), 0)}
            s["customers"].append(customer); self._audit(s, merchant, "CUSTOMER_CREATED", identifier)
            return self._public_customer(customer)
        return self._idempotent(merchant, "POST /v1/customers", key, body, action)

    def skus(self, merchant: str, query: str = "") -> dict[str, Any]:
        self._ensure_merchant(merchant)
        return {"skus": copy.deepcopy(self._search("skus", merchant, query, "label"))}

    def create_sku(self, merchant: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        require(str(body.get("label", "")).strip(), 400, "INVALID_SKU", "label is required")
        require(str(body.get("baseUnit", "")).strip(), 400, "INVALID_SKU", "baseUnit is required")
        require(isinstance(body.get("sellingPricePaise"), int) and body["sellingPricePaise"] >= 0,
                400, "INVALID_SKU", "sellingPricePaise must be a non-negative integer")
        def action(s: dict[str, Any]) -> dict[str, Any]:
            self._merchant(s, merchant)
            identifier = f"sku_{s['sequences']['sku']}"; s["sequences"]["sku"] += 1
            sku = {"id": identifier, "merchantId": merchant, "label": str(body["label"]).strip(),
                   "aliases": self._strings(body.get("aliases", [])), "baseUnit": body["baseUnit"],
                   "unitsPerCase": self._integer(body.get("unitsPerCase"), 1),
                   "sellingPricePaise": body["sellingPricePaise"],
                   "stockBaseUnits": self._integer(body.get("stockBaseUnits"), 0)}
            s["skus"].append(sku); self._audit(s, merchant, "SKU_CREATED", identifier); return copy.deepcopy(sku)
        return self._idempotent(merchant, "POST /v1/skus", key, body, action)

    def add_alias(self, merchant: str, sku_id: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        require(str(body.get("alias", "")).strip(), 400, "INVALID_ALIAS", "alias is required")
        def action(s: dict[str, Any]) -> dict[str, Any]:
            sku = self._owned(s["skus"], sku_id, merchant, "SKU_NOT_FOUND")
            sku["aliases"] = self._strings(sku["aliases"] + [body["alias"]]); self._audit(s, merchant, "SKU_ALIAS_ADDED", sku_id)
            return copy.deepcopy(sku)
        return self._idempotent(merchant, f"POST /v1/skus/{sku_id}/aliases", key, body, action)

    def create_upload(self, merchant: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        content_type, size = body.get("contentType"), body.get("sizeBytes")
        require(content_type in {"audio/webm", "video/webm", "audio/mpeg", "audio/mp3",
                                 "audio/mpeg3", "audio/x-mpeg-3", "audio/x-mp3", "audio/mp4",
                                 "audio/x-m4a", "audio/wav", "audio/x-wav", "audio/wave",
                                 "audio/3gpp", "audio/aac", "audio/x-aac", "audio/aiff",
                                 "audio/x-aiff", "audio/ogg", "audio/opus", "audio/flac",
                                 "audio/x-flac", "audio/amr", "audio/x-ms-wma"},
                415, "UNSUPPORTED_AUDIO", "Unsupported audio content type")
        require(isinstance(size, (int, float)) and 0 < size <= 15 * 1024 * 1024, 400, "INVALID_AUDIO_SIZE", "Audio must be between 1 byte and 15 MB")
        def action(_s: dict[str, Any]) -> dict[str, Any]:
            self._merchant(_s, merchant)
            identifier = f"upl_{uuid.uuid4()}"
            audio_key = f"{merchant}/{identifier}"
            _s["uploads"].append({"id": identifier, "merchantId": merchant, "audioKey": audio_key,
                                  "contentType": content_type, "maxSizeBytes": int(size), "contentBase64": None,
                                  "createdAt": self._iso()})
            return {"uploadId": identifier, "audioKey": audio_key,
                    "upload": {"method": "PUT", "url": f"/v1/voice-jobs/uploads/{identifier}", "expiresInSeconds": 300,
                               "headers": {"content-type": content_type}}}
        return self._idempotent(merchant, "POST /v1/voice-jobs/uploads", key, body, action)

    def put_upload(self, merchant: str, identifier: str, key: str, content: bytes, content_type: str) -> dict[str, Any]:
        require(0 < len(content) <= 15 * 1024 * 1024, 400, "INVALID_AUDIO_SIZE", "Audio must be between 1 byte and 15 MB")
        payload = {"sha256": hashlib.sha256(content).hexdigest(), "contentType": content_type}
        def action(s: dict[str, Any]) -> dict[str, Any]:
            upload = self._owned(s["uploads"], identifier, merchant, "UPLOAD_NOT_FOUND")
            require(content_type == upload["contentType"], 415, "UNSUPPORTED_AUDIO", "Content-Type does not match signed upload")
            require(len(content) <= upload["maxSizeBytes"], 400, "INVALID_AUDIO_SIZE", "Audio exceeds declared size")
            upload["contentBase64"] = base64.b64encode(content).decode("ascii"); upload["uploadedAt"] = self._iso()
            return {"uploadId": identifier, "audioKey": upload["audioKey"], "status": "UPLOADED"}
        return self._idempotent(merchant, f"PUT /v1/voice-jobs/uploads/{identifier}", key, payload, action)

    def submit_voice(self, merchant: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        require(str(body.get("transcript", "")).strip() or str(body.get("audioKey", "")).strip(),
                400, "INVALID_VOICE_JOB", "audioKey or transcript is required")
        self._ensure_merchant(merchant)
        submitted_transcript = str(body.get("transcript", "")).strip()
        if submitted_transcript:
            audio_fixture = f"TRANSCRIPT: {submitted_transcript}".encode()
        else:
            upload = self.store.read(lambda s: next((copy.deepcopy(x) for x in s["uploads"] if x["audioKey"] == body.get("audioKey") and x["merchantId"] == merchant), None))
            require(upload, 404, "UPLOAD_NOT_FOUND", "Uploaded audio was not found")
            require(upload.get("contentBase64"), 409, "UPLOAD_INCOMPLETE", "Audio upload has not completed")
            audio_fixture = base64.b64decode(upload["contentBase64"])
        try:
            transcription = self.provider.transcribe(
                audio_fixture, filename=str(body.get("filename", "voice.webm")),
                content_type=body.get("contentType", "audio/webm"), language_hint=body.get("languageHint"))
            transcript = str(transcription["text"])
            context = self.store.read(lambda s: {
                "customers": copy.deepcopy([x for x in s["customers"] if x["merchantId"] == merchant]),
                "skus": copy.deepcopy([x for x in s["skus"] if x["merchantId"] == merchant]),
                "reference_date": self.now().date().isoformat(),
            })
            provider_draft = self.provider.extract_order(transcript, context)
            validated = validate_draft_command(provider_draft)
            require(validated.ok, 502, "INVALID_PROVIDER_OUTPUT", "Provider returned an invalid draft",
                    [{"path": issue.path, "code": issue.code} for issue in validated.errors])
            proposal = self._provider_proposal(provider_draft)
        except ProviderError as error:
            raise ApiError(503 if error.retryable else 502, "PROVIDER_ERROR", "Voice provider could not process the request") from error
        def action(s: dict[str, Any]) -> dict[str, Any]:
            identifier = f"vj_{s['sequences']['voiceJob']}"; s["sequences"]["voiceJob"] += 1
            draft = {"id": f"draft_{uuid.uuid4()}", "voiceJobId": identifier, "merchantId": merchant,
                     "revision": 1, "intent": "create_sales_order", **proposal, "currency": "INR",
                     "createdAt": self._iso()}
            draft["validationErrors"] = self._validate(s, merchant, draft)
            clarification = self._next_clarification(s, merchant, draft)
            job = {"id": identifier, "merchantId": merchant, "audioKey": body.get("audioKey"),
                   "transcript": transcript, "language": transcription.get("language") or body.get("languageHint", "hi-IN"),
                   "state": "NEEDS_CLARIFICATION" if clarification else "READY_FOR_REVIEW",
                   "revision": 1, "committedOrderId": None, "createdAt": self._iso(), "updatedAt": self._iso()}
            s["voiceJobs"].append(job); s["drafts"].append(draft)
            if clarification: s["clarifications"].append({"id": f"clar_{uuid.uuid4()}", "voiceJobId": identifier, "revision": 1, "status": "OPEN", **clarification})
            self._audit(s, merchant, "VOICE_JOB_CREATED", identifier, {"state": job["state"]})
            return self._present_job(s, job)
        return self._idempotent(merchant, "POST /v1/voice-jobs", key, body, action)

    def voice_job(self, merchant: str, identifier: str) -> dict[str, Any]:
        return self.store.read(lambda s: self._present_job(s, self._owned(s["voiceJobs"], identifier, merchant, "VOICE_JOB_NOT_FOUND")))

    def edit_draft(self, merchant: str, identifier: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        def action(s: dict[str, Any]) -> dict[str, Any]:
            job = self._owned(s["voiceJobs"], identifier, merchant, "VOICE_JOB_NOT_FOUND")
            require(job["state"] in {"READY_FOR_REVIEW", "NEEDS_CLARIFICATION"}, 409, "INVALID_STATE", "Draft cannot be edited")
            self._revision(job, body); old = self._draft(s, job); draft = copy.deepcopy(old)
            for field in ("customerId", "deliveryDate", "items", "collectionAmountPaise"):
                if field in body: draft[field] = copy.deepcopy(body[field])
            draft.update({"id": f"draft_{uuid.uuid4()}", "revision": job["revision"] + 1, "createdAt": self._iso()})
            draft["validationErrors"] = self._validate(s, merchant, draft); s["drafts"].append(draft); job["revision"] += 1
            self._close_clarifications(s, identifier); clarification = self._next_clarification(s, merchant, draft)
            job["state"] = "NEEDS_CLARIFICATION" if clarification else "READY_FOR_REVIEW"; job["updatedAt"] = self._iso()
            if clarification: s["clarifications"].append({"id": f"clar_{uuid.uuid4()}", "voiceJobId": identifier, "revision": job["revision"], "status": "OPEN", **clarification})
            self._audit(s, merchant, "DRAFT_EDITED", identifier, {"revision": job["revision"]}); return self._present_job(s, job)
        return self._idempotent(merchant, f"PATCH /v1/voice-jobs/{identifier}/draft", key, body, action)

    def clarify(self, merchant: str, identifier: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        def action(s: dict[str, Any]) -> dict[str, Any]:
            job = self._owned(s["voiceJobs"], identifier, merchant, "VOICE_JOB_NOT_FOUND")
            require(job["state"] == "NEEDS_CLARIFICATION", 409, "INVALID_STATE", "Job does not need clarification"); self._revision(job, body)
            clarification = next((x for x in s["clarifications"] if x["voiceJobId"] == identifier and x["status"] == "OPEN"), None)
            require(clarification, 409, "NO_OPEN_CLARIFICATION", "No clarification is open")
            draft = copy.deepcopy(self._draft(s, job)); self._apply_answer(s, merchant, draft, clarification, body.get("answer"))
            job["revision"] += 1; draft.update({"id": f"draft_{uuid.uuid4()}", "revision": job["revision"], "createdAt": self._iso()})
            draft["validationErrors"] = self._validate(s, merchant, draft); s["drafts"].append(draft)
            clarification.update({"status": "RESOLVED", "answer": self._safe_answer(body.get("answer")), "resolvedAt": self._iso()})
            following = self._next_clarification(s, merchant, draft); job["state"] = "NEEDS_CLARIFICATION" if following else "READY_FOR_REVIEW"; job["updatedAt"] = self._iso()
            if following: s["clarifications"].append({"id": f"clar_{uuid.uuid4()}", "voiceJobId": identifier, "revision": job["revision"], "status": "OPEN", **following})
            self._audit(s, merchant, "CLARIFICATION_RESOLVED", identifier, {"fieldPath": clarification["fieldPath"]}); return self._present_job(s, job)
        return self._idempotent(merchant, f"POST /v1/voice-jobs/{identifier}/clarifications", key, body, action)

    def confirm(self, merchant: str, identifier: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        def action(s: dict[str, Any]) -> dict[str, Any]:
            job = self._owned(s["voiceJobs"], identifier, merchant, "VOICE_JOB_NOT_FOUND")
            if job["state"] == "COMMITTED": return self._confirmation(s, job, True)
            require(job["state"] == "READY_FOR_REVIEW", 409, "INVALID_STATE", "Job is not ready for confirmation"); self._revision(job, body)
            draft = self._draft(s, job); errors = self._validate(s, merchant, draft)
            require(not errors, 422, errors[0]["code"] if errors else "INVALID_DRAFT", "Draft did not pass deterministic validation", errors)
            customer = self._owned(s["customers"], draft["customerId"], merchant, "CUSTOMER_NOT_FOUND"); lines = []
            for item in draft["items"]:
                sku = self._owned(s["skus"], item["skuId"], merchant, "SKU_NOT_FOUND"); base = self._base_units(item, sku)
                require(sku["stockBaseUnits"] >= base, 409, "INSUFFICIENT_STOCK", f"Insufficient stock for {sku['label']}", {"skuId": sku["id"]})
                catalog_price = sku["sellingPricePaise"] if item["unit"] == "case" else round(sku["sellingPricePaise"] / max(sku.get("unitsPerCase", 1), 1))
                unit_price = item.get("quotedUnitPricePaise")
                if unit_price is None: unit_price = catalog_price
                lines.append({"id": f"oli_{uuid.uuid4()}", "skuId": sku["id"], "label": sku["label"],
                              "quantity": item["quantity"], "unit": item["unit"], "baseUnits": base,
                              "unitPricePaise": unit_price, "catalogUnitPricePaise": catalog_price,
                              "priceSource": "SPOKEN_QUOTE" if item.get("quotedUnitPricePaise") is not None else "CATALOG",
                              "lineTotalPaise": unit_price * item["quantity"]})
            total = sum(x["lineTotalPaise"] for x in lines); order_id = f"ord_{uuid.uuid4()}"
            order = {"id": order_id, "merchantId": merchant, "customerId": customer["id"], "voiceJobId": identifier,
                     "orderNumber": f"VL-{s['sequences']['order']}", "deliveryDate": draft["deliveryDate"], "currency": "INR",
                     "lines": lines, "totalPaise": total,
                     "collectionAmountPaise": draft.get("collectionAmountPaise"),
                     "status": "CONFIRMED", "createdAt": self._iso()}; s["sequences"]["order"] += 1
            for line in lines:
                sku = self._owned(s["skus"], line["skuId"], merchant, "SKU_NOT_FOUND"); sku["stockBaseUnits"] -= line["baseUnits"]
                s["inventoryMovements"].append({"id": f"mov_{uuid.uuid4()}", "merchantId": merchant, "skuId": sku["id"],
                                                 "sourceType": "SALES_ORDER", "sourceId": order_id, "deltaBaseUnits": -line["baseUnits"], "occurredAt": self._iso()})
            invoice = {"id": f"inv_{uuid.uuid4()}", "merchantId": merchant, "customerId": customer["id"], "orderId": order_id,
                       "invoiceNumber": f"INV-{s['sequences']['invoice']}", "totalPaise": total, "currency": "INR", "status": "ISSUED", "issuedAt": self._iso()}; s["sequences"]["invoice"] += 1
            s["orders"].append(order); s["invoices"].append(invoice)
            s["ledgerEntries"].append({"id": f"led_{uuid.uuid4()}", "merchantId": merchant, "customerId": customer["id"], "type": "SALES_INVOICE",
                                       "debitPaise": total, "creditPaise": 0, "occurredAt": self._iso(), "reference": invoice["invoiceNumber"], "orderId": order_id})
            if draft.get("collectionAmountPaise"):
                s["ledgerEntries"].append({"id": f"led_{uuid.uuid4()}", "merchantId": merchant,
                                           "customerId": customer["id"], "type": "PAYMENT_COLLECTION",
                                           "debitPaise": 0, "creditPaise": draft["collectionAmountPaise"],
                                           "occurredAt": self._iso(), "reference": f"Collection for {order['orderNumber']}",
                                           "orderId": order_id})
            s["outboxEvents"].append({"id": f"evt_{uuid.uuid4()}", "merchantId": merchant, "type": "ORDER_CONFIRMED", "aggregateId": order_id, "status": "PENDING", "createdAt": self._iso()})
            job.update({"state": "COMMITTED", "committedOrderId": order_id, "updatedAt": self._iso()}); self._audit(s, merchant, "ORDER_COMMITTED", order_id)
            return self._confirmation(s, job, False)
        result = self._idempotent(merchant, f"POST /v1/voice-jobs/{identifier}/confirm", key, body, action)
        if body.get("spokenConfirmation"):
            try:
                speech = self.provider.synthesize_confirmation(result["confirmationText"], language=body.get("language", "hi-IN"))
                encoded_audio = base64.b64encode(speech["audio"]).decode("ascii")
                self._save_audio_artifact(
                    merchant, result["order"]["id"], encoded_audio,
                    speech["content_type"], speech.get("language", "hi-IN"), speech.get("model"),
                )
                result["voiceConfirmation"] = {"status": "READY", "contentType": speech["content_type"],
                                                "audioBase64": encoded_audio,
                                                "language": speech.get("language", "hi-IN"), "model": speech.get("model")}
            except ProviderError:
                # The commercial transaction is already committed; optional TTS must never make it look failed.
                result["voiceConfirmation"] = {"status": "FAILED", "code": "TTS_UNAVAILABLE"}
        return result

    def confirmation_audio(self, merchant: str, order_id: str) -> tuple[bytes, str]:
        def read(s: dict[str, Any]) -> tuple[bytes, str]:
            self._owned(s["orders"], order_id, merchant, "ORDER_NOT_FOUND")
            artifact = next(
                (item for item in s.get("artifacts", [])
                 if item["merchantId"] == merchant and item["orderId"] == order_id
                 and item["kind"] == "CONFIRMATION_AUDIO"),
                None,
            )
            require(artifact, 404, "AUDIO_NOT_FOUND", "Confirmation audio is not available")
            return base64.b64decode(artifact["contentBase64"]), artifact["contentType"]

        return self.store.read(read)

    def cancel(self, merchant: str, identifier: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        def action(s: dict[str, Any]) -> dict[str, Any]:
            job = self._owned(s["voiceJobs"], identifier, merchant, "VOICE_JOB_NOT_FOUND")
            require(job["state"] not in {"COMMITTED", "CANCELLED"}, 409, "INVALID_STATE", "Job cannot be cancelled")
            job.update({"state": "CANCELLED", "updatedAt": self._iso()}); self._close_clarifications(s, identifier); self._audit(s, merchant, "VOICE_JOB_CANCELLED", identifier)
            return self._present_job(s, job)
        return self._idempotent(merchant, f"POST /v1/voice-jobs/{identifier}/cancel", key, body, action)

    def order(self, merchant: str, identifier: str) -> dict[str, Any]:
        return self.store.read(lambda s: copy.deepcopy(self._owned(s["orders"], identifier, merchant, "ORDER_NOT_FOUND")))

    def invoice(self, merchant: str, identifier: str) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        def read(s: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
            inv = self._owned(s["invoices"], identifier, merchant, "INVOICE_NOT_FOUND"); order = self._owned(s["orders"], inv["orderId"], merchant, "ORDER_NOT_FOUND")
            customer = self._owned(s["customers"], inv["customerId"], merchant, "CUSTOMER_NOT_FOUND"); return copy.deepcopy(inv), copy.deepcopy(order), self._public_customer(customer)
        return self.store.read(read)

    def ledger(self, merchant: str, customer_id: str) -> dict[str, Any]:
        def read(s: dict[str, Any]) -> dict[str, Any]:
            customer = self._owned(s["customers"], customer_id, merchant, "CUSTOMER_NOT_FOUND"); balance = 0; entries = []
            for item in sorted((x for x in s["ledgerEntries"] if x["merchantId"] == merchant and x["customerId"] == customer_id), key=lambda x: x["occurredAt"]):
                balance += item["debitPaise"] - item["creditPaise"]; entries.append({**copy.deepcopy(item), "balancePaise": balance})
            return {"customer": self._public_customer(customer), "currency": "INR", "balancePaise": balance, "entries": entries}
        return self.store.read(read)

    def create_reconciliation(self, merchant: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        require(str(body.get("documentName", "")).strip(), 400, "INVALID_DOCUMENT", "documentName is required")
        self._ensure_merchant(merchant)
        provider_input = {"supplier_name": body.get("supplierName"), "invoice_number": body.get("invoiceNumber"),
                          "invoice_date": body.get("invoiceDate"), "currency": "INR",
                          "items": [{"spoken_name": x.get("spokenName", x.get("label", "")), "quantity": x.get("quantity", 0),
                                     "unit": x.get("unit", "piece"), "unit_cost": x.get("unitCostPaise", 0) / 100}
                                    for x in body.get("items", [])]}
        try:
            if body.get("documentBase64"):
                try: document_bytes = base64.b64decode(body["documentBase64"], validate=True)
                except (ValueError, TypeError): raise ApiError(400, "INVALID_DOCUMENT", "documentBase64 is invalid") from None
                require(len(document_bytes) <= 15 * 1024 * 1024, 413, "PAYLOAD_TOO_LARGE", "Document is too large")
            else:
                document_bytes = json.dumps(provider_input).encode() if body.get("items") else b"offline demo document"
            extracted = self.provider.extract_document(document_bytes, filename=str(body["documentName"]), content_type=body.get("contentType"))
        except ProviderError as error:
            raise ApiError(503 if error.retryable else 502, "PROVIDER_ERROR", "Document provider could not process the request") from error
        def action(s: dict[str, Any]) -> dict[str, Any]:
            items = []
            for raw in extracted.get("items", []):
                spoken = str(raw.get("spoken_name", "")); sku = self._resolve_sku(spoken, s["skus"], merchant)
                items.append({"spokenName": spoken, "skuId": (sku or {}).get("id"), "quantity": raw.get("quantity"),
                              "unit": self._unit(raw.get("unit")) or ((sku or {}).get("baseUnit")), "unitCostPaise": round(raw.get("unit_cost", 0) * 100)})
            identifier = f"rec_{s['sequences']['reconciliation']}"; s["sequences"]["reconciliation"] += 1
            doc = {"id": identifier, "merchantId": merchant, "documentName": str(body["documentName"]), "state": "REVIEW_REQUIRED", "revision": 1,
                   "supplierName": extracted.get("supplier_name") or "Demo Supplier", "supplierInvoiceNumber": extracted.get("invoice_number") or f"SUP-{identifier}",
                   "items": items, "createdAt": self._iso(), "appliedAt": None}; s["reconciliationDocuments"].append(doc); self._audit(s, merchant, "RECONCILIATION_CREATED", identifier)
            return self._public_reconciliation(doc)
        return self._idempotent(merchant, "POST /v1/reconciliation-documents", key, body, action)

    def reconciliation(self, merchant: str, identifier: str) -> dict[str, Any]:
        return self.store.read(lambda s: self._public_reconciliation(self._owned(s["reconciliationDocuments"], identifier, merchant, "RECONCILIATION_NOT_FOUND")))

    def apply_reconciliation(self, merchant: str, identifier: str, key: str, body: dict[str, Any]) -> dict[str, Any]:
        def action(s: dict[str, Any]) -> dict[str, Any]:
            doc = self._owned(s["reconciliationDocuments"], identifier, merchant, "RECONCILIATION_NOT_FOUND")
            if doc["state"] == "APPLIED": return {**self._public_reconciliation(doc), "idempotentReplay": True}
            require(doc["state"] == "REVIEW_REQUIRED", 409, "INVALID_STATE", "Document is not reviewable"); self._revision(doc, body)
            require(doc["items"], 422, "EMPTY_DOCUMENT", "No document items to apply"); planned = []
            for item in doc["items"]:
                require(isinstance(item["quantity"], (int, float)) and item["quantity"] > 0, 422, "INVALID_QUANTITY", "Quantities must be positive")
                sku = self._owned(s["skus"], item.get("skuId"), merchant, "UNRESOLVED_SKU"); planned.append((sku, self._base_units(item, sku)))
            for sku, quantity in planned:
                sku["stockBaseUnits"] += quantity; s["inventoryMovements"].append({"id": f"mov_{uuid.uuid4()}", "merchantId": merchant, "skuId": sku["id"], "sourceType": "RECONCILIATION", "sourceId": identifier, "deltaBaseUnits": quantity, "occurredAt": self._iso()})
            doc.update({"state": "APPLIED", "appliedAt": self._iso()}); self._audit(s, merchant, "RECONCILIATION_APPLIED", identifier)
            return {**self._public_reconciliation(doc), "idempotentReplay": False}
        return self._idempotent(merchant, f"POST /v1/reconciliation-documents/{identifier}/apply", key, body, action)

    # IDs and stock remain canonical; explicit spoken prices and collection instructions survive review.
    @staticmethod
    def _provider_proposal(draft: dict[str, Any]) -> dict[str, Any]:
        customer, delivery = draft["customer"], draft["delivery_date"]
        return {"customerId": customer.get("candidate_id"), "customerSpokenName": customer.get("spoken_name"),
                "deliveryDate": delivery.get("value"),
                "items": [{"spokenName": x.get("spoken_name"), "skuId": x.get("candidate_sku_id"),
                           "quantity": x.get("quantity"), "unit": Service._unit(x.get("unit")), "confidence": x.get("confidence"),
                           "quotedUnitPricePaise": round(x["quoted_unit_price"] * 100) if x.get("quoted_unit_price") is not None else None,
                           "evidence": x.get("evidence")} for x in draft.get("items", [])],
                "mentionedPreviousBalancePaise": round(draft["mentioned_previous_balance"] * 100) if draft.get("mentioned_previous_balance") is not None else None,
                "collectionAmountPaise": round(draft["collection_amount"] * 100) if draft.get("collection_amount") is not None else None,
                "evidence": {"customer": customer.get("evidence"), "collection": draft.get("collection_evidence", "")},
                "warnings": list(draft.get("warnings", []))}

    def _validate(self, s: dict[str, Any], merchant: str, draft: dict[str, Any]) -> list[dict[str, Any]]:
        errors = []
        if not any(x["id"] == draft.get("customerId") and x["merchantId"] == merchant for x in s["customers"]): errors.append({"code": "AMBIGUOUS_CUSTOMER", "fieldPath": "customerId"})
        if not draft.get("deliveryDate"): errors.append({"code": "MISSING_DELIVERY_DATE", "fieldPath": "deliveryDate"})
        if not draft.get("items"): errors.append({"code": "MISSING_ITEMS", "fieldPath": "items"})
        for index, item in enumerate(draft.get("items", [])):
            sku = next((x for x in s["skus"] if x["id"] == item.get("skuId") and x["merchantId"] == merchant), None)
            if not sku: errors.append({"code": "UNRESOLVED_SKU", "fieldPath": f"items.{index}.skuId"})
            if not isinstance(item.get("quantity"), (int, float)) or item["quantity"] <= 0: errors.append({"code": "MISSING_QUANTITY", "fieldPath": f"items.{index}.quantity"})
            if not item.get("unit"): errors.append({"code": "MISSING_UNIT", "fieldPath": f"items.{index}.unit"})
            quoted = item.get("quotedUnitPricePaise")
            if quoted is not None and (isinstance(quoted, bool) or not isinstance(quoted, int) or quoted < 0): errors.append({"code": "INVALID_QUOTED_PRICE", "fieldPath": f"items.{index}.quotedUnitPricePaise"})
            if sku and item.get("quantity") and item.get("unit") and self._base_units(item, sku) > sku["stockBaseUnits"]: errors.append({"code": "INSUFFICIENT_STOCK", "fieldPath": f"items.{index}.quantity", "available": sku["stockBaseUnits"]})
        collection = draft.get("collectionAmountPaise")
        if collection is not None and (isinstance(collection, bool) or not isinstance(collection, int) or collection < 0): errors.append({"code": "INVALID_COLLECTION_AMOUNT", "fieldPath": "collectionAmountPaise"})
        if draft.get("customerId") and draft.get("mentionedPreviousBalancePaise") is not None:
            actual = sum(x["debitPaise"] - x["creditPaise"] for x in s["ledgerEntries"] if x["merchantId"] == merchant and x["customerId"] == draft["customerId"])
            if abs(actual - draft["mentionedPreviousBalancePaise"]) > 100: errors.append({"code": "BALANCE_MISMATCH", "fieldPath": "mentionedPreviousBalancePaise", "systemBalancePaise": actual})
        return errors

    def _next_clarification(self, s: dict[str, Any], merchant: str, draft: dict[str, Any]) -> dict[str, Any] | None:
        errors = self._validate(s, merchant, draft)
        if not errors: return None
        error = errors[0]; path = error["fieldPath"]
        if error["code"] == "AMBIGUOUS_CUSTOMER": return {"fieldPath": path, "code": error["code"], "question": f"‘{draft.get('customerSpokenName', 'customer')}’ kaun sa customer hai?", "options": [{"value": x["id"], "label": x["name"]} for x in s["customers"] if x["merchantId"] == merchant]}
        if error["code"] == "MISSING_DELIVERY_DATE": return {"fieldPath": path, "code": error["code"], "question": "Delivery date kya hai? (YYYY-MM-DD)", "options": []}
        match = re.match(r"items\.(\d+)\.", path)
        if match:
            item = draft["items"][int(match.group(1))]; label = item.get("spokenName", "Item")
            if error["code"] == "MISSING_UNIT": return {"fieldPath": path, "code": error["code"], "question": f"{label} ki {item.get('quantity')} case ya pieces?", "options": [{"value": "case", "label": "Case / peti"}, {"value": "piece", "label": "Piece / bottle"}]}
            if error["code"] == "MISSING_QUANTITY": return {"fieldPath": path, "code": error["code"], "question": f"{label} kitna bhejna hai?", "options": []}
            if error["code"] == "INSUFFICIENT_STOCK": return {"fieldPath": path, "code": error["code"], "question": f"{label} ka stock kam hai. Quantity badlein?", "options": []}
        if error["code"] == "BALANCE_MISMATCH": return {"fieldPath": path, "code": error["code"], "question": f"System balance ₹{error['systemBalancePaise']/100:,.2f} hai. Use karein?", "options": [{"value": error["systemBalancePaise"], "label": "Use system balance"}]}
        return {"fieldPath": path, "code": error["code"], "question": "Missing information provide karein.", "options": []}

    def _apply_answer(self, s: dict[str, Any], merchant: str, draft: dict[str, Any], clarification: dict[str, Any], answer: Any) -> None:
        parts = clarification["fieldPath"].split(".")
        if parts[0] == "customerId": self._owned(s["customers"], answer, merchant, "INVALID_CLARIFICATION"); draft["customerId"] = answer
        elif parts[0] == "deliveryDate":
            try: draft["deliveryDate"] = date.fromisoformat(str(answer)).isoformat()
            except ValueError: raise ApiError(400, "INVALID_CLARIFICATION", "Delivery date must use YYYY-MM-DD") from None
        elif parts[0] == "items":
            item = draft["items"][int(parts[1])]
            if parts[2] == "unit": require(answer in {"case", "piece", "kg", "pouch"}, 400, "INVALID_CLARIFICATION", "Unit is invalid"); item["unit"] = answer
            elif parts[2] == "quantity": require(isinstance(answer, (int, float)) and answer > 0, 400, "INVALID_CLARIFICATION", "Quantity must be positive"); item["quantity"] = answer
        elif parts[0] == "mentionedPreviousBalancePaise": draft[parts[0]] = int(answer)

    def _idempotent(self, merchant: str, route: str, key: str, body: dict[str, Any], action: Callable[[dict[str, Any]], dict[str, Any]]) -> dict[str, Any]:
        require(isinstance(key, str) and re.fullmatch(r"[A-Za-z0-9._:-]{8,200}", key), 400, "IDEMPOTENCY_KEY_REQUIRED", "Mutating requests require a valid Idempotency-Key")
        fingerprint = hashlib.sha256(json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest(); scope = f"{merchant}:{route}:{key}"
        def transaction(s: dict[str, Any]) -> dict[str, Any]:
            existing = s["idempotency"].get(scope)
            if existing:
                require(existing["fingerprint"] == fingerprint, 409, "IDEMPOTENCY_CONFLICT", "Idempotency key was reused with a different payload")
                return copy.deepcopy(existing["response"])
            result = action(s); s["idempotency"][scope] = {"fingerprint": fingerprint, "response": copy.deepcopy(result), "createdAt": self._iso()}; return result
        return self.store.transaction(transaction)

    def _confirmation(self, s: dict[str, Any], job: dict[str, Any], replay: bool) -> dict[str, Any]:
        order = next(x for x in s["orders"] if x["id"] == job["committedOrderId"]); invoice = next(x for x in s["invoices"] if x["orderId"] == order["id"]); customer = next(x for x in s["customers"] if x["id"] == order["customerId"])
        balance = sum(x["debitPaise"] - x["creditPaise"] for x in s["ledgerEntries"] if x["customerId"] == customer["id"] and x["merchantId"] == job["merchantId"])
        collection = order.get("collectionAmountPaise")
        collection_text = f" ₹{collection/100:,.2f} collection bhi record hua." if collection else ""
        return {"order": copy.deepcopy(order), "invoice": copy.deepcopy(invoice), "customerBalancePaise": balance,
                "confirmationText": f"Order {order['orderNumber']} ban gaya. {customer['name']} ka invoice ₹{order['totalPaise']/100:,.2f}.{collection_text}", "idempotentReplay": replay}

    def _save_audio_artifact(self, merchant: str, order_id: str, content: str,
                             content_type: str, language: str, model: str | None) -> None:
        def save(s: dict[str, Any]) -> None:
            existing = next(
                (item for item in s.setdefault("artifacts", [])
                 if item["merchantId"] == merchant and item["orderId"] == order_id
                 and item["kind"] == "CONFIRMATION_AUDIO"),
                None,
            )
            payload = {"merchantId": merchant, "orderId": order_id,
                       "kind": "CONFIRMATION_AUDIO", "contentBase64": content,
                       "contentType": content_type, "language": language, "model": model,
                       "createdAt": self._iso()}
            if existing:
                existing.update(payload)
            else:
                s["artifacts"].append({"id": f"art_{uuid.uuid4()}", **payload})

        self.store.transaction(save)

    def _present_job(self, s: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]:
        return {key: copy.deepcopy(job[key]) for key in ("id", "state", "revision", "transcript", "language", "committedOrderId", "createdAt", "updatedAt")} | {"draft": copy.deepcopy(self._draft(s, job)), "clarification": copy.deepcopy(next((x for x in s["clarifications"] if x["voiceJobId"] == job["id"] and x["status"] == "OPEN"), None))}

    def _draft(self, s: dict[str, Any], job: dict[str, Any]) -> dict[str, Any]: return next(x for x in s["drafts"] if x["voiceJobId"] == job["id"] and x["revision"] == job["revision"])
    def _revision(self, entity: dict[str, Any], body: dict[str, Any]) -> None: require(body.get("revision") == entity["revision"], 409, "STALE_DRAFT", "Revision is stale", {"currentRevision": entity["revision"]})
    def _close_clarifications(self, s: dict[str, Any], identifier: str) -> None:
        for item in s["clarifications"]:
            if item["voiceJobId"] == identifier and item["status"] == "OPEN": item["status"] = "CANCELLED"
    def _search(self, collection: str, merchant: str, query: str, label: str) -> list[dict[str, Any]]:
        needle = query.strip().casefold(); return self.store.read(lambda s: [copy.deepcopy(x) for x in s[collection] if x["merchantId"] == merchant and (not needle or needle in str(x[label]).casefold() or any(needle in str(a).casefold() for a in x.get("aliases", [])))])
    @staticmethod
    def _owned(items: list[dict[str, Any]], identifier: Any, merchant: str, code: str) -> dict[str, Any]:
        found = next((x for x in items if x.get("id") == identifier and x.get("merchantId") == merchant), None); require(found, 404, code, "Resource was not found"); return found
    @staticmethod
    def _merchant(s: dict[str, Any], merchant: str) -> dict[str, Any]:
        found = next((x for x in s["merchants"] if x["id"] == merchant), None)
        require(found, 404, "MERCHANT_NOT_FOUND", "Merchant was not found")
        return found
    def _ensure_merchant(self, merchant: str) -> None:
        self.store.read(lambda s: self._merchant(s, merchant))
    @staticmethod
    def _public_customer(customer: dict[str, Any]) -> dict[str, Any]: return {key: copy.deepcopy(value) for key, value in customer.items() if key != "phone"}
    @staticmethod
    def _public_reconciliation(doc: dict[str, Any]) -> dict[str, Any]: return {key: copy.deepcopy(value) for key, value in doc.items() if key != "merchantId"}
    @staticmethod
    def _strings(values: list[Any]) -> list[str]: return list(dict.fromkeys(str(x).strip() for x in values if str(x).strip()))
    @staticmethod
    def _integer(value: Any, fallback: int) -> int: return value if isinstance(value, int) else fallback
    @staticmethod
    def _unit(value: Any) -> str | None:
        if not value: return None
        normalized = str(value).casefold()
        if normalized in {"peti", "case", "crate", "carton"}: return "case"
        if normalized in {"bottle", "bottles", "piece", "pieces", "pcs"}: return "piece"
        if normalized in {"kilo", "kg"}: return "kg"
        return normalized
    @staticmethod
    def _base_units(item: dict[str, Any], sku: dict[str, Any]) -> int | float: return item["quantity"] * sku.get("unitsPerCase", 1) if item["unit"] == "case" else item["quantity"]
    @staticmethod
    def _resolve_sku(spoken: str, skus: list[dict[str, Any]], merchant: str) -> dict[str, Any] | None:
        lower = spoken.casefold(); return next((x for x in skus if x["merchantId"] == merchant and any(str(a).casefold() in lower for a in [x["label"], *x.get("aliases", [])])), None)
    @staticmethod
    def _safe_answer(answer: Any) -> Any: return answer[:100] if isinstance(answer, str) else answer
    def _iso(self) -> str: return self.now().isoformat()
    def _audit(self, s: dict[str, Any], merchant: str, action: str, entity: str, metadata: dict[str, Any] | None = None) -> None:
        s["audit"].append({"id": f"aud_{uuid.uuid4()}", "merchantId": merchant, "action": action, "entityId": entity, "metadata": metadata or {}, "occurredAt": self._iso()})
