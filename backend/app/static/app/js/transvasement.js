import { api } from "./api.js";
import { refreshDashboard } from "./dashboard.js";
import { dom } from "./dom.js";
import { refreshSelectedRuche } from "./ruches.js";
import { FORMAT_LABELS, state } from "./state.js";
import { optionalNumber, setHint, setStatus } from "./utils.js";

// --- Transvasement : changer le contenant sans changer la colonie ---------------

export function openTransvasementDialog(fromVisit) {
  const ruche = state.selectedRuche;
  if (!ruche) {
    setStatus("Selectionne une ruche avant de la transvaser.");
    return;
  }
  state.transvasementFromVisit = fromVisit;
  const frames = ruche.nombre_cadres ?? (["ruchette", "nucleus"].includes(ruche.format_ruche) ? 6 : 10);
  dom.transvasementTitle.textContent = `Transvaser ${ruche.identifiant_personnalise}`;
  dom.transvasementCurrent.textContent = `Contenant actuel : ${FORMAT_LABELS[ruche.format_ruche] || "format non renseigne"}, ${frames} cadre(s).`;
  dom.transvasementForm.reset();
  dom.transvasementFormat.value = ruche.format_ruche === "ruchette" || ruche.format_ruche === "nucleus" ? "dadant" : (ruche.format_ruche || "dadant");
  dom.transvasementCadresTransferes.value = String(frames);
  dom.transvasementAnneeCire.value = String(new Date().getFullYear());
  dom.transvasementSource.replaceChildren(...state.atelierRuches
    .filter((item) => item.id !== ruche.id)
    .map((item) => new Option(`${item.identifiant_personnalise} · ${FORMAT_LABELS[item.format_ruche] || "format ?"}`, item.id)));
  updateTransvasementProvenance();
  setHint(dom.transvasementHint, "", "");
  dom.transvasementDialog.showModal();
}

export function updateTransvasementProvenance() {
  const fromPreparedHive = dom.transvasementProvenance.value === "ruche_atelier";
  dom.transvasementSourceWrap.hidden = !fromPreparedHive;
  dom.transvasementElements.hidden = fromPreparedHive;
  dom.transvasementFormat.disabled = fromPreparedHive;
}

export function transvasementPayload() {
  const payload = {
    format_apres: dom.transvasementFormat.value,
    provenance: dom.transvasementProvenance.value,
    elements: [...dom.transvasementElements.querySelectorAll("input:checked")].map((input) => input.value),
    cadres_transferes: Number(dom.transvasementCadresTransferes.value || 0),
    cadres_ajoutes: Number(dom.transvasementCadresAjoutes.value || 0),
    annee_cire: optionalNumber(dom.transvasementAnneeCire.value),
    nouvel_identifiant: dom.transvasementIdentifiant.value.trim() || null,
  };
  if (payload.provenance === "ruche_atelier") {
    const source = state.atelierRuches.find((item) => item.id === dom.transvasementSource.value);
    payload.ruche_atelier_id = source?.id || null;
    payload.format_apres = source?.format_ruche || payload.format_apres;
  }
  return payload;
}

export function describeTransvasement(payload) {
  const origin = { stock: "stock atelier", achat: "nouveau materiel", ruche_atelier: "ruche preparee" }[payload.provenance];
  return `Transvasement prevu : ${FORMAT_LABELS[payload.format_apres] || payload.format_apres} (${origin}), ${payload.cadres_transferes} cadre(s) transferes + ${payload.cadres_ajoutes} ajoute(s).`;
}

export async function submitTransvasement(event) {
  event.preventDefault();
  const payload = transvasementPayload();
  if (payload.provenance === "ruche_atelier" && !payload.ruche_atelier_id) {
    setHint(dom.transvasementHint, "Aucune ruche preparee a l'atelier.", "error");
    return;
  }
  if (state.transvasementFromVisit) {
    // Applique a l'enregistrement de la visite (donc aussi hors ligne).
    state.pendingTransvasement = payload;
    renderPendingTransvasement();
    dom.transvasementDialog.close();
    return;
  }
  try {
    const result = await api(`/ruches/${encodeURIComponent(state.selectedRuche.id)}/transvasements`, { method: "POST", body: payload });
    dom.transvasementDialog.close();
    await refreshSelectedRuche();
    await refreshDashboard();
    setStatus(`Colonie transvasee en ${FORMAT_LABELS[result.format_apres] || result.format_apres}.`);
    if (result.tag_suggestions.includes("production") && window.confirm("La colonie passe en ruche : ajouter le tag production ?")) {
      await api(`/ruches/${encodeURIComponent(state.selectedRuche.id)}/tags`, { method: "POST", body: { libelle: "production" } });
      await refreshSelectedRuche();
    }
  } catch (error) {
    setHint(dom.transvasementHint, `Transvasement impossible: ${error.message}`, "error");
  }
}

export function renderPendingTransvasement() {
  dom.visitTransvasementSummary.hidden = !state.pendingTransvasement;
  dom.visitTransvasementSummary.textContent = state.pendingTransvasement ? describeTransvasement(state.pendingTransvasement) : "";
}
