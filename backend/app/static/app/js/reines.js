import { api } from "./api.js";
import { dom } from "./dom.js";
import { refreshSelectedRuche, selectRuche } from "./ruches.js";
import { state } from "./state.js";
import { formatFrenchDate, setHint, setStatus } from "./utils.js";

// Duree depuis le jour de mise en place de la reine (jour J).
export function queenTenure(placedAt) {
  const days = Math.max(0, Math.floor((Date.now() - new Date(placedAt).getTime()) / 86400000));
  if (days < 31) return `${days} jour(s)`;
  const years = Math.floor(days / 365);
  const months = Math.floor((days % 365) / 30.44);
  return years ? `${years} an(s) ${months} mois` : `${months} mois`;
}

export function renderQueenSummary(reines) {
  dom.queenHistoryList.innerHTML = reines.length ? "" : "<li>Aucune reine dans l historique.</li>";
  reines.forEach((reine) => {
    const item = document.createElement("li");
    item.textContent = `${reine.statut === "active" ? "Active" : "Terminee"} | ${reine.origine} | mise en place ${formatFrenchDate(reine.date_mise_en_place)}${reine.date_fin ? ` | fin ${formatFrenchDate(reine.date_fin)}` : ""}`;
    dom.queenHistoryList.appendChild(item);
  });
  const active = reines.find((item) => item.statut === "active");
  if (!active) {
    dom.queenSummary.textContent = "Aucune reine active renseignee.";
    return;
  }
  dom.queenSummary.textContent = `Reine active: ${active.origine}, en place depuis le ${formatFrenchDate(active.date_mise_en_place)} (${queenTenure(active.date_mise_en_place)}), race ${active.race || "-"}. Historique: ${reines.length} reine(s).`;
}

export async function saveQueen(event) {
  event.preventDefault();
  if (!state.selectedRuche) {
    setHint(dom.queenFormHint, "Selectionne une ruche d abord.", "error");
    return;
  }
  try {
    await api(`/ruches/${encodeURIComponent(state.selectedRuche.id)}/reines`, {
      method: "POST",
      body: {
        date_mise_en_place: `${dom.queenDate.value}T00:00:00Z`,
        origine: dom.queenOrigin.value,
        race: dom.queenRace.value.trim() || null,
        provenance: dom.queenProvenance.value.trim() || null
      }
    });
    dom.queenForm.reset();
    if (dom.queenDialog.open) dom.queenDialog.close();
    setStatus("Nouvelle reine enregistree.");
    await refreshSelectedRuche();
    await selectRuche(state.selectedRuche);
  } catch (error) {
    setHint(dom.queenFormHint, `Remplacement impossible: ${error.message}`, "error");
  }
}
