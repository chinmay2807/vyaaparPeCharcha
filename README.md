# VyapaarPeCharcha

FastAPI backend for an Android voice-order app. The phone records an order and sends the audio over the local network to a laptop. The laptop transcribes and extracts it with SarvamAI, asks for any required clarification, and waits for confirmation. Confirmation creates the order atomically and returns URLs for a PDF invoice and Sarvam-generated audio that the phone can display and play.

## Isolated setup

The project uses only its local `.venv`; nothing is installed in the global Python environment.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[dev]"
vyapaar-reset
vyapaar-api
```

The current `.env` binds FastAPI/Uvicorn to `0.0.0.0:8000`, uses SarvamAI for English STT and final TTS, and uses the configured Azure OpenAI deployment for structured order reasoning. The API documentation is available at the configured `APP_BASE_URL/docs` while the server is running.

If the laptop changes networks, run `ipconfig`, update `APP_BASE_URL` with the Wi-Fi IPv4 address, and use that same address as the Android app's API base URL. Both devices must be on the same network. Windows may ask you to allow Python on private networks.

## Android flow

1. `POST /v1/mobile/voice-jobs` as `multipart/form-data`, with the recording in the `audio` field and an `Idempotency-Key` header.
2. Display the returned transcript and draft. If state is `NEEDS_CLARIFICATION`, show the single returned question and send the answer to its `links.clarify` URL.
3. Show a review screen. Do not confirm silently.
4. Send the current revision to `links.confirm`.
5. Display `artifacts.invoice.url` as a PDF and stream or download `artifacts.audio.url` into the Android media player.

The mobile endpoint accepts `audio/mp4`, `audio/x-m4a`, `audio/3gpp`, `audio/aac`, `audio/webm`, `audio/mpeg`, and `audio/wav`, up to 15 MB. See [the Android API contract](docs/ANDROID_API.md).

## Structure

- `src/vyapaar/api.py`: FastAPI factory, middleware, exception handling, and Uvicorn entry point.
- `src/vyapaar/routers/`: separate catalog, voice, reconciliation, and Android/LAN `APIRouter` modules.
- `src/vyapaar/schemas.py`: Pydantic request schemas.
- `src/vyapaar/service.py`: deterministic workflow, revision, idempotency, and atomic confirmation service.
- `src/vyapaar/providers.py`: live Sarvam STT/TTS, Azure OpenAI structured order extraction, Sarvam Vision, and offline fixtures.
- `src/vyapaar/store.py`: crash-safe local JSON persistence for the laptop demo.
- `infra/migrations/`: production-shaped PostgreSQL schema and seed data.

## Verification

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m pip check
```

The tests exercise real FastAPI routes, multipart Android uploads, clarification and revision handling, atomic rollback, idempotency, invoice download, confirmation-audio download, tenant isolation, and mocked live Sarvam contracts.

## Test an existing laptop recording

Keep `vyapaar-api` running in one terminal. In another terminal, pass the recording path to the interactive client:

```powershell
.\.venv\Scripts\vyapaar-try-audio.exe "C:\path\to\order.m4a"
```

It prints the Sarvam transcript and extracted draft, prompts for any clarification, asks before confirmation, and downloads the resulting invoice and confirmation audio under `artifacts/<voice-job-id>/`.

The invoice is operational only. This MVP does not claim GST, e-invoice, or statutory accounting compliance. See [privacy and retention](docs/PRIVACY.md) and the [acceptance matrix](docs/ACCEPTANCE.md).

## Android / frontend app

The `android/` directory holds a Capacitor-wrapped React + Vite frontend (the voice-order UI with the 3D orb) that talks to this backend over the local network. See its `package.json` for scripts; install dependencies with `npm install`, run `npm run build`, then `npx cap sync android` before opening the `android/` project in Android Studio or running `gradlew assembleDebug`.
