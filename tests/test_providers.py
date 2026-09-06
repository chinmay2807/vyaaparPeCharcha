from __future__ import annotations

import io
import json
import os
import unittest
import urllib.error
import wave
from unittest.mock import patch

from vyapaar.providers import (
    AzureOpenAIConfig,
    AzureOrderProvider,
    ORDER_DRAFT_SCHEMA,
    STT_PATH,
    TTS_PATH,
    LiveSarvamProvider,
    OfflineSarvamProvider,
    ProviderConfig,
    ProviderError,
    create_provider,
    validate_schema,
)


CONTEXT = {
    "reference_date": "2026-09-05",
    "customers": [{"id": "cus_ramesh", "name": "Ramesh", "aliases": ["Ramesh ji"]}],
}


class OfflineProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.provider = OfflineSarvamProvider()

    def test_offline_is_default_and_requires_no_key(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            self.assertIsInstance(create_provider(), OfflineSarvamProvider)

    def test_transcription_fixture_is_deterministic(self) -> None:
        first = self.provider.transcribe(b"not real audio")
        second = self.provider.transcribe(b"not real audio")
        self.assertEqual(first, second)
        self.assertIn("Ramesh", first["text"])
        self.assertEqual(first["language"], "hi-IN")

    def test_plain_text_fixture_can_supply_transcript(self) -> None:
        result = self.provider.transcribe(b"TRANSCRIPT: Suresh ko 2 case Sprite bhejna")
        self.assertEqual(result["text"], "Suresh ko 2 case Sprite bhejna")

    def test_extraction_has_no_catalog_and_flags_missing_unit(self) -> None:
        draft = self.provider.extract_order(
            "Ramesh ko kal ke liye 6 peti Sprite, 4 Coke aur 20 bottle Limca bhejna. "
            "Uska last Rs 12,500 pending hai.",
            CONTEXT,
        )
        self.assertEqual(draft["customer"]["candidate_id"], "cus_ramesh")
        self.assertEqual(draft["delivery_date"]["value"], "2026-09-06")
        self.assertEqual([item["spoken_name"] for item in draft["items"]], ["Sprite", "Coke", "Limca"])
        self.assertNotIn("candidate_sku_id", draft["items"][0])
        self.assertEqual(draft["mentioned_previous_balance"], 12_500)
        validate_schema(draft, ORDER_DRAFT_SCHEMA)

    def test_extraction_parses_any_spoken_product_with_no_catalog_lookup(self) -> None:
        draft = self.provider.extract_order(
            "Suresh ko kal 5 piece Random Unknown Gadget bhejna", CONTEXT
        )
        self.assertEqual(len(draft["items"]), 1)
        self.assertEqual(draft["items"][0]["spoken_name"], "Random Unknown Gadget")
        self.assertEqual(draft["items"][0]["quantity"], 5)
        self.assertEqual(draft["items"][0]["unit"], "piece")

    def test_offline_confirmation_is_valid_wav(self) -> None:
        result = self.provider.synthesize_confirmation("Order ban gaya")
        self.assertEqual(result["content_type"], "audio/wav")
        with wave.open(io.BytesIO(result["audio"]), "rb") as audio:
            self.assertEqual(audio.getnchannels(), 1)
            self.assertGreater(audio.getnframes(), 0)


class SchemaTests(unittest.TestCase):
    def test_schema_rejects_extra_properties(self) -> None:
        invalid = OfflineSarvamProvider().extract_order("Ramesh ko kal 2 case Sprite", CONTEXT)
        invalid["llm_guess"] = True
        with self.assertRaisesRegex(ProviderError, "unexpected"):
            validate_schema(invalid, ORDER_DRAFT_SCHEMA)

    def test_schema_rejects_boolean_as_number(self) -> None:
        invalid = OfflineSarvamProvider().extract_order("Ramesh ko kal 2 case Sprite", CONTEXT)
        invalid["customer"]["confidence"] = True
        with self.assertRaisesRegex(ProviderError, "invalid type"):
            validate_schema(invalid, ORDER_DRAFT_SCHEMA)


class LiveProviderTests(unittest.TestCase):
    def setUp(self) -> None:
        self.config = ProviderConfig(
            api_key="server-secret",
            base_url="https://sarvam.test",
            timeout_seconds=3,
            max_retries=2,
        )

    def test_live_mode_requires_server_key(self) -> None:
        with patch.dict(os.environ, {"SARVAM_LIVE": "1"}, clear=True):
            with self.assertRaisesRegex(ProviderError, "SARVAM_API_KEY"):
                create_provider()

    def test_stt_uses_multipart_current_endpoint_and_server_header(self) -> None:
        requests = []

        def transport(request, timeout):
            requests.append((request, timeout))
            return json.dumps({"transcript": "Ramesh ko 2 case Sprite", "language_code": "hi-IN"}).encode()

        provider = LiveSarvamProvider(self.config, transport=transport)
        result = provider.transcribe(b"audio-bytes", filename="order.webm", content_type="audio/webm")
        request, timeout = requests[0]
        self.assertEqual(request.full_url, f"https://sarvam.test{STT_PATH}")
        self.assertEqual(request.get_header("Api-subscription-key"), "server-secret")
        self.assertIn("multipart/form-data", request.get_header("Content-type"))
        self.assertIn(b'saaras:v3', request.data)
        self.assertIn(b'audio-bytes', request.data)
        self.assertEqual(timeout, 3)
        self.assertEqual(result["text"], "Ramesh ko 2 case Sprite")

    def test_extraction_sends_strict_schema_and_validates_result(self) -> None:
        expected = OfflineSarvamProvider().extract_order(
            "Ramesh ko kal 2 case Sprite bhejna", CONTEXT
        )
        seen = {}

        def transport(request, timeout):
            del timeout
            seen.update(json.loads(request.data))
            response = {"choices": [{"message": {"content": json.dumps(expected)}}]}
            return json.dumps(response).encode()

        provider = LiveSarvamProvider(self.config, transport=transport)
        self.assertEqual(provider.extract_order("private transcript", CONTEXT), expected)
        self.assertEqual(seen["model"], "sarvam-105b")
        self.assertEqual(seen["temperature"], 0)
        self.assertIsNone(seen["reasoning_effort"])
        self.assertTrue(seen["response_format"]["json_schema"]["strict"])
        self.assertEqual(seen["response_format"]["json_schema"]["schema"], ORDER_DRAFT_SCHEMA)

    def test_tts_decodes_audio_from_current_endpoint(self) -> None:
        captured = {}

        def transport(request, timeout):
            del timeout
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data)
            return json.dumps({"audios": ["AAEC"]}).encode()

        result = LiveSarvamProvider(self.config, transport=transport).synthesize_confirmation(
            "Order ban gaya"
        )
        self.assertEqual(captured["url"], f"https://sarvam.test{TTS_PATH}")
        self.assertEqual(captured["body"]["model"], "bulbul:v3")
        self.assertEqual(captured["body"]["text"], "Order ban gaya")
        self.assertEqual(captured["body"]["language_code"], "hi-IN")
        self.assertEqual(captured["body"]["speaker"], "shubh")
        self.assertNotIn("inputs", captured["body"])
        self.assertEqual(result["audio"], b"\x00\x01\x02")

    def test_retries_transient_errors_with_bounded_backoff(self) -> None:
        attempts = 0
        sleeps = []

        def transport(request, timeout):
            nonlocal attempts
            del request, timeout
            attempts += 1
            if attempts < 3:
                raise urllib.error.URLError("transient")
            return json.dumps({"transcript": "ok transcript", "language_code": "hi-IN"}).encode()

        provider = LiveSarvamProvider(self.config, transport=transport, sleep=sleeps.append)
        self.assertEqual(provider.transcribe(b"audio")["text"], "ok transcript")
        self.assertEqual(attempts, 3)
        self.assertEqual(sleeps, [0.25, 0.5])

    def test_errors_do_not_expose_secret_or_payload(self) -> None:
        def transport(request, timeout):
            del request, timeout
            raise urllib.error.URLError("private transcript server-secret")

        provider = LiveSarvamProvider(self.config, transport=transport, sleep=lambda _: None)
        with self.assertRaises(ProviderError) as caught:
            provider.transcribe(b"private audio")
        message = str(caught.exception)
        self.assertNotIn("server-secret", message)
        self.assertNotIn("private", message)


class AzureOrderProviderTests(unittest.TestCase):
    def test_uses_azure_deployment_and_preserves_spoken_money(self) -> None:
        config = AzureOpenAIConfig(
            endpoint="https://azure.test", api_key="azure-secret",
            deployment="gpt-4.1-mini", api_version="2024-10-21",
            timeout_seconds=4, max_retries=0,
        )
        expected = OfflineSarvamProvider().extract_order(
            "Ramesh ko kal 3 case Sprite bhejna", CONTEXT
        )
        expected["items"][0]["quoted_unit_price"] = 2500
        expected["collection_amount"] = 10000
        expected["collection_evidence"] = "collect INR 10,000"
        captured = {}

        def transport(request, timeout):
            captured["request"] = request
            captured["timeout"] = timeout
            return json.dumps({"choices": [{"message": {"content": json.dumps(expected)}}]}).encode()

        result = AzureOrderProvider(config, transport=transport).extract_order(
            "Collect INR 10,000 from Ramesh and deliver 3 Sprite cases quoted at INR 2,500 each.",
            CONTEXT,
        )
        request = captured["request"]
        payload = json.loads(request.data)
        self.assertEqual(
            request.full_url,
            "https://azure.test/openai/deployments/gpt-4.1-mini/chat/completions?api-version=2024-10-21",
        )
        self.assertEqual(request.get_header("Api-key"), "azure-secret")
        self.assertEqual(captured["timeout"], 4)
        self.assertTrue(payload["response_format"]["json_schema"]["strict"])
        self.assertNotIn("minimum", json.dumps(payload["response_format"]))
        self.assertEqual(result["items"][0]["quoted_unit_price"], 2500)
        self.assertEqual(result["collection_amount"], 10000)

    def test_nullable_object_schema_keeps_additional_properties_false(self) -> None:
        """Azure's strict schema mode rejects an object branch of anyOf that is

        missing additionalProperties: false; a nullable object field (query,
        status_update) must keep it on the object branch, not just at the
        sibling level that gets discarded when type becomes anyOf.
        """
        config = AzureOpenAIConfig(
            endpoint="https://azure.test", api_key="azure-secret",
            deployment="gpt-4.1-mini", max_retries=0,
        )
        expected = OfflineSarvamProvider().extract_order("Ramesh ko kal 1 case Sprite", CONTEXT)
        captured = {}

        def transport(request, timeout):
            del timeout
            captured["body"] = json.loads(request.data)
            return json.dumps({"choices": [{"message": {"content": json.dumps(expected)}}]}).encode()

        AzureOrderProvider(config, transport=transport).extract_order("transcript", CONTEXT)
        schema = captured["body"]["response_format"]["json_schema"]["schema"]
        for field_name in ("query", "status_update"):
            field_schema = schema["properties"][field_name]
            object_branch = next(branch for branch in field_schema["anyOf"] if branch["type"] == "object")
            self.assertIs(object_branch["additionalProperties"], False)
            self.assertIn("properties", object_branch)

    def test_foundry_endpoint_uses_openai_v1_route(self) -> None:
        config = AzureOpenAIConfig(
            endpoint="https://resource.services.ai.azure.com", api_key="azure-secret",
            deployment="gpt-4.1-mini", max_retries=0,
        )
        expected = OfflineSarvamProvider().extract_order(
            "Ramesh ko kal 1 case Sprite", CONTEXT
        )
        captured = {}

        def transport(request, timeout):
            del timeout
            captured["url"] = request.full_url
            captured["body"] = json.loads(request.data)
            return json.dumps({"choices": [{"message": {"content": json.dumps(expected)}}]}).encode()

        AzureOrderProvider(config, transport=transport).extract_order("transcript", CONTEXT)
        self.assertEqual(
            captured["url"],
            "https://resource.services.ai.azure.com/openai/v1/chat/completions",
        )
        self.assertEqual(captured["body"]["model"], "gpt-4.1-mini")


if __name__ == "__main__":
    unittest.main()
