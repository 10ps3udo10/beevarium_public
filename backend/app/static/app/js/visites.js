import { api } from "./api.js";
import { loadDashboardIndicators, refreshDashboard } from "./dashboard.js";
import { dom } from "./dom.js";
import { getOfflineOperation, queueOfflineVisit, syncOfflineVisits, updateOfflineOperation, updateSyncStatus } from "./offline.js";
import { openHarvestFromHistory } from "./recoltes.js";
import { refreshSelectedRuche, selectRuche } from "./ruches.js";
import { fillVisitCreateScope } from "./scope.js";
import { state } from "./state.js";
import { loadRucheTags, renderVisitSelectedTags, renderVisitTagSuggestions } from "./tags.js";
import { renderPendingTransvasement } from "./transvasement.js";
import { defaultFrameCount, escapeHtml, formatFrenchDate, optionalBoolean, optionalNumber, optionalSelectBoolean, setHint, setStatus } from "./utils.js";

export function renderFrameActionOptions() {
  if (!dom.visiteCadresAction) return;
  dom.visiteCadresAction.innerHTML = "<option value=\"\">Aucun mouvement</option>";
  if (dom.editVisitCadresAction) dom.editVisitCadresAction.innerHTML = "<option value=\"\">Aucun mouvement</option>";
  state.references.cadreActions.forEach((label, id) => {
    const option = document.createElement("option");
    option.value = id;
    option.textContent = label;
    dom.visiteCadresAction.appendChild(option);
    if (dom.editVisitCadresAction) dom.editVisitCadresAction.appendChild(option.cloneNode(true));
  });
}

export function editVisitFrameMovements() {
  if (!dom.editVisitCadresAction?.value || !dom.editVisitCadresAnnee?.value) return undefined;
  return [{
    ref_action_cadre_id: dom.editVisitCadresAction.value,
    quantite: Number(dom.editVisitCadresQuantite.value || 1),
    annee_cire: Number(dom.editVisitCadresAnnee.value),
  }];
}

export function resetVisiteForm() {
  dom.visiteForm.reset();
  state.pendingVisitTags = [];
  state.pendingTransvasement = null;
  renderPendingTransvasement();
  dom.visiteCadresQuantite.value = "1";
  dom.visiteCadresTotal.dataset.frameDelta = "0";
  dom.visiteHausseQuantite.value = "";
  dom.visiteHausseQuantite.disabled = true;
  renderVisitSelectedTags([]);
  renderVisitTagSuggestions(dom.visitTagSuggestions, []);
  setHint(dom.visiteFormHint, "", "");
}

// Type de ruche repris de la fiche ; le changer pendant la visite (essaim
// devenu production...) met la ruche a jour avec la visite, meme hors ligne.
function hydrateVisitHiveType(ruche) {
  const options = [...state.references.types.entries()]
    .sort((a, b) => a[1].localeCompare(b[1], "fr"))
    .map(([id, label]) => `<option value="${escapeHtml(id)}">${escapeHtml(label)}</option>`)
    .join("");
  dom.visiteTypeRuche.innerHTML = `<option value="">Non renseigne</option>${options}`;
  dom.visiteTypeRuche.value = ruche?.ref_type_ruche_id || "";
  dom.visiteTypeRuche.dataset.initial = dom.visiteTypeRuche.value;
}

export function hydrateVisitEquipmentFromRuche() {
  const ruche = state.selectedRuche;
  hydrateVisitHiveType(ruche);
  if (!ruche) return;
  dom.visiteCorps.checked = ruche.has_corps === true;
  dom.visiteHausse.checked = ruche.has_hausse === true;
  dom.visitePartition.checked = ruche.has_partition === true;
  dom.visiteGrille.checked = ruche.has_grille_a_reine === true;
  dom.visiteNourrisseur.checked = ruche.has_nourrisseur === true;
  dom.visiteToit.checked = ruche.has_toit === true;
  dom.visitePlancher.checked = ruche.has_plancher === true;
  dom.visiteHausseQuantite.disabled = !dom.visiteHausse.checked;
}

// Nouvelle visite : cadres pre-remplis d'apres la ruche (nombre de cadres) et
// sa derniere visite (cadres de couvain). L'apiculteur corrige si besoin ; une
// valeur deja modifiee pendant le chargement n'est pas ecrasee.
export async function prefillVisitFramesFromRuche() {
  const ruche = state.selectedRuche;
  if (!ruche) return;
  const before = [dom.visiteCadresTotal.value, dom.visiteCadresCouvain.value];
  // En ligne, la derniere visite est relue (une visite vient peut-etre d'etre
  // saisie) ; hors ligne, le dernier etat charge sert.
  if (ruche.rucher_id && navigator.onLine) {
    try {
      const dernieres = await api(`/statistiques/dernieres-visites?rucher_id=${encodeURIComponent(ruche.rucher_id)}`);
      dernieres.forEach((visite) => state.latestVisitsByRuche.set(visite.ruche_id, visite));
    } catch {
      // Cache conserve.
    }
  }
  const last = state.latestVisitsByRuche.get(ruche.id);
  if (state.selectedRuche?.id !== ruche.id) return;
  const total = ruche.nombre_cadres ?? last?.nombre_cadres_total ?? defaultFrameCount(ruche.format_ruche);
  const brood = last?.nombre_cadres_couvain;
  if (dom.visiteCadresTotal.value === before[0]) {
    const delta = frameMovementDelta(dom.visiteCadresAction, dom.visiteCadresQuantite);
    dom.visiteCadresTotal.value = String(Math.max(0, total + delta));
    dom.visiteCadresTotal.dataset.frameDelta = String(delta);
  }
  if (dom.visiteCadresCouvain.value === before[1]) dom.visiteCadresCouvain.value = brood ?? "";
  setHint(dom.visiteFormHint, brood != null
    ? `Cadres pre-remplis d'apres la ruche et la visite du ${formatFrenchDate(last.date_visite)}.`
    : "Nombre de cadres pre-rempli d'apres la ruche.", "");
}

export function openNewVisitDialog() {
  state.pendingVisitTags = [];
  state.pendingTransvasement = null;
  renderPendingTransvasement();
  fillVisitCreateScope();
  hydrateVisitEquipmentFromRuche();
  dom.visiteCadresTotal.value = "";
  dom.visiteCadresCouvain.value = "";
  prefillVisitFramesFromRuche();
  renderVisitSelectedTags(state.selectedRucheTags);
  dom.visitCreateDialog.showModal();
}

// Un mouvement de cadres change le nombre total de cadres de la visite :
// +quantite pour un ajout, -quantite pour un retrait, rien pour une rotation.
// Le total garde l'ecart deja applique, pour qu'un changement d'action ou de
// quantite le corrige sans ecraser une saisie manuelle.
export function frameMovementDelta(actionSelect, quantityInput) {
  const label = (state.references.cadreActions.get(actionSelect.value) || "").toLowerCase();
  const quantity = Number(quantityInput.value || 1);
  if (label.startsWith("ajout")) return quantity;
  if (label.startsWith("retrait")) return -quantity;
  return 0;
}

export function applyFrameMovementToTotal(actionSelect, quantityInput, yearInput, totalInput) {
  if (actionSelect.value && !yearInput.value) yearInput.value = String(new Date().getFullYear());
  const delta = frameMovementDelta(actionSelect, quantityInput);
  const applied = Number(totalInput.dataset.frameDelta || 0);
  if (totalInput.value !== "") totalInput.value = String(Math.max(0, Number(totalInput.value) - applied + delta));
  totalInput.dataset.frameDelta = String(totalInput.value !== "" ? delta : 0);
}

export function visitFrameMovements() {
  if (!dom.visiteCadresAction.value || !dom.visiteCadresAnnee.value) return [];
  return [{
    ref_action_cadre_id: dom.visiteCadresAction.value,
    quantite: Number(dom.visiteCadresQuantite.value || 1),
    annee_cire: Number(dom.visiteCadresAnnee.value),
  }];
}

export function visitHausseMovements() {
  if (!dom.visiteHausse.checked || !dom.visiteHausseQuantite.value) return [];
  return [{ quantite_delta: Number(dom.visiteHausseQuantite.value), note: "Hausses notees en visite" }];
}

export async function saveVisite(event) {
  event.preventDefault();
  if (!state.selectedRuche || !state.authenticated) {
    setHint(dom.visiteFormHint, "Choisis le rucher puis la ruche concernee ci-dessus.", "error");
    return;
  }
  const body = {
    ruche_id: state.selectedRuche.id,
    visite_rucher_id: null,
    reine_vue: optionalBoolean(dom.visiteReineVue.value),
    presence_ponte: optionalBoolean(dom.visitePonte.value),
    etat_couvain: dom.visiteCouvain.value || null,
    nombre_cadres_couvain: optionalNumber(dom.visiteCadresCouvain.value),
    nombre_cadres_total: optionalNumber(dom.visiteCadresTotal.value),
    reserves_nourriture: dom.visiteReserves.value || null,
    note_ruche: optionalNumber(dom.visiteNote.value),
    corps_present: dom.visiteCorps.checked,
    hausse_presente: dom.visiteHausse.checked,
    partition_presente: dom.visitePartition.checked,
    grille_a_reine_presente: dom.visiteGrille.checked,
    nourrisseur_present: dom.visiteNourrisseur.checked,
    toit_present: dom.visiteToit.checked,
    plancher_present: dom.visitePlancher.checked,
    source_saisie: "manuelle",
    statut_validation: "valide",
    action_ids: [],
    interventions: [],
    mouvements_cadres: visitFrameMovements(),
    mouvements_hausses: visitHausseMovements(),
    tags_ajoutes: [...state.pendingVisitTags],
    ...(dom.visiteTypeRuche.value && dom.visiteTypeRuche.value !== dom.visiteTypeRuche.dataset.initial
      ? { ref_type_ruche_id: dom.visiteTypeRuche.value }
      : {}),
    // Heure de saisie : une visite synchronisee plus tard garde la bonne date.
    date_visite: new Date().toISOString(),
    ...(state.pendingTransvasement ? { transvasement: state.pendingTransvasement } : {})
  };
  if (state.mergeOperationId) {
    const operation = await getOfflineOperation(state.mergeOperationId);
    if (operation) {
      operation.payload = body;
      operation.client_base_updated_at = operation.server_visit?.updated_at || operation.client_base_updated_at;
      operation.status = "pending";
      await updateOfflineOperation(operation);
      state.mergeOperationId = null;
      resetVisiteForm();
      await syncOfflineVisits();
      setHint(dom.visiteFormHint, "Fusion mise en file de synchronisation.", "ok");
      return;
    }
  }
  if (Object.values(body).every((value) => value === null || value === "" || value === false || (Array.isArray(value) && value.length === 0))) {
    setHint(dom.visiteFormHint, "Renseigne au moins un indicateur de visite.", "error");
    return;
  }
  try {
    setStatus("Enregistrement de la visite...");
    if (!navigator.onLine) {
      await queueOfflineVisit(body);
      resetVisiteForm();
      dom.visitCreateDialog.close();
      setHint(dom.visiteFormHint, "Visite enregistree localement. Elle sera synchronisee au retour du reseau.", "ok");
      await updateSyncStatus("offline");
      setStatus("Visite locale en attente de synchronisation.");
      return;
    }
    const createdVisit = await api("/visites", { method: "POST", body });
    if (body.ref_type_ruche_id) await refreshSelectedRuche();
    const tagSuggestions = createdVisit.tag_suggestions || [];
    const warnings = createdVisit.avertissements || [];
    const tagRemovalSuggestions = createdVisit.tag_removal_suggestions || [];
    dom.visitCreateDialog.close();
    resetVisiteForm();
    setHint(dom.visiteFormHint, "Visite enregistree.", "ok");
    // On reste sur l onglet Visites, ruche selectionnee: l apiculteur enchaine
    // souvent plusieurs saisies de suite.
    const savedRuche = state.selectedRuche;
    if (savedRuche) {
      await selectRuche(savedRuche);
    }
    renderVisitTagSuggestions(dom.visitTagSuggestions, tagSuggestions, tagRemovalSuggestions);
    await loadVisitHistory();
    await loadDashboardIndicators();
    if (body.transvasement) await refreshDashboard();
    setStatus(warnings.length ? `Visite enregistree. ${warnings.join(" ")}` : "Visite enregistree.");
  } catch (error) {
    if (error.message === "Failed to fetch" || error.message === "Echec reseau") {
      await queueOfflineVisit(body);
      resetVisiteForm();
      dom.visitCreateDialog.close();
      setHint(dom.visiteFormHint, "Reseau indisponible: visite placee en file locale.", "ok");
      await updateSyncStatus("offline");
      setStatus("Visite locale en attente de synchronisation.");
      return;
    }
    setHint(dom.visiteFormHint, `Enregistrement impossible: ${error.message}`, "error");
    setStatus("Erreur visite.");
  }
}

export function renderVisites(visites) {
  dom.visitesList.innerHTML = "";
  if (!visites || visites.length === 0) {
    dom.visitesList.innerHTML = "<li>Aucune visite.</li>";
    return;
  }

  visites.forEach((visite) => {
    const li = document.createElement("li");
    li.className = "visit-history-item";
    const isHarvest = visite.type_evenement === "recolte";
    const status = isHarvest ? "Recolte" : visite.statut_validation === "valide" ? "Complete" : "Brouillon";
    const source = isHarvest ? `${Number(visite.poids_miel_kg || 0).toFixed(1)} kg` : visite.source_saisie === "ia_vocale" ? "IA" : "Manuelle";
    const location = visite.rucher_label ? `${visite.rucher_label} · ${visite.ruche_label}` : visite.ruche_label || visite.ruche_id.slice(0, 8);
    li.innerHTML = `<button class="visit-history-edit" type="button"><span class="visit-history-main"><strong>${escapeHtml(formatFrenchDate(visite.date_visite))}</strong><small>${escapeHtml(location)}</small></span><span class="visit-status ${isHarvest ? "is-harvest" : visite.statut_validation === "valide" ? "is-complete" : "is-draft"}">${escapeHtml(status)}</span><span class="visit-source">${escapeHtml(source)}</span></button>`;
    li.querySelector(".visit-history-edit").addEventListener("click", () => isHarvest ? openHarvestFromHistory(visite) : openVisitFromHistory(visite));
    dom.visitesList.appendChild(li);
  });
}

export async function openVisitFromHistory(visite) {
  try {
    const fullVisit = await api(`/visites/${encodeURIComponent(visite.id)}`);
    openVisitEditor({ ...fullVisit, ruche_label: visite.ruche_label });
  } catch (error) {
    setStatus(`Visite indisponible: ${error.message}`);
  }
}

export function openVisitEditor(visite) {
  state.selectedRuche = { id: visite.ruche_id, identifiant_personnalise: visite.ruche_label || visite.ruche_id.slice(0, 8) };
  dom.editVisitId.value = visite.id;
  dom.editVisitContext.textContent = `${visite.ruche_label || "Ruche"} · visite du ${formatFrenchDate(visite.date_visite)}`;
  dom.editVisitQueen.value = visite.reine_vue == null ? "" : String(visite.reine_vue);
  dom.editVisitPonte.value = visite.presence_ponte == null ? "" : String(visite.presence_ponte);
  dom.editVisitBrood.value = visite.etat_couvain || "";
  dom.editVisitReserves.value = visite.reserves_nourriture || "";
  dom.editVisitNote.value = visite.note_ruche ?? "";
  dom.editVisitBroodFrames.value = visite.nombre_cadres_couvain ?? "";
  dom.editVisitTotalFrames.value = visite.nombre_cadres_total ?? "";
  dom.editVisitCorps.checked = visite.corps_present === true;
  dom.editVisitHausse.checked = visite.hausse_presente === true;
  dom.editVisitPartition.checked = visite.partition_presente === true;
  dom.editVisitGrille.checked = visite.grille_a_reine_presente === true;
  dom.editVisitNourrisseur.checked = visite.nourrisseur_present === true;
  dom.editVisitToit.checked = visite.toit_present === true;
  dom.editVisitPlancher.checked = visite.plancher_present === true;
  dom.editVisitStatus.value = visite.statut_validation || "valide";
  const frameMovement = visite.mouvements_cadres?.find((item) => item.annee_cire);
  dom.editVisitCadresAction.value = frameMovement?.ref_action_cadre_id || "";
  dom.editVisitCadresQuantite.value = frameMovement?.quantite || 1;
  dom.editVisitCadresAnnee.value = frameMovement?.annee_cire || "";
  // Le total enregistre inclut deja ce mouvement.
  dom.editVisitTotalFrames.dataset.frameDelta = String(dom.editVisitTotalFrames.value !== "" ? frameMovementDelta(dom.editVisitCadresAction, dom.editVisitCadresQuantite) : 0);
  dom.editVisitHausseQuantite.disabled = !dom.editVisitHausse.checked;
  dom.editVisitHausseQuantite.value = "";
  setHint(dom.editVisitHint, "Les changements seront enregistres sur cette visite.", "");
  renderVisitSelectedTags(state.selectedRucheTags);
  loadRucheTags();
  dom.visitDialog.showModal();
}

export async function saveVisitEdit(event) {
  event.preventDefault();
  try {
    const updatedVisit = await api(`/visites/${encodeURIComponent(dom.editVisitId.value)}`, {
      method: "PATCH",
      body: {
        reine_vue: optionalSelectBoolean(dom.editVisitQueen.value),
        presence_ponte: optionalSelectBoolean(dom.editVisitPonte.value),
        etat_couvain: dom.editVisitBrood.value || null,
        reserves_nourriture: dom.editVisitReserves.value || null,
        note_ruche: optionalNumber(dom.editVisitNote.value),
        nombre_cadres_couvain: optionalNumber(dom.editVisitBroodFrames.value),
        nombre_cadres_total: optionalNumber(dom.editVisitTotalFrames.value),
        corps_present: dom.editVisitCorps.checked,
        hausse_presente: dom.editVisitHausse.checked,
        partition_presente: dom.editVisitPartition.checked,
        grille_a_reine_presente: dom.editVisitGrille.checked,
        nourrisseur_present: dom.editVisitNourrisseur.checked,
        toit_present: dom.editVisitToit.checked,
        plancher_present: dom.editVisitPlancher.checked,
        statut_validation: dom.editVisitStatus.value
        ,mouvements_cadres: editVisitFrameMovements()
        ,mouvements_hausses: dom.editVisitHausse.checked && dom.editVisitHausseQuantite.value ? [{ quantite_delta: Number(dom.editVisitHausseQuantite.value), note: "Hausses notees en visite" }] : undefined
      }
    });
    renderVisitTagSuggestions(dom.editVisitTagSuggestions, updatedVisit.tag_suggestions || [], updatedVisit.tag_removal_suggestions || []);
    dom.visitDialog.close();
    await loadVisitHistory();
    setStatus("Visite modifiee.");
  } catch (error) {
    setHint(dom.editVisitHint, `Modification impossible: ${error.message}`, "error");
  }
}

export async function loadVisitHistory() {
  if (!state.authenticated) return;
  const search = dom.visitesSearch.value.trim().toLowerCase();
  const eventType = dom.visitesTypeFilter.value;
  const status = dom.visitesStatusFilter.value;
  const source = dom.visitesSourceFilter.value;
  const startDate = dom.visitesStartDate.value;
  const endDate = dom.visitesEndDate.value;
  try {
    const params = new URLSearchParams({ limit: "100" });
    if (state.selectedRucher?.id) params.set("rucher_id", state.selectedRucher.id);
    if (state.selectedRuche?.id) params.set("ruche_id", state.selectedRuche.id);
    if (eventType) params.set("type_evenement", eventType);
    if (status) params.set("statut_validation", status);
    if (source) params.set("source_saisie", source);
    if (startDate) params.set("start_date", startDate);
    if (endDate) params.set("end_date", endDate);
    if (search) params.set("search", search);
    const history = await api(`/visites/historique?${params.toString()}`);
    const visits = history.visits;
    const unit = eventType === "recolte" ? "recolte(s)" : eventType === "visite" ? "visite(s)" : "evenement(s)";
    const suffix = history.total > visits.length ? ` · ${visits.length} plus recentes affichees.` : ".";
    dom.visitesHistoryHint.textContent = `${history.total} ${unit} correspondant aux filtres${suffix}`;
    renderVisites(visits);
  } catch (error) {
    dom.visitesHistoryHint.textContent = `Historique indisponible: ${error.message}`;
  }
}
