# Android ↔ laptop API contract

Use the laptop's Wi-Fi IPv4 address, currently `http://172.17.209.51:8000`. The app should store it as a configurable base URL because DHCP can change it.

For local HTTP development, the Android debug manifest needs internet permission and cleartext access:

```xml
<uses-permission android:name="android.permission.INTERNET" />
<application android:usesCleartextTraffic="true" ... />
```

Restrict cleartext to debug builds; use HTTPS outside a trusted local network.

## 1. Discover capabilities

```http
GET /v1/mobile/config
```

Returns the accepted recording MIME types, 15 MB limit, and confirmation requirement.

## 2. Upload and process a recording

```http
POST /v1/mobile/voice-jobs
Idempotency-Key: <stable UUID for this recording>
X-Merchant-Id: mer_demo
Content-Type: multipart/form-data

audio=<binary recording>
language_hint=hi-IN
```

Use the same idempotency key when retrying the same request. Sarvam translates speech to English, then Azure OpenAI classifies the transcript into one of three intents and produces its structured output.

For an order (`create_sales_order`), a successful response is `202` and contains `id`, `state` (`NEEDS_CLARIFICATION` or `READY_FOR_REVIEW`), `revision`, `transcript`, `draft`, one optional `clarification`, and navigation `links`. Explicit spoken values are exposed as `draft.items[].quotedUnitPricePaise` and `draft.collectionAmountPaise`.

For a read-only question about existing orders ("how many orders are pending for Ramesh") or a spoken status update ("mark Ramesh's order delivered"), the response is terminal immediately: `state` is `ANSWERED`, `draft` and `clarification` are both `null`, and `queryResult.answerText` holds the answer (also spoken back via `voiceAnswer.audioBase64`). A status update additionally sets `committedOrderId` to the order it changed. There is no clarify/confirm step for these — render the answer and stop. A status update always marks the customer's oldest not-yet-delivered order unless an order number was explicitly spoken, in which case that exact order is used.

## 3. Answer a clarification

```http
POST <links.clarify>
Idempotency-Key: <new stable UUID>
Content-Type: application/json

{"revision": 1, "answer": "case"}
```

Render only the question currently returned. Repeat if the next response still has `state=NEEDS_CLARIFICATION`.

## 4. Confirm after review

```http
POST <links.confirm>
Idempotency-Key: <new stable UUID>
Content-Type: application/json

{"revision": 2, "spokenConfirmation": true, "language": "hi-IN"}
```

The server performs the order, invoice, ledger and outbox writes atomically. There is no product catalog: the spoken product name is the order line's identity directly. The response contains:

```json
{
  "order": {
    "id": "ord_...",
    "orderNumber": "VL-1042",
    "totalPaise": 750000,
    "collectionAmountPaise": 1000000,
    "lines": [{"unitPricePaise": 250000, "priceSource": "SPOKEN_QUOTE"}]
  },
  "invoice": {"id": "inv_...", "invoiceNumber": "INV-1042"},
  "confirmationText": "Order VL-1042 ban gaya...",
  "artifacts": {
    "invoice": {"url": "http://<laptop>:8000/v1/invoices/inv_.../pdf", "contentType": "application/pdf"},
    "audio": {"url": "http://<laptop>:8000/v1/orders/ord_.../confirmation-audio", "contentType": "audio/wav", "language": "hi-IN"}
  }
}
```

Download or stream the PDF URL into the phone's PDF viewer and the audio URL into ExoPlayer/Media3. Both artifact requests should send `X-Merchant-Id` once real authentication replaces the demo merchant header.

## Failure handling

- `409 STALE_DRAFT`: refresh the job and use its current revision.
- `409 IDEMPOTENCY_CONFLICT`: generate a new key only if the payload intentionally changed.
- `503 PROVIDER_ERROR`: keep the recording and retry later with the same key.
- `404 AUDIO_NOT_FOUND`: the commercial transaction succeeded but TTS was unavailable; display `confirmationText`.

The Android app must never infer success from a failed network request. Treat an order as committed only when the confirmation response includes an order and invoice ID.
