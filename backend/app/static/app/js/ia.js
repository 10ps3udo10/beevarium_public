import { api } from "./api.js";
import { dom } from "./dom.js";
import { formatFrenchDate, optionalNumber, optionalSelectBoolean, setHint, setStatus } from "./utils.js";

export function fillDraftForm(draft) {
  dom.iaDraftId.value = draft.id;
  dom.iaReineVue.value = draft.reine_vue == null ? "" : String(draft.reine_vue);
  dom.iaCouvain.value = draft.etat_couvain || "";
  dom.iaReserves.value = draft.reserves_nourriture || "";
  dom.iaNote.value = draft.note_ruche ?? "";
  dom.iaCadresCouvain.value = draft.nombre_cadres_couvain ?? "";
  dom.iaCadresTotal.value = draft.nombre_cadres_total ?? "";
  setHint(dom.iaReviewHint, "", "");
  dom.iaReviewDialog.showModal();
}

export function renderDrafts(drafts) {
  dom.iaReviewSummary.textContent = `${drafts.length} brouillon(s) IA a revoir.`;
  dom.iaDraftsList.innerHTML = drafts.length ? "" : "<li>Aucun brouillon IA.</li>";
  drafts.forEach((draft) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.textContent = `${formatFrenchDate(draft.date_visite)} | note ${draft.note_ruche ?? "-"} | ${draft.ruche_id.slice(0, 8)}`;
    button.addEventListener("click", () => fillDraftForm(draft));
    item.appendChild(button);
    dom.iaDraftsList.appendChild(item);
  });
}

export async function loadDrafts() {
  try {
    const drafts = await api("/ia-vocale/brouillons");
    renderDrafts(drafts);
  } catch (error) {
    if (error.message.includes("premium")) {
      dom.iaReviewSummary.textContent = "Revue IA disponible pour les comptes Premium.";
      dom.iaDraftsList.innerHTML = "<li>Acces Premium requis.</li>";
      return;
    }
    dom.iaReviewSummary.textContent = `Chargement impossible: ${error.message}`;
  }
}

export function draftPayload(status) {
  return {
    reine_vue: optionalSelectBoolean(dom.iaReineVue.value),
    etat_couvain: dom.iaCouvain.value || null,
    reserves_nourriture: dom.iaReserves.value || null,
    note_ruche: optionalNumber(dom.iaNote.value),
    nombre_cadres_couvain: optionalNumber(dom.iaCadresCouvain.value),
    nombre_cadres_total: optionalNumber(dom.iaCadresTotal.value),
    statut_validation: status
  };
}

export async function saveDraft(status) {
  const draftId = dom.iaDraftId.value;
  if (!draftId) {
    setHint(dom.iaReviewHint, "Selectionne un brouillon d abord.", "error");
    return;
  }
  try {
    await api(`/visites/${encodeURIComponent(draftId)}`, { method: "PATCH", body: draftPayload(status) });
    dom.iaReviewDialog.close();
    dom.iaReviewForm.reset();
    dom.iaDraftId.value = "";
    await loadDrafts();
    setStatus(status === "valide" ? "Brouillon IA valide." : "Brouillon IA enregistre.");
  } catch (error) {
    setHint(dom.iaReviewHint, `Mise a jour impossible: ${error.message}`, "error");
  }
}

export async function rejectDraft() {
  const draftId = dom.iaDraftId.value;
  if (!draftId) {
    setHint(dom.iaReviewHint, "Selectionne un brouillon d abord.", "error");
    return;
  }
  try {
    await api(`/ia-vocale/brouillons/${encodeURIComponent(draftId)}`, { method: "DELETE" });
    dom.iaReviewDialog.close();
    dom.iaReviewForm.reset();
    dom.iaDraftId.value = "";
    await loadDrafts();
    setStatus("Brouillon IA rejete.");
  } catch (error) {
    setHint(dom.iaReviewHint, `Rejet impossible: ${error.message}`, "error");
  }
}
