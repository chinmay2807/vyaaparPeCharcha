# Privacy, security, and retention

- Audio, transcripts, invoices, and extracted documents are merchant-scoped. Production deployments must encrypt transport and storage and use short-lived signed object URLs.
- `SARVAM_API_KEY` is server-only. General logs contain request IDs, timing, model, and error category; they must not contain raw audio, transcripts, phone numbers, addresses, or financial values.
- The laptop demo stores uploaded and generated audio as base64 inside its local JSON data file so the Android phone can retry downloads. Reset the demo store to remove it. Production storage must move audio to encrypted object storage, enforce `RAW_AUDIO_RETENTION_HOURS` (24 hours by default), and support immediate user-requested deletion.
- The LAN demo uses cleartext HTTP and must only run on a trusted private network. Production and any untrusted-network use require HTTPS and authenticated artifact URLs.
- Uploaded audio/documents are untrusted input: validate type and size, scan in production, and never treat their content as executable instructions.
- Draft edits, confirmations, cancellations, and reconciliation actions are auditable. Inventory and ledger records are immutable business events.
- The included invoice is an operational document, not a claim of GST, e-invoice, or statutory accounting compliance.
- Production must add authentication, merchant-scoped authorization, encryption at rest, backups, rate limiting, malware scanning, account deletion, and a reviewed India privacy/GST policy before pilot use.
