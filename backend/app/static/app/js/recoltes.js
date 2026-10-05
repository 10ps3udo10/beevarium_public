import { api } from "./api.js";
import { dom } from "./dom.js";
import { refreshVisitsIfActive } from "./navigation.js";
import { state } from "./state.js";
import { loadEnrichedStatistics } from "./statistiques.js";
import { escapeHtml, formatFrenchDate, setHint, setStatus } from "./utils.js";

export function openHarvestDialog(harvest = null) {
  // Un ecouteur branche directement transmet l'evenement click : ce n'est pas une recolte.
  if (harvest instanceof Event) harvest = null;
  const selectedRucherId = state.selectedRuche?.rucher_id || state.selectedRucher?.id || "";
  dom.harvestRucher.replaceChildren(new Option("Tous les ruchers", ""));
  state.ruchers.forEach((rucher) => dom.harvestRucher.add(new Option(rucher.nom, rucher.id)));
  dom.harvestRucher.value = selectedRucherId;
  populateHarvestHives(selectedRucherId, state.selectedRuche?.id || "");
  dom.harvestDialogTitle.textContent = harvest ? "Modifier la recolte" : "Nouvelle recolte";
  dom.harvestId.value = harvest?.id || "";
  dom.btnDeleteHarvest.hidden = !harvest;
  const contextHive = harvest?.ruche_id ? state.allRuches.find((ruche) => ruche.id === harvest.ruche_id) : state.selectedRuche;
  dom.harvestContext.textContent = contextHive
    ? `${contextHive.identifiant_personnalise} · ${state.ruchers.find((rucher) => rucher.id === contextHive.rucher_id)?.nom || "Atelier"}`
    : "Choisis un rucher puis une ruche, ou tout un rucher pour repartir la recolte.";
  dom.harvestWeight.value = harvest?.poids_miel_kg ?? "";
  dom.harvestDialog.showModal();
}

export function populateHarvestHives(rucherId, selectedId = "") {
  const hives = state.allRuches.filter((ruche) => !ruche.is_at_atelier && (!rucherId || ruche.rucher_id === rucherId));
  dom.harvestRuche.replaceChildren(new Option("Toutes les ruches du rucher", ""));
  hives.forEach((ruche) => dom.harvestRuche.add(new Option(ruche.identifiant_personnalise, ruche.id)));
  dom.harvestRuche.value = selectedId;
}

export async function deleteHarvest() {
  const harvestId = dom.harvestId.value;
  if (!harvestId || !window.confirm("Supprimer definitivement cette recolte ? Cette action est irreversible.")) return;
  try {
    await api(`/recoltes/${encodeURIComponent(harvestId)}`, { method: "DELETE" });
    dom.harvestDialog.close();
    await loadRucheHarvests();
    await loadEnrichedStatistics();
    await refreshVisitsIfActive();
    setStatus("Recolte supprimee.");
  } catch (error) {
    setHint(dom.harvestHint, `Suppression impossible: ${error.message}`, "error");
  }
}

export async function saveHarvest(event) {
  event.preventDefault();
  const selectedRucheId = dom.harvestRuche.value;
  const selectedRucherId = dom.harvestRucher.value;
  try {
    const harvestId = dom.harvestId.value;
    if (harvestId) {
      await api(`/recoltes/${encodeURIComponent(harvestId)}`, { method: "PUT", body: { poids_miel_kg: Number(dom.harvestWeight.value) } });
    } else {
      const hives = state.allRuches.filter((ruche) => !ruche.is_at_atelier && (!selectedRucherId || ruche.rucher_id === selectedRucherId) && (!selectedRucheId || ruche.id === selectedRucheId));
      if (!hives.length) throw new Error("Selectionne au moins un rucher ou une ruche.");
      const weight = Number(dom.harvestWeight.value) / hives.length;
      // Repartition a parts egales : pratique, mais elle masque les ruches
      // faibles dans les statistiques ; l'apiculteur confirme en connaissance.
      const scope = selectedRucherId ? `les ${hives.length} ruches du rucher` : `les ${hives.length} ruches de tous les ruchers`;
      if (hives.length > 1 && !window.confirm(`Attention : ${dom.harvestWeight.value} kg seront repartis a parts egales sur ${scope}, soit ${weight.toFixed(2)} kg par ruche.\n\nLes statistiques ne distingueront plus les bonnes et les faibles productrices. Pour un suivi ruche par ruche, choisis une ruche.\n\nConfirmer la repartition ?`)) return;
      await Promise.all(hives.map((ruche) => api("/recoltes", { method: "POST", body: { ruche_id: ruche.id, visite_ruche_id: null, poids_miel_kg: weight } })));
    }
    dom.harvestDialog.close();
    await loadRucheHarvests();
    await loadEnrichedStatistics();
    await refreshVisitsIfActive();
    setStatus("Recolte enregistree.");
  } catch (error) {
    setHint(dom.harvestHint, `Enregistrement impossible: ${error.message}`, "error");
  }
}

export async function loadRucheHarvests() {
  if (!state.selectedRuche) return;
  const harvests = await api(`/recoltes?ruche_id=${encodeURIComponent(state.selectedRuche.id)}`);
  dom.rucheHarvestsList.innerHTML = harvests.length ? "" : "<li>Aucune recolte.</li>";
  harvests.forEach((harvest) => {
    const item = document.createElement("li");
    const button = document.createElement("button");
    button.textContent = `${formatFrenchDate(harvest.date_recolte)} · ${Number(harvest.poids_miel_kg).toFixed(2)} kg`;
    button.addEventListener("click", () => openHarvestDialog(harvest));
    item.appendChild(button);
    dom.rucheHarvestsList.appendChild(item);
  });
}

export async function openHarvestFromHistory(recolte) {
  try {
    const fullHarvest = await api(`/recoltes/${encodeURIComponent(recolte.id)}`);
    state.selectedRuche = { id: recolte.ruche_id, identifiant_personnalise: recolte.ruche_label };
    openHarvestDialog({ ...fullHarvest, poids_miel_kg: Number(fullHarvest.poids_miel_kg) });
  } catch (error) {
    setStatus(`Recolte indisponible: ${error.message}`);
  }
}

export function renderHoneyBreakdown(target, rows, limit = 8, keepEmpty = false) {
  if (!rows.length || (!keepEmpty && rows.every((row) => !Number(row.value)))) {
    target.innerHTML = "<p class=\"hint\">Aucune recolte sur la periode.</p>";
    return;
  }
  const maximum = Math.max(...rows.map((row) => Number(row.value)), 1);
  target.innerHTML = rows.slice(0, limit).map((row) => {
    const value = Number(row.value);
    const empty = value === 0 ? " is-empty" : "";
    return `<div class="bar-row${empty}" title="${escapeHtml(row.label)} : ${value.toFixed(1)} kg"><span>${escapeHtml(row.label)}</span><div class="bar-track"><i style="width:${Math.min(100, value / maximum * 100)}%"></i></div><strong>${value ? `${value.toFixed(1)} kg` : "0 kg"}</strong></div>`;
  }).join("");
}
