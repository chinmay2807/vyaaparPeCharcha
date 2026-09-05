import tempfile
import unittest
from pathlib import Path

from vyapaar.try_audio import audio_mime, multipart_audio


class TryAudioTests(unittest.TestCase):
    def test_common_recording_formats_have_sarvam_compatible_mime_types(self):
        self.assertEqual(audio_mime(Path("order.m4a")), "audio/mp4")
        self.assertEqual(audio_mime(Path("order.mp4")), "audio/mp4")
        self.assertEqual(audio_mime(Path("order.wav")), "audio/wav")
        self.assertEqual(audio_mime(Path("order.ogg")), "audio/ogg")

    def test_multipart_contains_audio_and_language(self):
        with tempfile.TemporaryDirectory() as directory:
            recording = Path(directory) / "order.wav"
            recording.write_bytes(b"audio-bytes")
            body, content_type = multipart_audio(recording, "hi-IN")
        self.assertIn("multipart/form-data; boundary=", content_type)
        self.assertIn(b'name="audio"', body)
        self.assertIn(b"audio-bytes", body)
        self.assertIn(b"hi-IN", body)


if __name__ == "__main__":
    unittest.main()
