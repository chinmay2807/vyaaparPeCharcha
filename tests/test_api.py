from __future__ import annotations

import base64
import copy
import unittest
from datetime import datetime, timezone
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from vyapaar.api import create_app
from vyapaar.providers import OfflineSarvamProvider
from vyapaar.service import Service
from vyapaar.store import JsonStore, seed_state


class ApiTests(unittest.TestCase):
    def setUp(self):
        self.store = JsonStore(initial=seed_state())
        service = Service(
            self.store, provider=OfflineSarvamProvider(),
            now=lambda: datetime(2026, 9, 5, 10, tzinfo=timezone.utc),
        )
        self.client = TestClient(create_app(service))

    def request(self, path, method="GET", body=None, key=None, merchant="mer_demo"):
        headers = {"X-Merchant-Id": merchant}
        if key:
            headers["Idempotency-Key"] = key
        response = self.client.request(method, path, json=body, headers=headers)
        payload = response.content if response.headers.get("content-type", "").startswith(
            ("application/pdf", "audio/")
        ) else response.json()
        return response.status_code, response.headers, payload

    def test_openapi_health_catalog_and_request_id(self):
        status, headers, health = self.request("/health")
        self.assertEqual((status, health["status"]), (200, "ok"))
        self.assertTrue(headers["X-Request-Id"])
        self.assertEqual(self.client.get("/openapi.json").status_code, 200)
        _, _, catalog = self.request("/v1/skus")
        self.assertEqual(len(catalog["skus"]), 30)
        _, _, customer = self.request("/v1/customers?query=ramesh")
        self.assertEqual(len(customer["customers"]), 1)
        self.assertNotIn("phone", customer["customers"][0])

    def test_mutation_idempotency_is_atomic_and_rejects_conflicts(self):
        status, _, body = self.request("/v1/customers", "POST", {"name": "A"})
        self.assertEqual((status, body["error"]["code"]), (400, "IDEMPOTENCY_KEY_REQUIRED"))
        first = self.request("/v1/customers", "POST", {"name": "A"}, "customer-001")
        replay = self.request("/v1/customers", "POST", {"name": "A"}, "customer-001")
        self.assertEqual(first[2], replay[2])
        self.assertEqual(len(self.store.snapshot()["customers"]), 3)
        conflict = self.request("/v1/customers", "POST", {"name": "B"}, "customer-001")
        self.assertEqual((conflict[0], conflict[2]["error"]["code"]), (409, "IDEMPOTENCY_CONFLICT"))

    def test_voice_review_confirm_pdf_audio_ledger_and_no_preconfirm_mutation(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 6 peti Sprite aur 4 Coke bhejna. last ₹12,500 pending"},
            "voicejob-001",
        )[2]
        self.assertEqual(submitted["clarification"]["code"], "MISSING_UNIT")
        state = self.store.snapshot()
        self.assertEqual(
            (len(state["orders"]), len(state["invoices"]), len(state["inventoryMovements"])),
            (0, 0, 0),
        )
        stale = self.request(
            f"/v1/voice-jobs/{submitted['id']}/clarifications", "POST",
            {"revision": 99, "answer": "case"}, "clarify-stale",
        )[2]
        self.assertEqual(stale["error"]["code"], "STALE_DRAFT")
        clarified = self.request(
            f"/v1/voice-jobs/{submitted['id']}/clarifications", "POST",
            {"revision": 1, "answer": "case"}, "clarify-good",
        )[2]
        confirmation = {"revision": 2, "spokenConfirmation": True}
        confirmed = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            confirmation, "confirm-good",
        )[2]
        state = self.store.snapshot()
        self.assertEqual(
            (len(state["orders"]), len(state["invoices"]), len(state["inventoryMovements"])),
            (1, 1, 2),
        )
        self.assertTrue(base64.b64decode(
            confirmed["voiceConfirmation"]["audioBase64"]
        ).startswith(b"RIFF"))
        replay = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            confirmation, "confirm-good",
        )[2]
        self.assertEqual(replay["order"]["id"], confirmed["order"]["id"])
        invoice = self.request(f"/v1/invoices/{confirmed['invoice']['id']}/pdf")[2]
        audio = self.request(
            f"/v1/orders/{confirmed['order']['id']}/confirmation-audio"
        )[2]
        self.assertTrue(invoice.startswith(b"%PDF-1.4"))
        self.assertTrue(audio.startswith(b"RIFF"))
        ledger = self.request("/v1/customers/cus_ramesh/ledger")[2]
        self.assertEqual(ledger["balancePaise"], 1_250_000 + confirmed["order"]["totalPaise"])

    def test_failed_confirmation_rolls_back_all_effects(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 1 peti Sprite bhejna"}, "voice-rollback",
        )[2]
        self.store.transaction(lambda state: next(
            item for item in state["skus"] if item["id"] == "sku_sprite_24x250"
        ).update({"stockBaseUnits": 0}))
        before = self.store.snapshot()
        failed = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            {"revision": 1}, "confirm-rollback",
        )
        self.assertEqual(failed[2]["error"]["code"], "INSUFFICIENT_STOCK")
        after = self.store.snapshot()
        for collection in ("orders", "invoices", "ledgerEntries", "inventoryMovements", "outboxEvents"):
            self.assertEqual(after[collection], before[collection])

    def test_spoken_quote_and_collection_are_committed(self):
        class SpokenMoneyProvider(OfflineSarvamProvider):
            def extract_order(self, transcript, merchant_context):
                draft = super().extract_order(transcript, merchant_context)
                draft["items"][0]["quoted_unit_price"] = 2500
                draft["items"][0]["unit"] = "crate"
                draft["collection_amount"] = 10000
                draft["collection_evidence"] = "collect INR 10,000"
                return draft

        self.client.app.state.service.provider = SpokenMoneyProvider()
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 3 case Sprite 2500 each; collect 10000"},
            "voice-spoken-money",
        )[2]
        self.assertEqual(submitted["draft"]["items"][0]["quotedUnitPricePaise"], 250000)
        self.assertEqual(submitted["draft"]["collectionAmountPaise"], 1000000)
        confirmed = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            {"revision": submitted["revision"]}, "confirm-spoken-money",
        )[2]
        self.assertEqual(confirmed["order"]["totalPaise"], 750000)
        self.assertEqual(confirmed["order"]["collectionAmountPaise"], 1000000)
        self.assertEqual(confirmed["order"]["lines"][0]["priceSource"], "SPOKEN_QUOTE")
        self.assertEqual(confirmed["order"]["lines"][0]["unit"], "case")
        self.assertEqual(confirmed["order"]["lines"][0]["baseUnits"], 72)
        entries = [entry for entry in self.store.snapshot()["ledgerEntries"]
                   if entry.get("orderId") == confirmed["order"]["id"]]
        self.assertEqual([entry["type"] for entry in entries], ["SALES_INVOICE", "PAYMENT_COLLECTION"])
        self.assertEqual(confirmed["customerBalancePaise"], 1000000)

    def test_edit_creates_immutable_revision(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 1 peti Sprite bhejna"}, "voice-edit-01",
        )[2]
        edited = self.request(
            f"/v1/voice-jobs/{submitted['id']}/draft", "PATCH",
            {"revision": 1, "deliveryDate": "2026-09-08"}, "edit-draft-01",
        )[2]
        self.assertEqual(edited["revision"], 2)
        self.assertEqual(
            [item["deliveryDate"] for item in self.store.snapshot()["drafts"]],
            ["2026-09-06", "2026-09-08"],
        )

    def test_missing_delivery_date_can_be_clarified(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko 1 peti Sprite bhejna"}, "voice-date-01",
        )[2]
        self.assertEqual(submitted["clarification"]["code"], "MISSING_DELIVERY_DATE")
        clarified = self.request(
            f"/v1/voice-jobs/{submitted['id']}/clarifications", "POST",
            {"revision": 1, "answer": "2026-09-05"}, "clarify-date-01",
        )[2]
        self.assertEqual(clarified["state"], "READY_FOR_REVIEW")
        self.assertEqual(clarified["draft"]["deliveryDate"], "2026-09-05")

    def test_android_multipart_flow_returns_reachable_pdf_and_audio(self):
        headers = {"Idempotency-Key": "android-voice-001", "X-Merchant-Id": "mer_demo"}
        recording = b"TRANSCRIPT: Ramesh ko kal 1 peti Sprite bhejna"
        submitted = self.client.post(
            "/v1/mobile/voice-jobs", headers=headers,
            files={"audio": ("order.m4a", recording, "audio/mp4")},
            data={"language_hint": "hi-IN"},
        )
        self.assertEqual(submitted.status_code, 202)
        job = submitted.json()
        self.assertEqual(job["state"], "READY_FOR_REVIEW")
        confirmed = self.client.post(
            f"/v1/mobile/voice-jobs/{job['id']}/confirm",
            headers={"Idempotency-Key": "android-confirm-001", "X-Merchant-Id": "mer_demo"},
            json={"revision": job["revision"]},
        )
        self.assertEqual(confirmed.status_code, 200)
        artifacts = confirmed.json()["artifacts"]
        pdf_path = urlsplit(artifacts["invoice"]["url"]).path
        audio_path = urlsplit(artifacts["audio"]["url"]).path
        pdf = self.client.get(pdf_path)
        audio = self.client.get(audio_path)
        self.assertEqual(pdf.headers["content-type"], "application/pdf")
        self.assertTrue(pdf.content.startswith(b"%PDF"))
        self.assertTrue(audio.headers["content-type"].startswith("audio/"))
        self.assertTrue(audio.content.startswith(b"RIFF"))

    def test_reconciliation_review_apply_and_replay(self):
        body = {"documentName": "supplier.pdf", "invoiceNumber": "SUP-9", "items": [
            {"spokenName": "Sprite case", "quantity": 2, "unit": "case", "unitCostPaise": 60000}
        ]}
        created = self.request("/v1/reconciliation-documents", "POST", body, "recon-create")[2]
        self.assertEqual(created["state"], "REVIEW_REQUIRED")
        before = self.store.snapshot()["skus"][0]["stockBaseUnits"]
        applied = self.request(
            f"/v1/reconciliation-documents/{created['id']}/apply", "POST",
            {"revision": 1}, "recon-apply",
        )[2]
        self.assertEqual(applied["state"], "APPLIED")
        self.assertEqual(self.store.snapshot()["skus"][0]["stockBaseUnits"], before + 48)

    def test_merchant_isolation(self):
        status, _, body = self.request(
            "/v1/customers/cus_ramesh/ledger", merchant="mer_other"
        )
        self.assertEqual((status, body["error"]["code"]), (404, "CUSTOMER_NOT_FOUND"))


if __name__ == "__main__":
    unittest.main()
