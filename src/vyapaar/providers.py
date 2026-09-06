"""Sarvam provider boundary with a deterministic, network-free demo fallback.

The live adapter is deliberately opt-in.  It reads the API key only from the
server environment, performs bounded retries, and never logs request bodies.
"""

from __future__ import annotations

import base64
import io
import json
import mimetypes
import os
import re
import time
import urllib.error
import urllib.request
import uuid
import wave
from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any, Callable, Mapping, Protocol
from urllib.parse import quote, urlsplit


SARVAM_BASE_URL = "https://api.sarvam.ai"
STT_PATH = "/speech-to-text"
CHAT_PATH = "/v1/chat/completions"
TTS_PATH = "/text-to-speech"


ORDER_DRAFT_SCHEMA: dict[str, Any] = {
    "type": "object",
    "additionalProperties": False,
    "required": [
        "intent",
        "customer",
        "delivery_date",
        "items",
        "mentioned_previous_balance",
        "collection_amount",
        "collection_evidence",
        "currency",
        "missing_fields",
        "warnings",
        "query",
        "status_update",
    ],
    "properties": {
        "intent": {"type": "string", "enum": ["create_sales_order", "query_orders", "update_order_status"]},
        "customer": {
            "type": "object",
            "additionalProperties": False,
            "required": ["spoken_name", "candidate_id", "confidence", "evidence"],
            "properties": {
                "spoken_name": {"type": "string"},
                "candidate_id": {"type": ["string", "null"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence": {"type": "string"},
            },
        },
        "delivery_date": {
            "type": "object",
            "additionalProperties": False,
            "required": ["value", "confidence", "evidence"],
            "properties": {
                "value": {"type": ["string", "null"]},
                "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                "evidence": {"type": "string"},
            },
        },
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": [
                    "spoken_name",
                    "quantity",
                    "unit",
                    "quoted_unit_price",
                    "confidence",
                    "evidence",
                ],
                "properties": {
                    "spoken_name": {"type": "string"},
                    "quantity": {"type": ["integer", "null"], "minimum": 1},
                    "unit": {"type": ["string", "null"]},
                    "quoted_unit_price": {"type": ["number", "null"]},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "evidence": {"type": "string"},
                },
            },
        },
        "mentioned_previous_balance": {"type": ["number", "null"]},
        "collection_amount": {"type": ["number", "null"]},
        "collection_evidence": {"type": "string"},
        "currency": {"type": "string", "enum": ["INR"]},
        "missing_fields": {"type": "array", "items": {"type": "string"}},
        "warnings": {"type": "array", "items": {"type": "string"}},
        "query": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["customer_spoken_name", "status_filter"],
            "properties": {
                "customer_spoken_name": {"type": ["string", "null"]},
                "status_filter": {"type": ["string", "null"], "enum": ["CONFIRMED", "DELIVERED", None]},
            },
        },
        "status_update": {
            "type": ["object", "null"],
            "additionalProperties": False,
            "required": ["customer_spoken_name", "order_number_spoken", "new_status"],
            "properties": {
                "customer_spoken_name": {"type": ["string", "null"]},
                "order_number_spoken": {"type": ["string", "null"]},
                "new_status": {"type": ["string", "null"], "enum": ["DELIVERED", None]},
            },
        },
    },
}


class ProviderError(RuntimeError):
    """A sanitized provider failure safe to surface in application logs."""

    def __init__(self, category: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.category = category
        self.retryable = retryable


class SarvamProvider(Protocol):
    def transcribe(
        self,
        audio: bytes,
        *,
        filename: str = "voice.webm",
        content_type: str | None = None,
        language_hint: str | None = None,
    ) -> dict[str, Any]: ...

    def extract_order(
        self, transcript: str, merchant_context: Mapping[str, Any]
    ) -> dict[str, Any]: ...

    def synthesize_confirmation(
        self, text: str, *, language: str = "hi-IN"
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class ProviderConfig:
    api_key: str
    base_url: str = SARVAM_BASE_URL
    stt_model: str = "saaras:v3"
    stt_mode: str = "codemix"
    llm_model: str = "sarvam-105b"
    vision_model: str = "sarvam-vision"
    tts_model: str = "bulbul:v3"
    timeout_seconds: float = 20.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> ProviderConfig:
        key = os.environ.get("SARVAM_API_KEY", "").strip()
        if not key:
            raise ProviderError("configuration", "SARVAM_API_KEY is required for live mode")
        return cls(
            api_key=key,
            base_url=os.environ.get("SARVAM_BASE_URL", SARVAM_BASE_URL).rstrip("/"),
            stt_model=os.environ.get("SARVAM_STT_MODEL", "saaras:v3"),
            stt_mode=os.environ.get("SARVAM_STT_MODE", "codemix"),
            llm_model=os.environ.get("SARVAM_LLM_MODEL", "sarvam-105b"),
            vision_model=os.environ.get("SARVAM_VISION_MODEL", "sarvam-vision"),
            tts_model=os.environ.get("SARVAM_TTS_MODEL", "bulbul:v3"),
            timeout_seconds=_positive_float_env("SARVAM_TIMEOUT_MS", 20_000) / 1000,
            max_retries=_nonnegative_int_env("SARVAM_MAX_RETRIES", 2),
        )


@dataclass(frozen=True)
class AzureOpenAIConfig:
    endpoint: str
    api_key: str
    deployment: str
    api_version: str = "2024-10-21"
    timeout_seconds: float = 30.0
    max_retries: int = 2

    @classmethod
    def from_env(cls) -> AzureOpenAIConfig:
        endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT", "").strip().rstrip("/")
        key = os.environ.get("AZURE_OPENAI_API_KEY", "").strip()
        deployment = (os.environ.get("AZURE_OPENAI_DEPLOYMENT", "").strip()
                      or os.environ.get("AZURE_OPENAI_MODEL", "").strip())
        if not endpoint:
            raise ProviderError("configuration", "AZURE_OPENAI_ENDPOINT is required for live mode")
        if not key:
            raise ProviderError("configuration", "AZURE_OPENAI_API_KEY is required for live mode")
        if not deployment:
            raise ProviderError("configuration", "AZURE_OPENAI_DEPLOYMENT is required for live mode")
        return cls(
            endpoint=endpoint,
            api_key=key,
            deployment=deployment,
            api_version=os.environ.get("AZURE_OPENAI_API_VERSION", "2024-10-21").strip(),
            timeout_seconds=_positive_float_env("AZURE_OPENAI_TIMEOUT_MS", 30_000) / 1000,
            max_retries=_nonnegative_int_env("AZURE_OPENAI_MAX_RETRIES", 2),
        )


class AzureOrderProvider:
    """Structured order extraction through an Azure OpenAI deployment."""

    def __init__(self, config: AzureOpenAIConfig | None = None, *,
                 transport: Transport | None = None,
                 sleep: Callable[[float], None] = time.sleep) -> None:
        self.config = config or AzureOpenAIConfig.from_env()
        self._transport = transport or _urlopen_transport
        self._sleep = sleep

    def extract_order(self, transcript: str, merchant_context: Mapping[str, Any]) -> dict[str, Any]:
        payload = {
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify the English transcript into exactly one intent, then extract that "
                        "intent's fields. Leave every field belonging to the other two intents at its "
                        "null/empty default.\n\n"
                        "create_sales_order: the merchant is placing a new order. Preserve every explicit "
                        "business instruction. There is no product catalog: each item's spoken_name is the "
                        "product's identity exactly as said, never matched against anything. Use only "
                        "customer IDs present in context; use null when no canonical customer matches. An "
                        "explicit per-unit agreed or quoted sale price belongs in quoted_unit_price. Money "
                        "is expressed in rupees. An instruction to collect, receive, or take money from the "
                        "customer belongs in collection_amount. An amount described as existing pending, "
                        "due, balance, or outstanding belongs in mentioned_previous_balance. Do not confuse "
                        "collection with balance or invoice total.\n\n"
                        "query_orders: the merchant is asking a read-only question about existing orders, "
                        "e.g. how many are pending, or for a customer's order status. Put the customer's "
                        "spoken name (or null if the question is about all customers) in "
                        "query.customer_spoken_name, and CONFIRMED or DELIVERED in query.status_filter if a "
                        "specific status was asked about, else null.\n\n"
                        "update_order_status: the merchant is reporting that an order was delivered/"
                        "completed, e.g. 'mark Ramesh's order delivered'. Put the customer's spoken name in "
                        "status_update.customer_spoken_name, an explicitly spoken order number (e.g. "
                        "'VL-1042') in status_update.order_number_spoken or null if none was said, and "
                        "DELIVERED in status_update.new_status.\n\n"
                        "Use null for absent values."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"transcript": transcript, "merchant_context": dict(merchant_context)},
                        ensure_ascii=False, separators=(",", ":"),
                    ),
                },
            ],
            "temperature": 0,
            "response_format": _response_format(
                "draft_command", _azure_compatible_schema(ORDER_DRAFT_SCHEMA)
            ),
        }
        if (urlsplit(self.config.endpoint).hostname or "").endswith(".services.ai.azure.com"):
            url = f"{self.config.endpoint}/openai/v1/chat/completions"
            payload["model"] = self.config.deployment
        else:
            encoded_deployment = quote(self.config.deployment, safe="")
            url = (
                f"{self.config.endpoint}/openai/deployments/{encoded_deployment}/chat/completions"
                f"?api-version={quote(self.config.api_version, safe='')}"
            )
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        last_error: ProviderError | None = None
        for attempt in range(self.config.max_retries + 1):
            request = urllib.request.Request(
                url, body,
                {"api-key": self.config.api_key, "Content-Type": "application/json",
                 "Accept": "application/json"},
                method="POST",
            )
            try:
                raw = self._transport(request, self.config.timeout_seconds)
                response = json.loads(raw.decode("utf-8"))
                if not isinstance(response, dict):
                    raise ValueError("expected object")
                result = _chat_json(response)
                validate_schema(result, ORDER_DRAFT_SCHEMA)
                return result
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or exc.code >= 500
                last_error = ProviderError(
                    "rate_limit" if exc.code == 429 else "http",
                    f"Azure OpenAI extraction request failed with status {exc.code}",
                    retryable=retryable,
                )
            except (urllib.error.URLError, TimeoutError, OSError):
                last_error = ProviderError(
                    "network", "Azure OpenAI extraction request failed", retryable=True
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise ProviderError(
                    "invalid_response", "Azure OpenAI extraction returned invalid JSON"
                ) from exc
            if not last_error.retryable or attempt >= self.config.max_retries:
                raise last_error
            self._sleep(min(0.25 * (2**attempt), 2.0))
        raise last_error or ProviderError("unknown", "Azure OpenAI extraction request failed")


class OfflineSarvamProvider:
    """Deterministic demo provider; makes no network calls and needs no secrets."""

    _DEFAULT_TRANSCRIPT = (
        "Ramesh ko kal ke liye 6 peti Sprite, 4 Coke, aur 20 Limca bhejna. "
        "Uska last ₹12,500 pending hai."
    )

    def transcribe(
        self,
        audio: bytes,
        *,
        filename: str = "voice.webm",
        content_type: str | None = None,
        language_hint: str | None = None,
    ) -> dict[str, Any]:
        del filename, content_type
        # Text fixtures make local tests and demos easy while arbitrary audio uses the golden sample.
        decoded = audio.decode("utf-8", errors="ignore").strip()
        match = re.fullmatch(r"TRANSCRIPT\s*:\s*(.{12,})", decoded, flags=re.I | re.S)
        text = match.group(1).strip() if match and _mostly_text(match.group(1)) else self._DEFAULT_TRANSCRIPT
        return {
            "text": text,
            "language": language_hint or "hi-IN",
            "model": "offline:deterministic-stt",
            "provider_request_id": "offline-stt-0001",
        }

    def extract_order(
        self, transcript: str, merchant_context: Mapping[str, Any]
    ) -> dict[str, Any]:
        result = _offline_order(transcript, merchant_context)
        validate_schema(result, ORDER_DRAFT_SCHEMA)
        return result

    def synthesize_confirmation(
        self, text: str, *, language: str = "hi-IN"
    ) -> dict[str, Any]:
        del text
        return {
            "audio": _silent_wav(),
            "content_type": "audio/wav",
            "language": language,
            "model": "offline:deterministic-tts",
            "provider_request_id": "offline-tts-0001",
        }


Transport = Callable[[urllib.request.Request, float], bytes]


class LiveSarvamProvider:
    """Thin synchronous HTTP adapter for Sarvam's current MVP endpoints."""

    def __init__(
        self,
        config: ProviderConfig | None = None,
        *,
        transport: Transport | None = None,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.config = config or ProviderConfig.from_env()
        self._transport = transport or _urlopen_transport
        self._sleep = sleep

    def transcribe(
        self,
        audio: bytes,
        *,
        filename: str = "voice.webm",
        content_type: str | None = None,
        language_hint: str | None = None,
    ) -> dict[str, Any]:
        fields = {"model": self.config.stt_model, "mode": self.config.stt_mode}
        if language_hint:
            fields["language_code"] = language_hint
        body, boundary = _multipart(
            fields,
            "file",
            filename,
            content_type or mimetypes.guess_type(filename)[0] or "application/octet-stream",
            audio,
        )
        result = self._request_json(
            STT_PATH, body, {"Content-Type": f"multipart/form-data; boundary={boundary}"}, "stt"
        )
        transcript = result.get("transcript") or result.get("text")
        if not isinstance(transcript, str) or not transcript.strip():
            raise ProviderError("invalid_response", "Sarvam STT returned no transcript")
        return {
            "text": transcript.strip(),
            "language": "en-IN" if self.config.stt_mode == "translate" else (
                result.get("language_code") or result.get("language") or language_hint
            ),
            "source_language": result.get("language_code") or result.get("language") or language_hint,
            "model": self.config.stt_model,
            "provider_request_id": result.get("request_id"),
        }

    def extract_order(
        self, transcript: str, merchant_context: Mapping[str, Any]
    ) -> dict[str, Any]:
        payload = {
            "model": self.config.llm_model,
            "temperature": 0,
            "reasoning_effort": None,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "Classify the transcript as create_sales_order, query_orders, or "
                        "update_order_status, then extract that intent's fields; leave the other two "
                        "intents' fields at their null/empty default. Use only canonical IDs supplied in "
                        "context. Never invent prices, balances, stock, customer IDs, SKU IDs, units, or "
                        "dates. Use null and missing_fields when uncertain. Output JSON matching the schema."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {"transcript": transcript, "merchant_context": dict(merchant_context)},
                        ensure_ascii=False,
                        separators=(",", ":"),
                    ),
                },
            ],
            "response_format": _response_format("draft_command", ORDER_DRAFT_SCHEMA),
        }
        response = self._post_json(CHAT_PATH, payload, "extraction")
        result = _chat_json(response)
        validate_schema(result, ORDER_DRAFT_SCHEMA)
        return result

    def synthesize_confirmation(
        self, text: str, *, language: str = "hi-IN"
    ) -> dict[str, Any]:
        response = self._post_json(
            TTS_PATH,
            {
                "text": text,
                "language_code": language,
                "speaker": "shubh",
                "model": self.config.tts_model,
                "enable_preprocessing": True,
            },
            "tts",
        )
        encoded = (response.get("audios") or [response.get("audio")])[0]
        if not isinstance(encoded, str):
            raise ProviderError("invalid_response", "Sarvam TTS returned no audio")
        try:
            audio = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise ProviderError("invalid_response", "Sarvam TTS returned invalid audio") from exc
        return {
            "audio": audio,
            "content_type": response.get("content_type", "audio/wav"),
            "language": language,
            "model": self.config.tts_model,
            "provider_request_id": response.get("request_id"),
        }

    def _post_json(self, path: str, payload: Mapping[str, Any], operation: str) -> dict[str, Any]:
        return self._request_json(
            path,
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
            {"Content-Type": "application/json"},
            operation,
        )

    def _request_json(
        self, path: str, body: bytes, headers: Mapping[str, str], operation: str
    ) -> dict[str, Any]:
        request_headers = {"api-subscription-key": self.config.api_key, "Accept": "application/json"}
        request_headers.update(headers)
        last_error: ProviderError | None = None
        for attempt in range(self.config.max_retries + 1):
            request = urllib.request.Request(
                f"{self.config.base_url}{path}", body, request_headers, method="POST"
            )
            try:
                raw = self._transport(request, self.config.timeout_seconds)
                parsed = json.loads(raw.decode("utf-8"))
                if not isinstance(parsed, dict):
                    raise ValueError("expected object")
                return parsed
            except urllib.error.HTTPError as exc:
                retryable = exc.code == 429 or exc.code >= 500
                last_error = ProviderError(
                    "rate_limit" if exc.code == 429 else "http",
                    f"Sarvam {operation} request failed with status {exc.code}",
                    retryable=retryable,
                )
            except (urllib.error.URLError, TimeoutError, OSError):
                last_error = ProviderError(
                    "network", f"Sarvam {operation} request failed", retryable=True
                )
            except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
                raise ProviderError(
                    "invalid_response", f"Sarvam {operation} returned invalid JSON"
                ) from exc
            if not last_error.retryable or attempt >= self.config.max_retries:
                raise last_error
            self._sleep(min(0.25 * (2**attempt), 2.0))
        raise last_error or ProviderError("unknown", f"Sarvam {operation} request failed")


class LiveHybridProvider:
    """Sarvam speech in/out with Azure OpenAI for order reasoning."""

    def __init__(self, sarvam: LiveSarvamProvider | None = None,
                 azure: AzureOrderProvider | None = None) -> None:
        self.sarvam = sarvam or LiveSarvamProvider()
        self.azure = azure or AzureOrderProvider()

    def transcribe(self, audio: bytes, *, filename: str = "voice.webm",
                   content_type: str | None = None,
                   language_hint: str | None = None) -> dict[str, Any]:
        return self.sarvam.transcribe(
            audio, filename=filename, content_type=content_type,
            language_hint=language_hint,
        )

    def extract_order(self, transcript: str,
                      merchant_context: Mapping[str, Any]) -> dict[str, Any]:
        return self.azure.extract_order(transcript, merchant_context)

    def synthesize_confirmation(self, text: str, *, language: str = "hi-IN") -> dict[str, Any]:
        return self.sarvam.synthesize_confirmation(text, language=language)


def create_provider(*, live: bool | None = None) -> SarvamProvider:
    """Return offline fixtures or the live Sarvam-speech/Azure-reasoning pipeline."""

    enabled = live if live is not None else os.environ.get("SARVAM_LIVE", "").lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return LiveHybridProvider() if enabled else OfflineSarvamProvider()


def validate_schema(value: Any, schema: Mapping[str, Any], path: str = "$") -> None:
    """Validate the strict subset of JSON Schema used by provider responses."""

    types = schema.get("type")
    allowed = [types] if isinstance(types, str) else types
    if allowed and not any(_matches_json_type(value, item) for item in allowed):
        raise ProviderError("schema", f"Provider output has invalid type at {path}")
    if value is None:
        return
    if "enum" in schema and value not in schema["enum"]:
        raise ProviderError("schema", f"Provider output has invalid value at {path}")
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in schema and value < schema["minimum"]:
            raise ProviderError("schema", f"Provider output is below minimum at {path}")
        if "maximum" in schema and value > schema["maximum"]:
            raise ProviderError("schema", f"Provider output is above maximum at {path}")
    if isinstance(value, dict):
        properties = schema.get("properties", {})
        missing = [key for key in schema.get("required", []) if key not in value]
        if missing:
            raise ProviderError("schema", f"Provider output is missing {missing[0]} at {path}")
        if schema.get("additionalProperties") is False:
            extras = value.keys() - properties.keys()
            if extras:
                raise ProviderError(
                    "schema", f"Provider output has unexpected {sorted(extras)[0]} at {path}"
                )
        for key, item in value.items():
            if key in properties:
                validate_schema(item, properties[key], f"{path}.{key}")
    if isinstance(value, list) and "items" in schema:
        for index, item in enumerate(value):
            validate_schema(item, schema["items"], f"{path}[{index}]")


_UNIT_WORDS = {
    "peti": "case", "crate": "case", "case": "case", "carton": "case",
    "bottle": "piece", "bottles": "piece", "piece": "piece", "pieces": "piece",
    "pcs": "piece", "pc": "piece", "kg": "kg", "kilo": "kg", "kilos": "kg", "pouch": "pouch",
}
_ITEM_SPLIT = re.compile(r",|\baur\b|\band\b", re.I)
_PRICE_PATTERN = re.compile(r"(?:@|price|rate)\D*(\d+(?:\.\d+)?)", re.I)
_TRAILING_VERB = re.compile(r"\s+(?:ke\s+liye|bhejna|bhejo|dena|do|chahiye)\s*$", re.I)
_LEADING_QUANTITY = re.compile(
    r"^(\d+(?:\.\d+)?)\s*(peti|crate|case|carton|bottles?|pieces?|pcs?|kg|kilos?|pouch)?\s*(.+)$",
    re.I,
)
_LEADING_TIME_WORDS = re.compile(
    r"^\s*(?:kal|aaj|parso|parson|today|tomorrow|yesterday|कल|आज|परसों)"
    r"(?:\s+ke\s+liye)?\s*|^\s*ke\s+liye\s*",
    re.I,
)


_STATUS_UPDATE_PATTERN = re.compile(
    r"\b(?:mark|deliver|delivered|complete[d]?)\b.*\b(?:order|delivery)?\b", re.I
)
_QUERY_PATTERN = re.compile(
    r"\bhow many\b|\bhow much\b|\bkitn[ae]\b|\bpending\s+orders?\b|\border\s+status\b", re.I
)
_ORDER_NUMBER_PATTERN = re.compile(r"\b(VL-\d+)\b", re.I)


def _detect_intent(transcript: str) -> str:
    if _QUERY_PATTERN.search(transcript):
        return "query_orders"
    if _STATUS_UPDATE_PATTERN.search(transcript) and re.search(r"\bdeliver", transcript, re.I):
        return "update_order_status"
    return "create_sales_order"


_EMPTY_QUERY = {"customer_spoken_name": None, "status_filter": None}
_EMPTY_STATUS_UPDATE = {"customer_spoken_name": None, "order_number_spoken": None, "new_status": None}


def _offline_order(transcript: str, context: Mapping[str, Any]) -> dict[str, Any]:
    """Extract a draft with no product catalog: whatever product name is spoken

    becomes the order line directly. Only quantity/unit/price are pattern-matched
    out of the transcript; the product identity is never looked up anywhere.
    """
    customers = _as_list(context.get("customers"))
    customer = _find_customer(transcript, customers)
    intent = _detect_intent(transcript)
    if intent == "query_orders":
        status_filter = "DELIVERED" if re.search(r"\bdelivered\b", transcript, re.I) else (
            "CONFIRMED" if re.search(r"\bpending\b", transcript, re.I) else None)
        return {
            "intent": "query_orders",
            "customer": {"spoken_name": customer[0], "candidate_id": customer[1],
                         "confidence": 0.98 if customer[1] else 0.0, "evidence": customer[0]},
            "delivery_date": {"value": None, "confidence": 0.0, "evidence": ""},
            "items": [],
            "mentioned_previous_balance": None,
            "collection_amount": None,
            "collection_evidence": "",
            "currency": "INR",
            "missing_fields": [],
            "warnings": [],
            "query": {"customer_spoken_name": customer[0] or None, "status_filter": status_filter},
            "status_update": _EMPTY_STATUS_UPDATE,
        }
    if intent == "update_order_status":
        order_match = _ORDER_NUMBER_PATTERN.search(transcript)
        return {
            "intent": "update_order_status",
            "customer": {"spoken_name": customer[0], "candidate_id": customer[1],
                         "confidence": 0.98 if customer[1] else 0.0, "evidence": customer[0]},
            "delivery_date": {"value": None, "confidence": 0.0, "evidence": ""},
            "items": [],
            "mentioned_previous_balance": None,
            "collection_amount": None,
            "collection_evidence": "",
            "currency": "INR",
            "missing_fields": [],
            "warnings": [],
            "query": _EMPTY_QUERY,
            "status_update": {"customer_spoken_name": customer[0] or None,
                               "order_number_spoken": order_match.group(1) if order_match else None,
                               "new_status": "DELIVERED"},
        }
    reference = _reference_date(context)
    delivery_evidence = "kal" if re.search(r"\bkal\b|कल", transcript, re.I) else ""
    delivery = reference + timedelta(days=1) if delivery_evidence else None

    items: list[dict[str, Any]] = []
    missing: list[str] = []
    tail_match = re.search(r"\bko\b(.*?)(?:\.\s*uska|\.\s*last|$)", transcript, re.I | re.S)
    item_span = tail_match.group(1) if tail_match else transcript
    for raw_segment in _ITEM_SPLIT.split(item_span):
        evidence = raw_segment.strip(" .")
        if not evidence:
            continue
        price_match = _PRICE_PATTERN.search(evidence)
        remainder = _PRICE_PATTERN.sub("", evidence).strip(" .")
        remainder = _TRAILING_VERB.sub("", remainder).strip(" .")
        remainder = _LEADING_TIME_WORDS.sub("", remainder).strip(" .")
        if not remainder:
            continue
        quantity: int | float | None = None
        unit: str | None = None
        leading = _LEADING_QUANTITY.match(remainder)
        if leading:
            quantity_value = float(leading.group(1))
            quantity = int(quantity_value) if quantity_value.is_integer() else quantity_value
            unit = _UNIT_WORDS.get((leading.group(2) or "").lower())
            name = leading.group(3).strip(" .")
        else:
            name = remainder
        if not name:
            continue
        index = len(items)
        if unit is None:
            missing.append(f"items[{index}].unit")
        items.append({
            "spoken_name": name,
            "quantity": quantity,
            "unit": unit,
            "quoted_unit_price": float(price_match.group(1)) if price_match else None,
            "confidence": 0.9,
            "evidence": evidence,
        })
    if not items:
        missing.append("items")
    balance_match = re.search(r"(?:₹|rs\.?|inr)?\s*([\d,]+)\s*(?:pending|baaki|बाकी)", transcript, re.I)
    return {
        "intent": "create_sales_order",
        "customer": {
            "spoken_name": customer[0],
            "candidate_id": customer[1],
            "confidence": 0.98 if customer[1] else 0.45,
            "evidence": customer[0],
        },
        "delivery_date": {
            "value": delivery.isoformat() if delivery else None,
            "confidence": 0.99 if delivery else 0.0,
            "evidence": delivery_evidence,
        },
        "items": items,
        "mentioned_previous_balance": float(balance_match.group(1).replace(",", "")) if balance_match else None,
        "collection_amount": None,
        "collection_evidence": "",
        "currency": "INR",
        "missing_fields": (["customer.candidate_id"] if not customer[1] else [])
        + ([] if delivery else ["delivery_date.value"])
        + missing,
        "warnings": [],
        "query": _EMPTY_QUERY,
        "status_update": _EMPTY_STATUS_UPDATE,
    }


def _find_customer(transcript: str, customers: list[Any]) -> tuple[str, str | None]:
    lowered = transcript.lower()
    for customer in customers:
        if not isinstance(customer, Mapping):
            continue
        names = [customer.get("name"), *_as_list(customer.get("aliases"))]
        for name in filter(None, names):
            if str(name).lower() in lowered:
                return str(name), str(customer.get("id")) if customer.get("id") else None
    match = re.search(r"(?:^|\s)([A-Z][a-z]{2,})\s+ko\b", transcript)
    return (match.group(1), None) if match else ("", None)


def _reference_date(context: Mapping[str, Any]) -> date:
    value = context.get("reference_date") or context.get("today") or "2026-09-05"
    try:
        return date.fromisoformat(str(value)[:10])
    except ValueError:
        return date(2026, 9, 5)


def _chat_json(response: Mapping[str, Any]) -> dict[str, Any]:
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ProviderError("invalid_response", "Sarvam reasoning returned no content") from exc
    if isinstance(content, dict):
        return content
    if not isinstance(content, str):
        raise ProviderError("invalid_response", "Sarvam reasoning returned invalid content")
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", content.strip(), flags=re.I)
    try:
        parsed = json.loads(cleaned)
    except json.JSONDecodeError as exc:
        raise ProviderError("invalid_response", "Sarvam reasoning returned invalid JSON") from exc
    if not isinstance(parsed, dict):
        raise ProviderError("invalid_response", "Sarvam reasoning returned a non-object")
    return parsed


def _response_format(name: str, schema: Mapping[str, Any]) -> dict[str, Any]:
    return {"type": "json_schema", "json_schema": {"name": name, "strict": True, "schema": schema}}


def _azure_compatible_schema(value: Any) -> Any:
    """Remove unsupported constraints and express nullable types with anyOf."""

    if isinstance(value, list):
        return [_azure_compatible_schema(item) for item in value]
    if not isinstance(value, Mapping):
        return value
    converted: dict[str, Any] = {}
    for key, item in value.items():
        if key in {"minimum", "maximum", "pattern", "format"}:
            continue
        if key == "type" and isinstance(item, list):
            converted["anyOf"] = [{"type": item_type} for item_type in item]
        else:
            converted[key] = _azure_compatible_schema(item)
    return converted


def _multipart(
    fields: Mapping[str, str],
    file_field: str,
    filename: str,
    content_type: str,
    content: bytes,
) -> tuple[bytes, str]:
    boundary = f"----vyapaar-{uuid.uuid4().hex}"
    chunks: list[bytes] = []
    for name, value in fields.items():
        chunks.extend(
            [
                f"--{boundary}\r\n".encode(),
                f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode(),
                str(value).encode(),
                b"\r\n",
            ]
        )
    safe_name = filename.replace('"', "").replace("\r", "").replace("\n", "")
    chunks.extend(
        [
            f"--{boundary}\r\n".encode(),
            f'Content-Disposition: form-data; name="{file_field}"; filename="{safe_name}"\r\n'.encode(),
            f"Content-Type: {content_type}\r\n\r\n".encode(),
            content,
            b"\r\n",
            f"--{boundary}--\r\n".encode(),
        ]
    )
    return b"".join(chunks), boundary


def _urlopen_transport(request: urllib.request.Request, timeout: float) -> bytes:
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read()


def _silent_wav() -> bytes:
    target = io.BytesIO()
    with wave.open(target, "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(8_000)
        output.writeframes(b"\x00\x00" * 800)
    return target.getvalue()


def _matches_json_type(value: Any, type_name: str) -> bool:
    return {
        "object": lambda: isinstance(value, dict),
        "array": lambda: isinstance(value, list),
        "string": lambda: isinstance(value, str),
        "number": lambda: isinstance(value, (int, float)) and not isinstance(value, bool),
        "integer": lambda: isinstance(value, int) and not isinstance(value, bool),
        "boolean": lambda: isinstance(value, bool),
        "null": lambda: value is None,
    }.get(type_name, lambda: False)()


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _mostly_text(value: str) -> bool:
    printable = sum(character.isprintable() for character in value)
    return bool(value) and printable / len(value) > 0.9


def _positive_float_env(name: str, default: float) -> float:
    try:
        value = float(os.environ.get(name, default))
    except ValueError as exc:
        raise ProviderError("configuration", f"{name} must be a number") from exc
    if value <= 0:
        raise ProviderError("configuration", f"{name} must be positive")
    return value


def _nonnegative_int_env(name: str, default: int) -> int:
    try:
        value = int(os.environ.get(name, default))
    except ValueError as exc:
        raise ProviderError("configuration", f"{name} must be an integer") from exc
    if value < 0:
        raise ProviderError("configuration", f"{name} must be non-negative")
    return value
