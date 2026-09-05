# Acceptance checklist

| Requirement | Proof |
|---|---|
| Seed merchant, customers, and 30 SKU aliases | `.\.venv\Scripts\vyapaar-reset.exe`; `GET /v1/customers` and `/v1/skus` |
| Android recording upload over LAN | FastAPI multipart mobile route and end-to-end artifact test |
| Durable voice workflow | crash-safe JSON store and FastAPI workflow test |
| Transcript and detected language available | voice-job response |
| Sarvam speech with Azure reasoning | live hybrid-provider smoke test and Azure contract tests |
| Spoken quote and collection preserved | draft, invoice, and ledger assertion in API tests |
| Schema-valid extraction or recoverable error | domain/provider contract tests |
| One focused clarification | domain policy and end-to-end API test |
| Immutable review edits | new revision; stale confirm returns `STALE_DRAFT` |
| No pre-confirm mutation | API test compares order, stock, invoice, and ledger before confirm |
| Atomic, idempotent confirmation | rollback/idempotency tests and database unique indexes |
| Invoice, stock, and ledger reconcile | transaction and PDF tests |
| PDF and Sarvam audio returned to phone | mobile confirmation returns downloadable artifact URLs |
| Reviewable bill extraction | remains `REVIEW_REQUIRED` until explicit apply |
| Evaluation/demo fallback | 50-case fixture and deterministic provider |
| Tenant isolation | cross-merchant authorization tests |
| Retention and PII policy | `docs/PRIVACY.md` |

Run `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`. Live Sarvam smoke tests are separate and require a key and budget cap. The Android UI is intentionally not implemented in the current backend scope.
