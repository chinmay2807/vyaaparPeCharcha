import { Preferences } from "@capacitor/preferences";

const BASE_URL_KEY = "vyapaar_api_base_url";
const MERCHANT_ID = "mer_demo";
const DB_KEY = "vyapaar_db";
const DEFAULT_BASE_URL = "http://192.168.1.100:8000";

export async function getBaseUrl() {
  const { value } = await Preferences.get({ key: BASE_URL_KEY });
  return value || DEFAULT_BASE_URL;
}

export async function setBaseUrl(url) {
  await Preferences.set({ key: BASE_URL_KEY, value: url.replace(/\/+$/, "") });
}

function uuid() {
  if (crypto.randomUUID) return crypto.randomUUID();
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

async function request(path, { method = "GET", body, headers = {}, idempotencyKey, isForm = false } = {}) {
  const baseUrl = await getBaseUrl();
  const finalHeaders = { "X-Merchant-Id": MERCHANT_ID, ...headers };
  if (idempotencyKey) finalHeaders["Idempotency-Key"] = idempotencyKey;
  if (body && !isForm) finalHeaders["Content-Type"] = "application/json";

  const response = await fetch(`${baseUrl}${path}`, {
    method,
    headers: finalHeaders,
    body: isForm ? body : body ? JSON.stringify(body) : undefined,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json") ? await response.json() : await response.blob();

  if (!response.ok) {
    const error = new Error(payload?.error?.message || `Request failed: ${response.status}`);
    error.status = response.status;
    error.code = payload?.error?.code;
    error.details = payload?.error?.details;
    throw error;
  }
  return payload;
}

export const api = {
  config: () => request("/v1/mobile/config"),
  health: () => request("/health"),
  sync: () => request("/v1/mobile/sync"),

  getJob: (jobId) => request(`/v1/mobile/voice-jobs/${jobId}`),

  submitVoiceJob: (audioBlob, filename, mimeType, languageHint) => {
    const form = new FormData();
    form.append("audio", audioBlob, filename);
    if (languageHint) form.append("language_hint", languageHint);
    return request("/v1/mobile/voice-jobs", {
      method: "POST",
      body: form,
      isForm: true,
      idempotencyKey: uuid(),
    });
  },

  clarify: (job, revision, answer) =>
    request(job.links.clarify.replace(/^https?:\/\/[^/]+/, ""), {
      method: "POST",
      body: { revision, answer },
      idempotencyKey: uuid(),
    }),

  confirm: (job, revision, language) =>
    request(job.links.confirm.replace(/^https?:\/\/[^/]+/, ""), {
      method: "POST",
      body: { revision, spokenConfirmation: true, language },
      idempotencyKey: uuid(),
    }),

  cancel: (jobId) =>
    request(`/v1/voice-jobs/${jobId}/cancel`, {
      method: "POST",
      body: {},
      idempotencyKey: uuid(),
    }),

  artifactUrl: async (relativeOrAbsoluteUrl) => {
    if (/^https?:\/\//.test(relativeOrAbsoluteUrl)) return relativeOrAbsoluteUrl;
    const baseUrl = await getBaseUrl();
    return `${baseUrl}${relativeOrAbsoluteUrl}`;
  },
};

export async function loadLocalDb() {
  const { value } = await Preferences.get({ key: DB_KEY });
  return value ? JSON.parse(value) : null;
}

export async function saveLocalDb(snapshot) {
  await Preferences.set({ key: DB_KEY, value: JSON.stringify(snapshot) });
}

export async function refreshLocalDb() {
  const snapshot = await api.sync();
  await saveLocalDb(snapshot);
  return snapshot;
}
