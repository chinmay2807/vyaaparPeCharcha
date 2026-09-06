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

from .domain import DomainError, resolve_relative_date, validate_draft_command
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
            timezone_name = self.store.read(lambda s: self._merchant(s, merchant)["timezone"])
            context = self.store.read(lambda s: {
                "customers": copy.deepcopy([x for x in s["customers"] if x["merchantId"] == merchant]),
                "reference_date": self.now().date().isoformat(),
            })
            provider_draft = self.provider.extract_order(transcript, context)
            validated = validate_draft_command(provider_draft)
            require(validated.ok, 502, "INVALID_PROVIDER_OUTPUT", "Provider returned an invalid draft",
                    [{"path": issue.path, "code": issue.code} for issue in validated.errors])
            intent = provider_draft.get("intent")
            if intent == "create_sales_order":
                self._apply_extraction_defaults(provider_draft, timezone_name)
            proposal = self._provider_proposal(provider_draft)
        except ProviderError as error:
            raise ApiError(503 if error.retryable else 502, "PROVIDER_ERROR", "Voice provider could not process the request") from error
        language = transcription.get("language") or body.get("languageHint", "hi-IN")
        if intent == "query_orders":
            action = self._action_query(merchant, body, transcript, language, proposal.get("query") or {})
        elif intent == "update_order_status":
            action = self._action_status_update(merchant, body, transcript, language, proposal.get("statusUpdate") or {})
        else:
            action = self._action_create_order(merchant, body, transcript, language, proposal)
        result = self._idempotent(merchant, "POST /v1/voice-jobs", key, body, action)
        if result.get("state") == "ANSWERED":
            self._speak_answer(result, language)
        return result

    def _speak_answer(self, job: dict[str, Any], language: str) -> None:
        try:
            speech = self.provider.synthesize_confirmation(job["queryResult"]["answerText"], language=language)
            job["voiceAnswer"] = {"status": "READY", "contentType": speech["content_type"],
                                   "audioBase64": base64.b64encode(speech["audio"]).decode("ascii"),
                                   "language": speech.get("language", language)}
        except ProviderError:
            job["voiceAnswer"] = {"status": "FAILED", "code": "TTS_UNAVAILABLE"}

    def _action_create_order(self, merchant: str, body: dict[str, Any], transcript: str, language: str,
                              proposal: dict[str, Any]) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def action(s: dict[str, Any]) -> dict[str, Any]:
            identifier = f"vj_{s['sequences']['voiceJob']}"; s["sequences"]["voiceJob"] += 1
            draft = {"id": f"draft_{uuid.uuid4()}", "voiceJobId": identifier, "merchantId": merchant,
                     "revision": 1, "intent": "create_sales_order", **proposal, "currency": "INR",
                     "createdAt": self._iso()}
            draft["validationErrors"] = self._validate(s, merchant, draft)
            clarification = self._next_clarification(s, merchant, draft)
            job = {"id": identifier, "merchantId": merchant, "audioKey": body.get("audioKey"),
                   "transcript": transcript, "language": language,
                   "state": "NEEDS_CLARIFICATION" if clarification else "READY_FOR_REVIEW",
                   "revision": 1, "committedOrderId": None, "createdAt": self._iso(), "updatedAt": self._iso()}
            s["voiceJobs"].append(job); s["drafts"].append(draft)
            if clarification: s["clarifications"].append({"id": f"clar_{uuid.uuid4()}", "voiceJobId": identifier, "revision": 1, "status": "OPEN", **clarification})
            self._audit(s, merchant, "VOICE_JOB_CREATED", identifier, {"state": job["state"]})
            return self._present_job(s, job)
        return action

    def _action_query(self, merchant: str, body: dict[str, Any], transcript: str, language: str,
                       query: dict[str, Any]) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def action(s: dict[str, Any]) -> dict[str, Any]:
            identifier = f"vj_{s['sequences']['voiceJob']}"; s["sequences"]["voiceJob"] += 1
            spoken_name = str(query.get("customerSpokenName") or "").strip()
            customer = self._match_customer(s, merchant, spoken_name) if spoken_name else None
            require(not spoken_name or customer, 422, "CUSTOMER_NOT_FOUND", f"No customer matches '{spoken_name}'")
            orders = [o for o in s["orders"] if o["merchantId"] == merchant
                      and (customer is None or o["customerId"] == customer["id"])
                      and (not query.get("statusFilter") or o["status"] == query["statusFilter"])]
            status_label = {"CONFIRMED": "pending", "DELIVERED": "delivered"}.get(query.get("statusFilter"), "")
            who = f" for {customer['name']}" if customer else ""
            answer_text = f"{len(orders)} {status_label} order{'s' if len(orders) != 1 else ''}{who}.".replace("  ", " ")
            job = {"id": identifier, "merchantId": merchant, "audioKey": body.get("audioKey"),
                   "transcript": transcript, "language": language, "state": "ANSWERED",
                   "revision": 1, "committedOrderId": None, "createdAt": self._iso(), "updatedAt": self._iso(),
                   "queryResult": {"answerText": answer_text, "orderCount": len(orders),
                                   "orderNumbers": [o["orderNumber"] for o in orders]}}
            s["voiceJobs"].append(job)
            self._audit(s, merchant, "VOICE_QUERY_ANSWERED", identifier, {"orderCount": len(orders)})
            return self._present_answered_job(job)
        return action

    def _action_status_update(self, merchant: str, body: dict[str, Any], transcript: str, language: str,
                               status_update: dict[str, Any]) -> Callable[[dict[str, Any]], dict[str, Any]]:
        def action(s: dict[str, Any]) -> dict[str, Any]:
            identifier = f"vj_{s['sequences']['voiceJob']}"; s["sequences"]["voiceJob"] += 1
            order_number = str(status_update.get("orderNumberSpoken") or "").strip()
            spoken_name = str(status_update.get("customerSpokenName") or "").strip()
            order = None
            if order_number:
                order = next((o for o in s["orders"] if o["merchantId"] == merchant
                              and o["orderNumber"].casefold() == order_number.casefold()), None)
                require(order, 422, "ORDER_NOT_FOUND", f"No order matches '{order_number}'")
            else:
                customer = self._match_customer(s, merchant, spoken_name)
                require(customer, 422, "CUSTOMER_NOT_FOUND", f"No customer matches '{spoken_name}'")
                candidates = sorted((o for o in s["orders"] if o["merchantId"] == merchant
                                     and o["customerId"] == customer["id"] and o["status"] != "DELIVERED"),
                                    key=lambda o: o["createdAt"])
                require(candidates, 422, "ORDER_NOT_FOUND", f"No undelivered order for '{spoken_name}'")
                order = candidates[0]
            order["status"] = "DELIVERED"; order["deliveredAt"] = self._iso()
            self._audit(s, merchant, "ORDER_STATUS_UPDATED", order["id"], {"status": "DELIVERED"})
            job = {"id": identifier, "merchantId": merchant, "audioKey": body.get("audioKey"),
                   "transcript": transcript, "language": language, "state": "ANSWERED",
                   "revision": 1, "committedOrderId": order["id"], "createdAt": self._iso(), "updatedAt": self._iso(),
                   "queryResult": {"answerText": f"Order {order['orderNumber']} marked delivered.",
                                   "orderCount": 1, "orderNumbers": [order["orderNumber"]]}}
            s["voiceJobs"].append(job)
            return self._present_answered_job(job)
        return action

    def _match_customer(self, s: dict[str, Any], merchant: str, spoken_name: str) -> dict[str, Any] | None:
        needle = spoken_name.strip().casefold()
        if not needle: return None
        for customer in s["customers"]:
            if customer["merchantId"] != merchant: continue
            names = [customer["name"], *customer.get("aliases", [])]
            if any(needle == str(name).strip().casefold() for name in names): return customer
        return None

    def _present_answered_job(self, job: dict[str, Any]) -> dict[str, Any]:
        return {key: copy.deepcopy(job[key]) for key in
                ("id", "state", "revision", "transcript", "language", "committedOrderId",
                 "createdAt", "updatedAt", "queryResult")} | {"draft": None, "clarification": None}

    def voice_job(self, merchant: str, identifier: str) -> dict[str, Any]:
        def read(s: dict[str, Any]) -> dict[str, Any]:
            job = self._owned(s["voiceJobs"], identifier, merchant, "VOICE_JOB_NOT_FOUND")
            return self._present_answered_job(job) if job["state"] == "ANSWERED" else self._present_job(s, job)
        return self.store.read(read)

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
            if draft.get("customerId"):
                customer = self._owned(s["customers"], draft["customerId"], merchant, "CUSTOMER_NOT_FOUND")
            else:
                customer = self._create_customer_record(s, merchant, str(draft.get("customerSpokenName", "")).strip())
                draft["customerId"] = customer["id"]
            lines = [{"id": f"oli_{uuid.uuid4()}", "label": item["spokenName"],
                      "quantity": item["quantity"], "unit": item["unit"],
                      "unitPricePaise": item["quotedUnitPricePaise"],
                      "lineTotalPaise": item["quotedUnitPricePaise"] * item["quantity"]} for item in draft["items"]]
            total = sum(x["lineTotalPaise"] for x in lines); order_id = f"ord_{uuid.uuid4()}"
            order = {"id": order_id, "merchantId": merchant, "customerId": customer["id"], "voiceJobId": identifier,
                     "orderNumber": f"VL-{s['sequences']['order']}", "deliveryDate": draft["deliveryDate"], "currency": "INR",
                     "lines": lines, "totalPaise": total,
                     "collectionAmountPaise": draft.get("collectionAmountPaise"),
                     "status": "CONFIRMED", "createdAt": self._iso()}; s["sequences"]["order"] += 1
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

    def sync(self, merchant: str) -> dict[str, Any]:
        def read(s: dict[str, Any]) -> dict[str, Any]:
            self._merchant(s, merchant)
            customers = [self._public_customer(x) for x in s["customers"] if x["merchantId"] == merchant]
            orders = [copy.deepcopy(x) for x in s["orders"] if x["merchantId"] == merchant]
            invoices = [copy.deepcopy(x) for x in s["invoices"] if x["merchantId"] == merchant]
            ledger_by_customer: dict[str, Any] = {}
            for customer in customers:
                balance = 0
                entries = []
                for item in sorted((x for x in s["ledgerEntries"] if x["merchantId"] == merchant and x["customerId"] == customer["id"]), key=lambda x: x["occurredAt"]):
                    balance += item["debitPaise"] - item["creditPaise"]
                    entries.append({**copy.deepcopy(item), "balancePaise": balance})
                ledger_by_customer[customer["id"]] = {"balancePaise": balance, "entries": entries}
            return {
                "syncedAt": self._iso(),
                "merchant": copy.deepcopy(self._merchant(s, merchant)),
                "customers": customers,
                "orders": orders,
                "invoices": invoices,
                "ledgerByCustomer": ledger_by_customer,
            }
        return self.store.read(read)

    def _apply_extraction_defaults(self, draft: dict[str, Any], timezone_name: str) -> None:
        """Fill fields the merchant left unsaid instead of always asking.

        No delivery date spoken -> today. today/tomorrow/yesterday spoken ->
        resolved against the merchant's calendar day instead of asked again.
        No quantity spoken for an item -> 1. No unit spoken for an item -> piece.
        There is no product catalog: whatever product name is spoken becomes the
        order line directly, with no lookup or matching against anything.
        """
        delivery = draft.get("delivery_date") or {}
        spoken_date = delivery.get("evidence") or delivery.get("value")
        resolved = None
        if spoken_date:
            try:
                resolved = resolve_relative_date(str(spoken_date), timezone_name, now=self.now())
            except DomainError:
                resolved = None
        if resolved:
            delivery["value"] = resolved.isoformat()
        elif not delivery.get("value"):
            delivery["value"] = self.now().date().isoformat()
        draft["delivery_date"] = delivery
        for item in draft.get("items", []):
            if item.get("quantity") is None:
                item["quantity"] = 1
            if not item.get("unit") or self._unit(item.get("unit")) is None:
                item["unit"] = "piece"

    def _create_customer_record(self, s: dict[str, Any], merchant: str, spoken_name: str) -> dict[str, Any]:
        """A spoken name with no matching customer becomes a new customer at confirm time.

        There is no fixed merchant customer list; every distinct party a merchant
        speaks an order for becomes part of that merchant's own customer base over
        time, exactly as an SKU alias is learned the first time it is used.
        """
        require(spoken_name, 400, "INVALID_CLARIFICATION", "A customer name is required to create an order")
        identifier = f"cus_{s['sequences']['customer']}"; s["sequences"]["customer"] += 1
        customer = {"id": identifier, "merchantId": merchant, "name": spoken_name, "aliases": [spoken_name],
                    "phone": None, "address": None, "creditLimitPaise": 0}
        s["customers"].append(customer); self._audit(s, merchant, "CUSTOMER_CREATED", identifier, {"source": "voice_order"})
        return customer

    # There is no product catalog: a spoken product name is the order line's identity.
    # Explicit spoken prices and collection instructions survive review unchanged.
    @staticmethod
    def _provider_proposal(draft: dict[str, Any]) -> dict[str, Any]:
        customer, delivery = draft["customer"], draft["delivery_date"]
        query = draft.get("query") or {}
        status_update = draft.get("status_update") or {}
        return {"customerId": customer.get("candidate_id"), "customerSpokenName": customer.get("spoken_name"),
                "deliveryDate": delivery.get("value"),
                "items": [{"spokenName": x.get("spoken_name"),
                           "quantity": x.get("quantity"), "unit": Service._unit(x.get("unit")), "confidence": x.get("confidence"),
                           "quotedUnitPricePaise": round(x["quoted_unit_price"] * 100) if x.get("quoted_unit_price") is not None else None,
                           "evidence": x.get("evidence")} for x in draft.get("items", [])],
                "mentionedPreviousBalancePaise": round(draft["mentioned_previous_balance"] * 100) if draft.get("mentioned_previous_balance") is not None else None,
                "collectionAmountPaise": round(draft["collection_amount"] * 100) if draft.get("collection_amount") is not None else None,
                "evidence": {"customer": customer.get("evidence"), "collection": draft.get("collection_evidence", "")},
                "warnings": list(draft.get("warnings", [])),
                "query": {"customerSpokenName": query.get("customer_spoken_name"), "statusFilter": query.get("status_filter")},
                "statusUpdate": {"customerSpokenName": status_update.get("customer_spoken_name"),
                                  "orderNumberSpoken": status_update.get("order_number_spoken"),
                                  "newStatus": status_update.get("new_status")}}

    def _validate(self, s: dict[str, Any], merchant: str, draft: dict[str, Any]) -> list[dict[str, Any]]:
        errors = []
        has_customer_id = any(x["id"] == draft.get("customerId") and x["merchantId"] == merchant for x in s["customers"])
        if not draft.get("customerId") and not str(draft.get("customerSpokenName", "")).strip():
            errors.append({"code": "MISSING_CUSTOMER", "fieldPath": "customerId"})
        elif draft.get("customerId") and not has_customer_id:
            errors.append({"code": "AMBIGUOUS_CUSTOMER", "fieldPath": "customerId"})
        if not draft.get("deliveryDate"): errors.append({"code": "MISSING_DELIVERY_DATE", "fieldPath": "deliveryDate"})
        if not draft.get("items"): errors.append({"code": "MISSING_ITEMS", "fieldPath": "items"})
        for index, item in enumerate(draft.get("items", [])):
            if not str(item.get("spokenName", "")).strip(): errors.append({"code": "MISSING_PRODUCT_NAME", "fieldPath": f"items.{index}.spokenName"})
            if not isinstance(item.get("quantity"), (int, float)) or item["quantity"] <= 0: errors.append({"code": "MISSING_QUANTITY", "fieldPath": f"items.{index}.quantity"})
            if not item.get("unit"): errors.append({"code": "MISSING_UNIT", "fieldPath": f"items.{index}.unit"})
            quoted = item.get("quotedUnitPricePaise")
            if quoted is None: errors.append({"code": "MISSING_PRICE", "fieldPath": f"items.{index}.quotedUnitPricePaise"})
            elif isinstance(quoted, bool) or not isinstance(quoted, int) or quoted < 0: errors.append({"code": "INVALID_QUOTED_PRICE", "fieldPath": f"items.{index}.quotedUnitPricePaise"})
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
        if error["code"] == "MISSING_CUSTOMER": return {"fieldPath": path, "code": error["code"], "question": "Yeh order kis customer ke liye hai?", "options": []}
        if error["code"] == "AMBIGUOUS_CUSTOMER": return {"fieldPath": path, "code": error["code"], "question": f"‘{draft.get('customerSpokenName', 'customer')}’ kaun sa customer hai?", "options": [{"value": x["id"], "label": x["name"]} for x in s["customers"] if x["merchantId"] == merchant]}
        if error["code"] == "MISSING_DELIVERY_DATE": return {"fieldPath": path, "code": error["code"], "question": "Delivery date kya hai? (YYYY-MM-DD)", "options": []}
        match = re.match(r"items\.(\d+)\.", path)
        if match:
            item = draft["items"][int(match.group(1))]; label = item.get("spokenName", "Item")
            if error["code"] == "MISSING_PRODUCT_NAME": return {"fieldPath": path, "code": error["code"], "question": "Yeh item kya hai?", "options": []}
            if error["code"] == "MISSING_UNIT": return {"fieldPath": path, "code": error["code"], "question": f"{label} ki {item.get('quantity')} case ya pieces?", "options": [{"value": "case", "label": "Case / peti"}, {"value": "piece", "label": "Piece / bottle"}]}
            if error["code"] == "MISSING_QUANTITY": return {"fieldPath": path, "code": error["code"], "question": f"{label} kitna bhejna hai?", "options": []}
            if error["code"] == "MISSING_PRICE": return {"fieldPath": path, "code": error["code"], "question": f"{label} ka rate kya hai? (per {item.get('unit', 'piece')})", "options": []}
        if error["code"] == "BALANCE_MISMATCH": return {"fieldPath": path, "code": error["code"], "question": f"System balance ₹{error['systemBalancePaise']/100:,.2f} hai. Use karein?", "options": [{"value": error["systemBalancePaise"], "label": "Use system balance"}]}
        return {"fieldPath": path, "code": error["code"], "question": "Missing information provide karein.", "options": []}

    def _apply_answer(self, s: dict[str, Any], merchant: str, draft: dict[str, Any], clarification: dict[str, Any], answer: Any) -> None:
        parts = clarification["fieldPath"].split(".")
        if parts[0] == "customerId" and clarification["code"] == "MISSING_CUSTOMER":
            require(str(answer).strip(), 400, "INVALID_CLARIFICATION", "A customer name is required")
            draft["customerSpokenName"] = str(answer).strip()
        elif parts[0] == "customerId": self._owned(s["customers"], answer, merchant, "INVALID_CLARIFICATION"); draft["customerId"] = answer
        elif parts[0] == "deliveryDate":
            try: draft["deliveryDate"] = date.fromisoformat(str(answer)).isoformat()
            except ValueError: raise ApiError(400, "INVALID_CLARIFICATION", "Delivery date must use YYYY-MM-DD") from None
        elif parts[0] == "items":
            index = int(parts[1]); item = draft["items"][index]
            if parts[2] == "unit": require(answer in {"case", "piece", "kg", "pouch"}, 400, "INVALID_CLARIFICATION", "Unit is invalid"); item["unit"] = answer
            elif parts[2] == "quantity": require(isinstance(answer, (int, float)) and answer > 0, 400, "INVALID_CLARIFICATION", "Quantity must be positive"); item["quantity"] = answer
            elif parts[2] == "spokenName": require(str(answer).strip(), 400, "INVALID_CLARIFICATION", "A product name is required"); item["spokenName"] = str(answer).strip()
            elif parts[2] == "quotedUnitPricePaise":
                require(isinstance(answer, (int, float)) and not isinstance(answer, bool) and answer >= 0, 400, "INVALID_CLARIFICATION", "Price must be a non-negative number")
                item["quotedUnitPricePaise"] = round(answer)
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
    def _safe_answer(answer: Any) -> Any: return answer[:100] if isinstance(answer, str) else answer
    def _iso(self) -> str: return self.now().isoformat()
    def _audit(self, s: dict[str, Any], merchant: str, action: str, entity: str, metadata: dict[str, Any] | None = None) -> None:
        s["audit"].append({"id": f"aud_{uuid.uuid4()}", "merchantId": merchant, "action": action, "entityId": entity, "metadata": metadata or {}, "occurredAt": self._iso()})
