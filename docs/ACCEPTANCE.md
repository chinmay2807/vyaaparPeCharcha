# Acceptance checklist

| Requirement | Proof |
|---|---|
| Seed merchant and customers | `.\.venv\Scripts\vyapaar-reset.exe`; `GET /v1/customers` |
| Android recording upload over LAN | FastAPI multipart mobile route and end-to-end artifact test |
| Durable voice workflow | crash-safe JSON store and FastAPI workflow test |
| Transcript and detected language available | voice-job response |
| Sarvam speech with Azure reasoning | live hybrid-provider smoke test and Azure contract tests |
| No product catalog: spoken product name is the order line's identity | offline provider and API tests with unrecognized product names |
| Spoken quote, unit, and collection preserved | draft, invoice, and ledger assertion in API tests |
| Schema-valid extraction or recoverable error | domain/provider contract tests |
| Only genuinely necessary clarifications (price only; date/quantity/unit default; customer auto-created) | API tests for defaulting and clarification-minimization behavior |
| Immutable review edits | new revision; stale confirm returns `STALE_DRAFT` |
| No pre-confirm mutation | API test compares order, invoice, and ledger before confirm |
| Atomic, idempotent confirmation | rollback/idempotency tests and database unique indexes |
| Invoice and ledger reconcile | transaction and PDF tests |
| PDF and Sarvam audio returned to phone | mobile confirmation returns downloadable artifact URLs |
| Evaluation/demo fallback | deterministic offline provider |
| Tenant isolation | cross-merchant authorization tests |
| Retention and PII policy | `docs/PRIVACY.md` |

Run `.\.venv\Scripts\python.exe -m unittest discover -s tests -v`. Live Sarvam smoke tests are separate and require a key and budget cap. The Android UI is implemented (`app/`) and wired to this backend; see `CONTEXT.md`/`HISTORY.md`.
