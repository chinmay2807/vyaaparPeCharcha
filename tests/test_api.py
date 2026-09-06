from __future__ import annotations

import base64
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

    def test_openapi_health_and_request_id(self):
        status, headers, health = self.request("/health")
        self.assertEqual((status, health["status"]), (200, "ok"))
        self.assertTrue(headers["X-Request-Id"])
        self.assertEqual(self.client.get("/openapi.json").status_code, 200)
        _, _, customer = self.request("/v1/customers?query=ramesh")
        self.assertEqual(len(customer["customers"]), 1)
        self.assertNotIn("phone", customer["customers"][0])

    def test_mobile_sync_returns_full_merchant_snapshot(self):
        status, _, body = self.request("/v1/mobile/sync")
        self.assertEqual(status, 200)
        self.assertEqual(body["merchant"]["id"], "mer_demo")
        self.assertEqual(len(body["customers"]), 2)
        self.assertNotIn("phone", body["customers"][0])
        ramesh = next(c for c in body["customers"] if c["id"] == "cus_ramesh")
        ledger = body["ledgerByCustomer"][ramesh["id"]]
        self.assertEqual(ledger["balancePaise"], 1_250_000)
        self.assertEqual(len(ledger["entries"]), 1)
        other_merchant = self.request("/v1/mobile/sync", merchant="mer_other")
        self.assertEqual(other_merchant[2]["error"]["code"], "MERCHANT_NOT_FOUND")

    def test_sync_lists_unconfirmed_voice_jobs_as_pending(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 2 case Sprite @400 bhejna"}, "voice-pending-01",
        )[2]
        self.assertEqual(submitted["state"], "READY_FOR_REVIEW")
        _, _, synced = self.request("/v1/mobile/sync")
        pending_ids = [job["id"] for job in synced["pendingVoiceJobs"]]
        self.assertIn(submitted["id"], pending_ids)
        confirmed = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            {"revision": submitted["revision"], "spokenConfirmation": False}, "confirm-pending-01",
        )[2]
        self.assertTrue(confirmed["order"]["id"])
        _, _, synced_after = self.request("/v1/mobile/sync")
        self.assertNotIn(submitted["id"], [job["id"] for job in synced_after["pendingVoiceJobs"]])

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
            {"transcript": "Ramesh ko kal 6 peti Sprite @500 aur 4 case Coke @600 bhejna. last ₹12,500 pending"},
            "voicejob-001",
        )[2]
        self.assertIsNone(submitted["clarification"])
        self.assertEqual(submitted["state"], "READY_FOR_REVIEW")
        state = self.store.snapshot()
        self.assertEqual((len(state["orders"]), len(state["invoices"])), (0, 0))
        stale = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            {"revision": 99, "spokenConfirmation": True}, "confirm-stale",
        )[2]
        self.assertEqual(stale["error"]["code"], "STALE_DRAFT")
        confirmation = {"revision": 1, "spokenConfirmation": True}
        confirmed = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            confirmation, "confirm-good",
        )[2]
        state = self.store.snapshot()
        self.assertEqual((len(state["orders"]), len(state["invoices"])), (1, 1))
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
            {"transcript": "Ramesh ko kal 1 peti Sprite @500 bhejna"}, "voice-rollback",
        )[2]
        before = self.store.snapshot()
        failed = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            {"revision": 99, "spokenConfirmation": True}, "confirm-rollback",
        )
        self.assertEqual(failed[2]["error"]["code"], "STALE_DRAFT")
        after = self.store.snapshot()
        for collection in ("orders", "invoices", "ledgerEntries", "outboxEvents"):
            self.assertEqual(after[collection], before[collection])

    def test_spoken_quote_and_collection_are_committed(self):
        class SpokenMoneyProvider(OfflineSarvamProvider):
            def extract_order(self, transcript, merchant_context):
                draft = super().extract_order(transcript, merchant_context)
                draft["items"][0]["quoted_unit_price"] = 2500
                draft["items"][0]["unit"] = "case"
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
        self.assertEqual(confirmed["order"]["lines"][0]["unit"], "case")
        entries = [entry for entry in self.store.snapshot()["ledgerEntries"]
                   if entry.get("orderId") == confirmed["order"]["id"]]
        self.assertEqual([entry["type"] for entry in entries], ["SALES_INVOICE", "PAYMENT_COLLECTION"])
        self.assertEqual(confirmed["customerBalancePaise"], 1000000)

    def test_restated_balance_is_not_recorded_as_a_new_collection(self):
        class RestatedBalanceProvider(OfflineSarvamProvider):
            def extract_order(self, transcript, merchant_context):
                draft = super().extract_order(transcript, merchant_context)
                draft["items"][0]["quoted_unit_price"] = 400
                draft["mentioned_previous_balance"] = 20000
                draft["collection_amount"] = 20000
                draft["collection_evidence"] = "twenty thousand rupees for the previous one to him"
                return draft

        self.client.app.state.service.provider = RestatedBalanceProvider()
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Puneet ko kal 10 Sprite boxes @400 bhejna; uska bees hazaar pending hai"},
            "voice-restated-balance",
        )[2]
        self.assertIsNone(submitted["draft"]["collectionAmountPaise"])
        self.assertEqual(submitted["draft"]["mentionedPreviousBalancePaise"], 2000000)
        confirmed = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            {"revision": submitted["revision"]}, "confirm-restated-balance",
        )[2]
        self.assertIsNone(confirmed["order"]["collectionAmountPaise"])
        entries = [entry for entry in self.store.snapshot()["ledgerEntries"]
                   if entry.get("orderId") == confirmed["order"]["id"]]
        self.assertEqual([entry["type"] for entry in entries], ["SALES_INVOICE"])

    def test_edit_creates_immutable_revision(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 1 peti Sprite @500 bhejna"}, "voice-edit-01",
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

    def test_missing_delivery_date_defaults_to_today_without_asking(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko 1 peti Sprite @500 bhejna"}, "voice-date-01",
        )[2]
        self.assertIsNone(submitted["clarification"])
        self.assertEqual(submitted["draft"]["deliveryDate"], "2026-09-05")

    def test_relative_delivery_date_is_resolved_without_asking(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 1 peti Sprite @500 bhejna"}, "voice-date-02",
        )[2]
        self.assertIsNone(submitted["clarification"])
        self.assertEqual(submitted["draft"]["deliveryDate"], "2026-09-06")

    def test_missing_item_quantity_defaults_to_one(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko Sprite case @500 bhejna"}, "voice-qty-01",
        )[2]
        self.assertEqual(submitted["draft"]["items"][0]["quantity"], 1)

    def test_missing_unit_defaults_to_piece(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 4 Coke @15 bhejna"}, "voice-unit-01",
        )[2]
        self.assertIsNone(submitted["clarification"])
        self.assertEqual(submitted["draft"]["items"][0]["unit"], "piece")

    def test_missing_price_is_the_only_thing_still_asked_for_an_item(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 4 case Coke bhejna"}, "voice-price-01",
        )[2]
        self.assertEqual(submitted["clarification"]["code"], "MISSING_PRICE")
        answered = self.request(
            f"/v1/voice-jobs/{submitted['id']}/clarifications", "POST",
            {"revision": 1, "answer": 60000}, "voice-price-01-answer",
        )[2]
        self.assertIsNone(answered["clarification"])
        self.assertEqual(answered["draft"]["items"][0]["quotedUnitPricePaise"], 60000)

    def test_any_spoken_product_name_becomes_the_order_line_with_no_catalog(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 5 piece Random Unknown Gadget @200 bhejna"},
            "voice-nocatalog-01",
        )[2]
        self.assertIsNone(submitted["clarification"])
        item = submitted["draft"]["items"][0]
        self.assertEqual(item["spokenName"], "Random Unknown Gadget")
        self.assertNotIn("skuId", item)
        confirmed = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            {"revision": 1, "spokenConfirmation": False}, "confirm-nocatalog-01",
        )[2]
        line = confirmed["order"]["lines"][0]
        self.assertEqual(line["label"], "Random Unknown Gadget")
        self.assertEqual(line["quantity"], 5)
        self.assertEqual(line["unitPricePaise"], 20000)
        self.assertEqual(line["lineTotalPaise"], 100000)

    def test_unmatched_customer_becomes_a_new_customer_only_at_confirm(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Suresh ko kal 1 peti Sprite @500 bhejna"}, "voice-newcust-01",
        )[2]
        self.assertIsNone(submitted["clarification"])
        self.assertEqual(submitted["state"], "READY_FOR_REVIEW")
        self.assertIsNone(submitted["draft"]["customerId"])
        before = self.store.snapshot()
        self.assertEqual(len(before["customers"]), 2)
        confirmed = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            {"revision": 1, "spokenConfirmation": False}, "confirm-newcust-01",
        )[2]
        after = self.store.snapshot()
        self.assertEqual(len(after["customers"]), 3)
        new_customer = next(c for c in after["customers"] if c["id"] == confirmed["order"]["customerId"])
        self.assertEqual(new_customer["name"], "Suresh")

    def test_query_orders_answers_without_a_draft_or_clarification(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 3 case Sprite @500 bhejna"}, "voice-query-order-01",
        )[2]
        self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            {"revision": submitted["revision"], "spokenConfirmation": False}, "confirm-query-order-01",
        )
        answered = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "How many pending orders does Ramesh have?"}, "voice-query-01",
        )[2]
        self.assertEqual(answered["state"], "ANSWERED")
        self.assertIsNone(answered["draft"])
        self.assertIsNone(answered["clarification"])
        self.assertEqual(answered["queryResult"]["orderCount"], 1)
        self.assertIn("voiceAnswer", answered)

    def test_update_order_status_marks_the_oldest_undelivered_order_delivered(self):
        submitted = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Ramesh ko kal 3 case Sprite @500 bhejna"}, "voice-status-order-01",
        )[2]
        confirmed = self.request(
            f"/v1/voice-jobs/{submitted['id']}/confirm", "POST",
            {"revision": submitted["revision"], "spokenConfirmation": False}, "confirm-status-order-01",
        )[2]
        answered = self.request(
            "/v1/voice-jobs", "POST",
            {"transcript": "Mark Ramesh order delivered"}, "voice-status-01",
        )[2]
        self.assertEqual(answered["state"], "ANSWERED")
        self.assertEqual(answered["committedOrderId"], confirmed["order"]["id"])
        after = self.store.snapshot()
        order = next(o for o in after["orders"] if o["id"] == confirmed["order"]["id"])
        self.assertEqual(order["status"], "DELIVERED")

    def test_android_multipart_flow_returns_reachable_pdf_and_audio(self):
        headers = {"Idempotency-Key": "android-voice-001", "X-Merchant-Id": "mer_demo"}
        recording = b"TRANSCRIPT: Ramesh ko kal 1 peti Sprite @500 bhejna"
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

    def test_merchant_isolation(self):
        status, _, body = self.request(
            "/v1/customers/cus_ramesh/ledger", merchant="mer_other"
        )
        self.assertEqual((status, body["error"]["code"]), (404, "CUSTOMER_NOT_FOUND"))


if __name__ == "__main__":
    unittest.main()
