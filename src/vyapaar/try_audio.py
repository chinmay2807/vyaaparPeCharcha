"""Interactive local client for exercising the complete backend with an audio file."""

from __future__ import annotations

import argparse
import json
import mimetypes
import sys
import uuid
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen


MIME_OVERRIDES = {
    ".aac": "audio/aac",
    ".aif": "audio/aiff",
    ".aiff": "audio/aiff",
    ".amr": "audio/amr",
    ".flac": "audio/flac",
    ".m4a": "audio/mp4",
    ".mp4": "audio/mp4",
    ".mp3": "audio/mpeg",
    ".ogg": "audio/ogg",
    ".opus": "audio/opus",
    ".wav": "audio/wav",
    ".webm": "audio/webm",
    ".wma": "audio/x-ms-wma",
}


def audio_mime(path: Path) -> str:
    return MIME_OVERRIDES.get(path.suffix.lower()) or mimetypes.guess_type(path.name)[0] or "application/octet-stream"


def multipart_audio(path: Path, language: str) -> tuple[bytes, str]:
    boundary = f"----Vyapaar{uuid.uuid4().hex}"
    audio = path.read_bytes()
    parts = [
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"language_hint\"\r\n\r\n{language}\r\n".encode(),
        (
            f"--{boundary}\r\nContent-Disposition: form-data; name=\"audio\"; "
            f"filename=\"{path.name}\"\r\nContent-Type: {audio_mime(path)}\r\n\r\n"
        ).encode(),
        audio,
        f"\r\n--{boundary}--\r\n".encode(),
    ]
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def call(url: str, method: str = "GET", *, body: bytes | None = None,
         content_type: str | None = None, key: str | None = None,
         merchant: str = "mer_demo") -> tuple[bytes, str]:
    headers = {"X-Merchant-Id": merchant}
    if content_type:
        headers["Content-Type"] = content_type
    if key:
        headers["Idempotency-Key"] = key
    request = Request(url, data=body, headers=headers, method=method)
    try:
        with urlopen(request, timeout=90) as response:
            return response.read(), response.headers.get_content_type()
    except HTTPError as error:
        detail = error.read().decode("utf-8", "replace")
        raise RuntimeError(f"Backend returned HTTP {error.code}: {detail}") from error
    except URLError as error:
        raise RuntimeError(f"Cannot reach backend at {url}: {error.reason}") from error


def json_call(url: str, method: str, payload: dict[str, Any], key: str,
              merchant: str) -> dict[str, Any]:
    raw, _ = call(
        url, method, body=json.dumps(payload).encode(), content_type="application/json",
        key=key, merchant=merchant,
    )
    return json.loads(raw)


def local_url(base_url: str, supplied: str) -> str:
    return f"{base_url.rstrip('/')}{urlsplit(supplied).path}"


def choose_answer(clarification: dict[str, Any], scripted: list[str]) -> Any:
    print(f"\nClarification: {clarification['question']}")
    options = clarification.get("options", [])
    for index, option in enumerate(options, 1):
        print(f"  {index}. {option['label']}")
    entered = scripted.pop(0) if scripted else input("Answer (number or value): ").strip()
    if entered.isdigit() and options and 1 <= int(entered) <= len(options):
        return options[int(entered) - 1]["value"]
    return entered


def save_artifact(base_url: str, descriptor: dict[str, Any], destination: Path,
                  merchant: str) -> Path:
    raw, _ = call(local_url(base_url, descriptor["url"]), merchant=merchant)
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_bytes(raw)
    return destination


def run(args: argparse.Namespace) -> int:
    path = Path(args.audio).expanduser().resolve()
    if not path.is_file():
        raise RuntimeError(f"Audio file not found: {path}")
    body, content = multipart_audio(path, args.language)
    key = args.idempotency_key or f"audio-{uuid.uuid4().hex}"
    raw, _ = call(
        f"{args.base_url.rstrip('/')}/v1/mobile/voice-jobs", "POST",
        body=body, content_type=content, key=key, merchant=args.merchant,
    )
    job = json.loads(raw)
    print(f"\nTranscript [{job.get('language')}]:\n{job.get('transcript')}\n")
    print("Extracted draft:")
    print(json.dumps(job.get("draft"), indent=2, ensure_ascii=False))

    scripted = list(args.answer)
    while job["state"] == "NEEDS_CLARIFICATION":
        answer = choose_answer(job["clarification"], scripted)
        job = json_call(
            local_url(args.base_url, job["links"]["clarify"]), "POST",
            {"revision": job["revision"], "answer": answer},
            f"clarify-{uuid.uuid4().hex}", args.merchant,
        )
        print("\nUpdated draft:")
        print(json.dumps(job.get("draft"), indent=2, ensure_ascii=False))

    if job["state"] != "READY_FOR_REVIEW":
        raise RuntimeError(f"Job cannot be confirmed; state is {job['state']}")
    if not args.yes and input("\nConfirm and save this order? [y/N]: ").strip().lower() not in {"y", "yes"}:
        print("Not confirmed. The draft was saved, but stock and ledger were not changed.")
        return 0

    result = json_call(
        local_url(args.base_url, job["links"]["confirm"]), "POST",
        {"revision": job["revision"], "spokenConfirmation": True, "language": args.language},
        f"confirm-{uuid.uuid4().hex}", args.merchant,
    )
    target = Path(args.output).resolve() / job["id"]
    invoice = save_artifact(
        args.base_url, result["artifacts"]["invoice"],
        target / result["artifacts"]["invoice"]["filename"], args.merchant,
    )
    audio = result["artifacts"]["audio"]
    confirmation = None
    if audio.get("url"):
        audio_name = "confirmation.wav" if audio.get("contentType") == "audio/wav" else "confirmation.mp3"
        confirmation = save_artifact(args.base_url, audio, target / audio_name, args.merchant)
    print(f"\nSaved order: {result['order']['orderNumber']}")
    print(f"Saved object ID: {result['order']['id']}")
    print(f"Invoice: {invoice}")
    if confirmation:
        print(f"Confirmation audio: {confirmation}")
        return 0
    print(f"Confirmation audio unavailable: {audio.get('code', 'TTS_UNAVAILABLE')}", file=sys.stderr)
    return 2


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a laptop audio file through the full backend")
    parser.add_argument("audio", help="Path to WAV, MP3, M4A, MP4, AAC, OGG, FLAC, WebM, AMR, or WMA audio")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--merchant", default="mer_demo")
    parser.add_argument("--language", default="hi-IN")
    parser.add_argument("--output", default="artifacts")
    parser.add_argument("--idempotency-key")
    parser.add_argument("--answer", action="append", default=[], help="Script a clarification answer")
    parser.add_argument("--yes", action="store_true", help="Confirm without the final y/N prompt")
    try:
        raise SystemExit(run(parser.parse_args()))
    except RuntimeError as error:
        print(f"Error: {error}", file=sys.stderr)
        raise SystemExit(1) from error


if __name__ == "__main__":
    main()
