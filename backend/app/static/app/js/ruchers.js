import { api } from "./api.js";
import { refreshDashboard, renderDashboardContext } from "./dashboard.js";
import { dom } from "./dom.js";
import { setActiveTab } from "./navigation.js";
import { renderRuches, rucherHives } from "./ruches.js";
import { state } from "./state.js";
import { escapeHtml, optionalNumber, setHint, setStatus } from "./utils.js";
import { renderVisites } from "./visites.js";

// Le detail du rucher n a de sens que dans l onglet Ruchers. Sans ce garde-fou,
// selectionner un rucher depuis Visites ou Statistiques y injecte toute la liste.
export function updateRucherPanelVisibility() {
  const dashboardCard = document.getElementById("dashboard-card");
  const activeTab = dashboardCard?.dataset.activeTab;
  if (dom.rucherSelectedPanel) {
    dom.rucherSelectedPanel.hidden = activeTab !== "ruchers" || !state.selectedRucher;
  }
}

export function renderRuchers() {
  dom.ruchersList.innerHTML = "";
  const search = dom.rucherSearch.value.trim().toLowerCase();
  const ruchers = state.ruchers.filter((rucher) => !search || rucher.nom.toLowerCase().includes(search));
  if (ruchers.length === 0) {
    dom.ruchersList.innerHTML = "<li>Aucun rucher.</li>";
    return;
  }

  ruchers.forEach((rucher) => {
    const li = document.createElement("li");
    li.className = "rucher-card-item";
    const button = document.createElement("button");
    const terrainIcons = { plaine: "🌾", bocage: "🌿", montagne: "⛰", foret: "🌲", ville: "🏙", littoral: "🌊", autre: "📍" };
    const terrain = rucher.type_terrain || "autre";
    const isInactive = rucher.statut_activite === "inactif";
    button.classList.toggle("is-inactive", isInactive);
    button.innerHTML = `<span class="rucher-icon terrain-${escapeHtml(terrain)}" aria-hidden="true">${terrainIcons[terrain] || terrainIcons.autre}</span><span class="rucher-card-copy"><strong>${escapeHtml(rucher.nom)}</strong><small>${escapeHtml(terrain)}</small></span><span class="rucher-status${isInactive ? " is-inactive" : ""}">${isInactive ? "Inactif" : "Actif"}</span>`;
    if (state.selectedRucher?.id === rucher.id) {
      button.classList.add("active");
    }
    button.addEventListener("click", () => selectRucher(rucher));
    li.appendChild(button);
    dom.ruchersList.appendChild(li);
  });
}

export function renderRucherDetail(rucher) {
  updateRucherPanelVisibility();
  if (!rucher) {
    return;
  }
  dom.rucherDetail.innerHTML = [
    ["Nom", rucher.nom],
    ["Terrain", rucher.type_terrain || "-"],
    ["Activite", rucher.statut_activite],
  ].map(([label, value]) => `<div><strong>${escapeHtml(label)}</strong>${escapeHtml(value)}</div>`).join("");
}

export function openRucherEditor() {
  if (!state.selectedRucher) return;
  dom.editRucherId.value = state.selectedRucher.id;
  dom.editRucherName.value = state.selectedRucher.nom;
  dom.editRucherType.value = state.selectedRucher.type_terrain || "autre";
  dom.editRucherStatus.value = state.selectedRucher.statut_activite || "actif";
  dom.editRucherPeuplement.value = state.selectedRucher.statut_peuplement || "peuple";
  dom.editRucherLatitude.value = state.selectedRucher.latitude ?? "";
  dom.editRucherLongitude.value = state.selectedRucher.longitude ?? "";
  setHint(dom.editRucherHint, "", "");
  dom.rucherDialog.showModal();
}

export function openRucherCreator() {
  dom.createRucherName.value = "";
  dom.createRucherType.value = "plaine";
  setHint(dom.createRucherHint, "", "");
  dom.rucherCreateDialog.showModal();
  dom.createRucherName.focus();
}

export async function createRucherFromDialog(event) {
  event.preventDefault();
  try {
    await api("/ruchers", { method: "POST", body: { nom: dom.createRucherName.value.trim(), type_terrain: dom.createRucherType.value, statut_activite: "actif", statut_peuplement: "peuple" } });
    dom.rucherCreateDialog.close();
    await refreshDashboard();
    if (state.onboardingFlowActive) setActiveTab("dashboard");
    setStatus("Rucher cree.");
  } catch (error) {
    setHint(dom.createRucherHint, `Creation impossible: ${error.message}`, "error");
  }
}

export async function saveRucherEdit(event) {
  event.preventDefault();
  try {
    // Le PUT remplace tout le rucher : chaque champ est renvoye, sinon les
    // coordonnees GPS etaient effacees a chaque modification.
    const updated = await api(`/ruchers/${encodeURIComponent(dom.editRucherId.value)}`, {
      method: "PUT",
      body: {
        nom: dom.editRucherName.value.trim(),
        type_terrain: dom.editRucherType.value,
        statut_activite: dom.editRucherStatus.value,
        statut_peuplement: dom.editRucherPeuplement.value,
        latitude: optionalNumber(dom.editRucherLatitude.value),
        longitude: optionalNumber(dom.editRucherLongitude.value),
      },
    });
    dom.rucherDialog.close();
    state.ruchers = state.ruchers.map((rucher) => rucher.id === updated.id ? updated : rucher);
    state.selectedRucher = updated;
    renderRuchers();
    renderRucherDetail(updated);
    setStatus("Rucher mis a jour.");
  } catch (error) {
    setHint(dom.editRucherHint, `Modification impossible: ${error.message}`, "error");
  }
}

// Suppression en deux temps : un rucher occupe propose d'abord de deplacer
// ses ruches (l'API refuse de supprimer un rucher non vide), puis confirmation.
export function openRucherDelete() {
  const rucher = state.selectedRucher;
  if (!rucher) return;
  dom.rucherDialog.close();
  dom.rucherDeleteTitle.textContent = `Supprimer ${rucher.nom}`;
  setHint(dom.rucherDeleteHint, "", "");
  renderRucherDeleteStep();
  dom.rucherDeleteDialog.showModal();
}

export function renderRucherDeleteStep() {
  const rucher = state.selectedRucher;
  const hives = rucherHives(rucher.id);
  dom.rucherDeleteMoveStep.hidden = hives.length === 0;
  dom.rucherDeleteConfirmStep.hidden = hives.length > 0;
  if (hives.length) {
    // Des colonies vivantes ne vont pas a l'Atelier : seulement vers un autre
    // rucher (transhumance).
    const targets = state.ruchers.filter((item) => item.id !== rucher.id);
    dom.rucherDeleteMoveText.textContent = targets.length
      ? `Ce rucher contient ${hives.length} ruche(s). Transhume-les vers un autre rucher avant de le supprimer : leur historique est conserve.`
      : `Ce rucher contient ${hives.length} ruche(s). Cree d'abord un autre rucher pour les y transhumer.`;
    dom.rucherDeleteTarget.replaceChildren(...targets.map((item) => new Option(item.nom, item.id)));
    dom.rucherDeleteTarget.disabled = !targets.length;
    dom.btnRucherDeleteMove.disabled = !targets.length;
  } else {
    dom.rucherDeleteConfirmText.textContent = `Le rucher ${rucher.nom} est vide. Confirmer sa suppression definitive ?`;
  }
}

export async function moveHivesBeforeRucherDelete() {
  const hives = rucherHives(state.selectedRucher.id);
  const targetId = dom.rucherDeleteTarget.value;
  if (!targetId) {
    setHint(dom.rucherDeleteHint, "Choisis le rucher de destination.", "error");
    return;
  }
  try {
    await api("/ruches/move", { method: "POST", body: { ruche_ids: hives.map((ruche) => ruche.id), target_rucher_id: targetId, move_to_atelier: false } });
    await refreshDashboard();
    renderRucherDeleteStep();
    setHint(dom.rucherDeleteHint, `${hives.length} ruche(s) deplacee(s).`, "ok");
  } catch (error) {
    setHint(dom.rucherDeleteHint, `Deplacement impossible: ${error.message}`, "error");
  }
}

export async function confirmRucherDelete() {
  const rucher = state.selectedRucher;
  try {
    await api(`/ruchers/${encodeURIComponent(rucher.id)}`, { method: "DELETE" });
    dom.rucherDeleteDialog.close();
    state.selectedRucher = null;
    state.selectedRuche = null;
    state.selectedRucheIds.clear();
    await refreshDashboard();
    updateRucherPanelVisibility();
    setStatus(`Rucher ${rucher.nom} supprime.`);
  } catch (error) {
    setHint(dom.rucherDeleteHint, `Suppression impossible: ${error.message}`, "error");
  }
}

export async function selectRucher(rucher) {
  if (state.selectedRucher?.id !== rucher.id) {
    state.selectedRucheIds.clear();
  }
  state.selectedRucher = rucher;
  state.selectedRuche = null;
  renderDashboardContext();
  renderRucherDetail(rucher);
  renderRuchers();
  setStatus("Chargement des ruches...");
  try {
    state.ruches = await api(`/ruches?rucher_id=${encodeURIComponent(rucher.id)}`);
    state.latestVisitsByRuche.clear();
    // Un seul appel pour tout le rucher, au lieu d un appel par ruche.
    const dernieres = await api(`/statistiques/dernieres-visites?rucher_id=${encodeURIComponent(rucher.id)}`);
    dernieres.forEach((visite) => state.latestVisitsByRuche.set(visite.ruche_id, visite));
    renderRuches();
    renderVisites([]);
    setStatus("Ruches chargees.");
  } catch (error) {
    setStatus(`Erreur ruches: ${error.message}`);
  }
}
