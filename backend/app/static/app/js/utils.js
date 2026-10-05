import { dom } from "./dom.js";

export function escapeHtml(value) {
  return String(value ?? "").replace(/[&<>"']/g, (character) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#039;"
  })[character]);
}

export function setStatus(message) {
  dom.status.textContent = message;
}

export function setHint(target, message, kind = "") {
  target.textContent = message;
  target.classList.remove("ok", "error");
  if (kind) {
    target.classList.add(kind);
  }
}

export function optionalNumber(value) {
  return value === "" ? null : Number(value);
}

export function optionalBoolean(value) {
  return value === "" ? null : value === "true";
}

// Capacite par defaut d'un corps selon son format (comme materiel_flux.py).
export function defaultFrameCount(format) {
  const normalized = (format || "").trim().toLowerCase();
  if (normalized === "ruchette" || normalized === "nucleus") return 6;
  if (normalized === "warre") return 8;
  return 10;
}

export function formatFrenchDate(value) {
  return value ? new Date(value).toLocaleDateString("fr-FR") : "-";
}

export function optionalSelectBoolean(value) {
  return value === "" ? null : value === "true";
}

export function formatRatio(value) {
  return value == null ? "-" : `${Math.round(Number(value) * 100)}%`;
}

export function periodLabel(start, end) {
  if (!start || !end) return "Periode";
  const currentYear = new Date().getFullYear();
  if (start === `${currentYear}-01-01` && end.startsWith(`${currentYear}-`)) return `Saison ${currentYear}`;
  if (start.endsWith("-01-01") && end.endsWith("-12-31") && start.slice(0, 4) === end.slice(0, 4)) return `Saison ${start.slice(0, 4)}`;
  return `Du ${formatFrenchDate(start)} au ${formatFrenchDate(end)}`;
}

// Oeil des champs mot de passe : bascule texte/masque, utilisable au toucher.
export function bindPasswordToggles(root = document) {
  root.querySelectorAll("[data-password-for]").forEach((button) => {
    const input = document.getElementById(button.dataset.passwordFor);
    if (!input) return;
    button.addEventListener("click", () => {
      const visible = input.type === "password";
      input.type = visible ? "text" : "password";
      button.setAttribute("aria-pressed", String(visible));
      button.setAttribute("aria-label", visible ? "Masquer le mot de passe" : "Afficher le mot de passe");
      input.focus();
    });
  });
}
