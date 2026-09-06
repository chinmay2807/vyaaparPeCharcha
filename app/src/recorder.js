import { Capacitor } from "@capacitor/core";

function base64ToBlob(base64, mimeType) {
  const binary = atob(base64);
  const bytes = new Uint8Array(binary.length);
  for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
  return new Blob([bytes], { type: mimeType });
}

class NativeRecorder {
  async start() {
    const { VoiceRecorder } = await import("capacitor-voice-recorder");
    this.plugin = VoiceRecorder;
    const permission = await VoiceRecorder.hasAudioRecordingPermission();
    if (!permission.value) {
      const granted = await VoiceRecorder.requestAudioRecordingPermission();
      if (!granted.value) throw new Error("Microphone permission was denied");
    }
    await VoiceRecorder.startRecording();
  }

  async stop() {
    const result = await this.plugin.stopRecording();
    const { recordDataBase64, mimeType } = result.value;
    return { blob: base64ToBlob(recordDataBase64, mimeType), mimeType, filename: "recording.aac" };
  }
}

class BrowserRecorder {
  async start() {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    this.stream = stream;
    this.chunks = [];
    this.mimeType = MediaRecorder.isTypeSupported("audio/webm") ? "audio/webm" : "audio/mp4";
    this.mediaRecorder = new MediaRecorder(stream, { mimeType: this.mimeType });
    this.mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) this.chunks.push(event.data);
    };
    this.mediaRecorder.start();
  }

  async stop() {
    const stopped = new Promise((resolve) => {
      this.mediaRecorder.onstop = resolve;
    });
    this.mediaRecorder.stop();
    await stopped;
    this.stream.getTracks().forEach((track) => track.stop());
    const blob = new Blob(this.chunks, { type: this.mimeType });
    const extension = this.mimeType.includes("webm") ? "webm" : "mp4";
    return { blob, mimeType: this.mimeType, filename: `recording.${extension}` };
  }
}

export function createRecorder() {
  return Capacitor.isNativePlatform() ? new NativeRecorder() : new BrowserRecorder();
}
