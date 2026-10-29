import { dom } from "./dom.js";
import { state } from "./state.js";
import { setHint } from "./utils.js";

export const RETRYABLE_STATUS_CODES = new Set([429, 502, 503, 504]);
// Badge d'environnement de l'en-tete : il suit l'API reellement jointe
// (champ `environment` de /health), pas le profil du fichier config.json.
const ENVIRONMENT_LABELS = { staging: "Beta", prod: "", production: "", dev: "Test", test: "Test", local: "Local" };

export async function renderEnvironmentPill() {
  let environment = "";
  try {
    environment = String((await api("/health")).environment || "").toLowerCase();
  } catch {
    environment = "";
  }
  const onThisMachine = ["localhost", "127.0.0.1"].includes(window.location.hostname) && environment === "dev";
  const label = onThisMachine ? "Local" : (ENVIRONMENT_LABELS[environment] ?? environment);
  dom.environmentPill.textContent = label;
  dom.environmentPill.classList.toggle("is-empty", !label);
}

export async function loadConfig() {
  const response = await fetch("./config.json", { cache: "no-store" });
  if (!response.ok) {
    throw new Error("Impossible de charger config.json");
  }
  state.config = await response.json();

  const profiles = state.config.profiles || {};
  dom.envSelect.innerHTML = "";
  Object.entries(profiles).forEach(([key, profile]) => {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = profile.label || key;
    dom.envSelect.appendChild(option);
  });

  const savedProfile = localStorage.getItem("bee.profile");
  const defaultProfile = state.config.defaultProfile || "local";
  state.profile = profiles[savedProfile] ? savedProfile : defaultProfile;
  dom.envSelect.value = state.profile;

  const savedOverride = localStorage.getItem("bee.apiOverride") || "";
  dom.overrideUrl.value = savedOverride;
  applyApiBaseUrl();
  setHint(dom.configHint, `Profil actif: ${state.profile}`, "ok");
}

export function applyApiBaseUrl() {
  const isLocalHost = ["localhost", "127.0.0.1", "::1"].includes(window.location.hostname);
  if (!isLocalHost) {
    state.apiBaseUrl = window.location.origin;
    dom.overrideUrl.value = "";
    dom.overrideUrl.disabled = true;
    dom.saveConfig.disabled = true;
    return;
  }
  const profileData = state.config.profiles[state.profile] || {};
  const override = (dom.overrideUrl.value || "").trim();
  const rawValue = override || profileData.apiBaseUrl || "same-origin";
  state.apiBaseUrl = rawValue === "same-origin" ? window.location.origin : rawValue.replace(/\/$/, "");
}

export function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export function normalizeApiDetail(detail) {
  if (Array.isArray(detail)) {
    return detail.map((item) => item?.msg || JSON.stringify(item)).join(" | ");
  }
  if (detail && typeof detail === "object") {
    return JSON.stringify(detail);
  }
  return String(detail);
}

export async function fetchWithRetry(url, init, maxAttempts = 3, baseDelayMs = 220) {
  let lastError = null;

  for (let attempt = 1; attempt <= maxAttempts; attempt += 1) {
    try {
      const response = await fetch(url, init);
      if (RETRYABLE_STATUS_CODES.has(response.status) && attempt < maxAttempts) {
        await sleep(baseDelayMs * attempt);
        continue;
      }
      return response;
    } catch (error) {
      lastError = error;
      if (attempt < maxAttempts) {
        await sleep(baseDelayMs * attempt);
        continue;
      }
      throw error;
    }
  }

  throw lastError || new Error("Echec reseau");
}

export async function api(path, options = {}) {
  const headers = { ...(options.headers || {}) };
  if (state.token) {
    headers.Authorization = `Bearer ${state.token}`;
  }
  if (options.body && !headers["Content-Type"]) {
    headers["Content-Type"] = "application/json";
  }

  const response = await fetchWithRetry(`${state.apiBaseUrl}${path}`, {
    method: options.method || "GET",
    headers,
    body: options.body ? JSON.stringify(options.body) : undefined
  });

  let payload = null;
  const asText = await response.text();
  if (asText) {
    try {
      payload = JSON.parse(asText);
    } catch {
      payload = { detail: asText };
    }
  }

  if (!response.ok) {
    const detail = payload?.detail || payload?.error || `${response.status} ${response.statusText}`;
      const error = new Error(normalizeApiDetail(detail));
      error.status = response.status;
      error.payload = payload;
      throw error;
  }

  return payload;
}
