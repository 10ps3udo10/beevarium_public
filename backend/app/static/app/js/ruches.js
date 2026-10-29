import { api } from "./api.js";
import { loadMaterialStock } from "./atelier.js";
import { refreshDashboard, renderDashboardContext } from "./dashboard.js";
import { dom } from "./dom.js";
import { setActiveTab } from "./navigation.js";
import { loadRucheHarvests } from "./recoltes.js";
import { renderQueenSummary } from "./reines.js";
import { state } from "./state.js";
import { loadAdvancedSynthesis, loadSynthese, setCurrentApiculturePeriod } from "./statistiques.js";
import { loadRucheTags } from "./tags.js";
import { escapeHtml, optionalNumber, setHint, setStatus } from "./utils.js";
import { renderVisites } from "./visites.js";

export function renderRucheReferenceOptions() {
  const populate = (select, values) => {
    const current = select.value;
    select.innerHTML = "<option value=\"\">Non renseigne</option>";
    values.forEach((label, id) => {
      const option = document.createElement("option");
      option.value = id;
      option.textContent = label;
      select.appendChild(option);
    });
    select.value = current;
  };
  populate(dom.rucheType, state.references.types);
  populate(dom.rucheStatus, state.references.statuses);
}

export function rucherHives(rucherId) {
  return state.allRuches.filter((ruche) => ruche.rucher_id === rucherId && !ruche.is_at_atelier);
}

export function renderRucheContext(ruche) {
  if (!ruche) {
    dom.rucheContextCard.hidden = true;
    return;
  }
  const location = ruche.is_at_atelier ? "Atelier" : state.selectedRucher?.nom || "Terrain";
  dom.rucheContextCard.hidden = false;
  dom.rucheContextTitle.textContent = ruche.identifiant_personnalise;
  dom.rucheContextStatus.textContent = location;
  dom.rucheContextSummary.innerHTML = [
    ["Statut", ruche.is_at_atelier ? "Inactive / atelier" : "Active / terrain"],
    ["Type", ruche.ref_type_ruche_id ? "Renseigne" : "Non renseigne"],
    ["Reine", ruche.reine_race || ruche.reine_annee_marquage ? `${ruche.reine_race || "Race non renseignee"}${ruche.reine_annee_marquage ? ` · ${ruche.reine_annee_marquage}` : ""}` : "Non renseignee"],
    ["Provenance", ruche.reine_provenance || "Non renseignee"]
  ].map(([label, value]) => `<div><strong>${escapeHtml(label)}</strong>${escapeHtml(value)}</div>`).join("");
}

export function renderRuches() {
  dom.ruchesList.innerHTML = "";
  const search = dom.rucheSearch.value.trim().toLowerCase();
  const ruches = sortRuches(
    state.ruches.filter((ruche) => !search || ruche.identifiant_personnalise.toLowerCase().includes(search))
  );
  if (ruches.length === 0) {
    dom.ruchesList.innerHTML = "<li>Aucune ruche dans ce rucher.</li>";
    renderBulkActions();
    return;
  }

  const table = document.createElement("table");
  table.className = "hives-table";
  const colonnes = [
    ["", null],
    ["Nom", "nom"],
    ["Statut", "statut"],
    ["Tags", null],
    ["Reine", "reine"],
    ["Cadres", "cadres"],
  ];
  const { cle, croissant } = state.rucheSort;
  const entetes = colonnes
    .map(([label, tri]) => {
      if (!tri) {
        return label ? `<th scope="col">${label}</th>` : `<th scope="col"><span class="sr-only">Selection</span></th>`;
      }
      const actif = cle === tri;
      const fleche = actif ? (croissant ? " ▲" : " ▼") : "";
      const ordre = actif ? (croissant ? "ascending" : "descending") : "none";
      return `<th scope="col" aria-sort="${ordre}"><button type="button" class="th-sort${actif ? " is-active" : ""}" data-sort="${tri}">${label}${fleche}</button></th>`;
    })
    .join("");
  table.innerHTML = `<thead><tr>${entetes}</tr></thead><tbody></tbody>`;
  const selectAll = document.createElement("input");
  selectAll.type = "checkbox";
  selectAll.setAttribute("aria-label", "Selectionner toutes les ruches visibles");
  selectAll.checked = ruches.length > 0 && ruches.every((ruche) => state.selectedRucheIds.has(ruche.id));
  selectAll.indeterminate = ruches.some((ruche) => state.selectedRucheIds.has(ruche.id)) && !selectAll.checked;
  selectAll.addEventListener("change", () => {
    ruches.forEach((ruche) => {
      if (selectAll.checked) state.selectedRucheIds.add(ruche.id);
      else state.selectedRucheIds.delete(ruche.id);
    });
    state.selectedRuche = selectAll.checked && ruches.length === 1 ? ruches[0] : null;
    renderRuches();
  });
  table.querySelector("th").replaceChildren(selectAll);
  table.querySelectorAll(".th-sort").forEach((bouton) => {
    bouton.addEventListener("click", () => trierRuchesPar(bouton.dataset.sort));
  });
  const body = table.querySelector("tbody");
  ruches.forEach((ruche) => {
    const row = document.createElement("tr");
    row.dataset.rucheId = ruche.id;
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = state.selectedRucheIds.has(ruche.id);
    checkbox.setAttribute("aria-label", `Selectionner ${ruche.identifiant_personnalise}`);
    checkbox.addEventListener("click", (event) => event.stopPropagation());
    checkbox.addEventListener("change", () => keepInPlace(row, () => toggleRucheSelection(ruche.id, checkbox.checked)));
    const selectionCell = document.createElement("td");
    selectionCell.appendChild(checkbox);
    row.appendChild(selectionCell);
    const button = document.createElement("button");
    button.className = "table-link";
    const statusLabel = ruche.is_at_atelier ? "Atelier" : state.references.statuses.get(ruche.ref_statut_ruche_id) || "Non renseigne";
    const queen = ruche.reine_race || ruche.reine_annee_marquage
      ? `Reine: ${ruche.reine_race || "renseignee"}${ruche.reine_annee_marquage ? `, ${ruche.reine_annee_marquage}` : ""}`
      : "Reine non renseignee";
    button.textContent = ruche.identifiant_personnalise;
    if (state.selectedRuche?.id === ruche.id) {
      button.classList.add("active");
    }
    const nameCell = document.createElement("td"); nameCell.appendChild(button); row.appendChild(nameCell);
    const statusCell = document.createElement("td"); statusCell.textContent = statusLabel; row.appendChild(statusCell);
    const tagsCell = document.createElement("td");
    tagsCell.className = "hive-tags-cell";
    const tagLabels = (ruche.tags || []).map((tag) => tag.libelle);
    tagsCell.textContent = tagLabels.slice(0, 3).join(" · ") || "-";
    if (tagLabels.length > 3) tagsCell.textContent += ` +${tagLabels.length - 3}`;
    row.appendChild(tagsCell);
    const queenCell = document.createElement("td"); queenCell.textContent = ruche.reine_race || ruche.reine_annee_marquage ? `${ruche.reine_race || "Inconnue"}${ruche.reine_annee_marquage ? ` · ${ruche.reine_annee_marquage}` : ""}` : "Inconnue"; row.appendChild(queenCell);
    const framesCell = document.createElement("td"); framesCell.textContent = cadresDe(ruche) || "-"; row.appendChild(framesCell);
    // Clic sur la ligne : ouvre cette ruche seule. La selection multiple et la
    // deselection passent par les cases a cocher : avant, ouvrir une autre
    // ruche l'ajoutait a la selection et masquait sa fiche.
    row.addEventListener("click", () => {
      state.selectedRucheIds.clear();
      toggleRucheSelection(ruche.id, true);
      renderRuches();
    });
    body.appendChild(row);
  });
  dom.ruchesList.appendChild(table);
  renderBulkActions();
}

export function cadresDe(ruche) {
  return state.latestVisitsByRuche.get(ruche.id)?.nombre_cadres_total ?? ruche.nombre_cadres ?? 0;
}

export function sortRuches(ruches) {
  const { cle, croissant } = state.rucheSort;
  const parNom = (left, right) =>
    left.identifiant_personnalise.localeCompare(right.identifiant_personnalise, "fr", { numeric: true });
  const libelle = (map, id) => map.get(id) || "";

  const valeurs = {
    nom: parNom,
    statut: (a, b) =>
      libelle(state.references.statuses, a.ref_statut_ruche_id)
        .localeCompare(libelle(state.references.statuses, b.ref_statut_ruche_id), "fr"),
    type: (a, b) =>
      libelle(state.references.types, a.ref_type_ruche_id)
        .localeCompare(libelle(state.references.types, b.ref_type_ruche_id), "fr"),
    // Sans annee connue, la ruche part en fin de liste plutot qu en tete.
    reine: (a, b) => (a.reine_annee_marquage || 9999) - (b.reine_annee_marquage || 9999),
    cadres: (a, b) => cadresDe(a) - cadresDe(b),
  };

  const comparateur = valeurs[cle] || parNom;
  return [...ruches].sort((a, b) => {
    const ordre = comparateur(a, b) || parNom(a, b);
    return croissant ? ordre : -ordre;
  });
}

export function trierRuchesPar(cle) {
  const actuel = state.rucheSort;
  state.rucheSort = { cle, croissant: actuel.cle === cle ? !actuel.croissant : true };
  renderRuches();
}

// Cocher une ruche affiche la barre de selection et la fiche au-dessus de la
// liste, puis ses tags arrivent du serveur un instant plus tard. Safari iOS ne
// compense pas ces decalages : la ligne fuit sous le doigt et un second appui
// coche la mauvaise ruche. On garde la ligne a sa place pendant le chargement,
// sauf si l'utilisateur touche ou fait defiler l'ecran entre-temps.
const KEEP_IN_PLACE_MS = 1200;
let keepInPlaceRun = 0;

export function keepInPlace(element, update) {
  const run = ++keepInPlaceRun;
  const key = element.dataset.rucheId;
  const anchorTop = element.getBoundingClientRect().top;
  const until = performance.now() + KEEP_IN_PLACE_MS;
  const stop = () => { if (keepInPlaceRun === run) keepInPlaceRun += 1; };
  window.addEventListener("touchstart", stop, { once: true, passive: true });
  window.addEventListener("wheel", stop, { once: true, passive: true });
  update();
  const hold = () => {
    if (keepInPlaceRun !== run) return;
    // Le tableau peut avoir ete reconstruit : on retrouve la meme ruche.
    const current = element.isConnected ? element : key ? document.querySelector(`[data-ruche-id="${CSS.escape(key)}"]`) : null;
    if (current) {
      const shift = current.getBoundingClientRect().top - anchorTop;
      if (Math.abs(shift) >= 1) window.scrollBy(0, shift);
    }
    if (performance.now() < until) requestAnimationFrame(hold);
    else stop();
  };
  hold();
}

export function toggleRucheSelection(rucheId, selected) {
  if (selected) state.selectedRucheIds.add(rucheId);
  else state.selectedRucheIds.delete(rucheId);
  const ruche = state.ruches.find((item) => item.id === rucheId) || state.atelierRuches.find((item) => item.id === rucheId);
  if (selected) {
    state.selectedRuche = ruche || null;
    if (ruche?.is_at_atelier) {
      state.selectedRucher = null;
    } else if (ruche?.rucher_id && ruche.rucher_id !== state.selectedRucher?.id) {
      state.selectedRucher = state.ruchers.find((item) => item.id === ruche.rucher_id) || state.selectedRucher;
    }
  }
  else if (state.selectedRuche?.id === rucheId) {
    state.selectedRuche = null;
    state.selectedRucheTags = [];
    renderRucheContext(null);
  }
  renderDashboardContext();
  renderBulkActions();
  if (selected && state.selectedRuche) {
    loadRucheHarvests();
    loadRucheTags();
  }
}

// Vers l'Atelier, deux choix : stocker la ruche montee telle quelle, ou la
// demonter (elements remis en stock, ruche archivee avec son historique).
export function renderBulkTargets() {
  dom.bulkMoveTarget.replaceChildren(
    new Option("Atelier : stocker telle quelle", "atelier"),
    new Option("Atelier : demonter (elements remis en stock)", "demonter"),
    ...state.ruchers.map((rucher) => new Option(rucher.nom, rucher.id)),
  );
}

export function renderBulkActions() {
  const selected = [...state.selectedRucheIds];
  const terrainIds = new Set(state.ruches.map((ruche) => ruche.id));
  const atelierIds = new Set(state.atelierRuches.map((ruche) => ruche.id));
  const terrainCount = selected.filter((id) => terrainIds.has(id)).length;
  const atelierCount = selected.filter((id) => atelierIds.has(id)).length;
  dom.rucherBulkActions.hidden = terrainCount === 0;
  dom.atelierBulkActions.hidden = atelierCount === 0;
  dom.btnEditAtelierSelected.hidden = atelierCount !== 1;
  if (terrainCount > 1) {
    dom.rucheContextCard.hidden = true;
    dom.rucheSecondaryActions.hidden = true;
  } else if (state.selectedRuche && terrainIds.has(state.selectedRuche.id)) {
    renderRucheContext(state.selectedRuche);
    dom.rucheSecondaryActions.hidden = false;
  } else if (terrainCount === 0 && (!state.selectedRuche || !atelierIds.has(state.selectedRuche.id))) {
    dom.rucheContextCard.hidden = true;
    dom.rucheSecondaryActions.hidden = true;
  }
  dom.rucherSelectedCount.textContent = String(terrainCount);
  dom.atelierSelectedCount.textContent = String(atelierCount);
  // Les destinations ne sont generees qu'a l'ouverture de la popup : les
  // regenerer ici remettait le choix sur "Atelier" pendant qu'elle etait ouverte.
}

export function selectedIdsForSource(sourceType) {
  const allowedIds = new Set((sourceType === "atelier" ? state.atelierRuches : state.ruches).map((ruche) => ruche.id));
  return [...state.selectedRucheIds].filter((id) => allowedIds.has(id));
}

export function openBulkMoveDialog(sourceLabel, sourceType) {
  const selected = selectedIdsForSource(sourceType);
  if (!selected.length) return;
  state.pendingBulkMoveIds = selected;
  renderBulkTargets();
  setHint(dom.bulkMoveHint, "", "");
  dom.bulkMoveSummary.textContent = `${selected.length} ruche(s) selectionnee(s) depuis ${sourceLabel}.`;
  dom.bulkMoveDialog.showModal();
  dom.bulkMoveTarget.focus();
}

export async function submitBulkMove(event) {
  event.preventDefault();
  const selected = state.pendingBulkMoveIds;
  if (!selected.length) return;
  const destination = dom.bulkMoveTarget.value;
  if (destination === "demonter" && !window.confirm(`Demonter ${selected.length} ruche(s) ? Les elements reviennent dans le stock de l'Atelier, la reine active est terminee et la ruche sort de la liste. Ses visites et recoltes restent dans l'historique.`)) {
    return;
  }
  try {
    if (destination === "demonter") {
      await api("/ruches/demontage", { method: "POST", body: { ruche_ids: selected } });
    } else {
      await api("/ruches/move", { method: "POST", body: { ruche_ids: selected, target_rucher_id: destination === "atelier" ? null : destination, move_to_atelier: destination === "atelier" } });
    }
    dom.bulkMoveDialog.close();
    state.pendingBulkMoveIds = [];
    state.selectedRucheIds.clear();
    if (destination === "demonter" && selected.includes(state.selectedRuche?.id)) state.selectedRuche = null;
    await refreshDashboard();
    setStatus(destination === "demonter" ? `${selected.length} ruche(s) demontee(s), elements remis en stock.` : `${selected.length} ruche(s) deplacee(s).`);
  } catch (error) {
    setHint(dom.bulkMoveHint, `Deplacement impossible: ${error.message}`, "error");
  }
}

export function resetRucheForm() {
  dom.rucheForm.reset();
  if (dom.rucheDialog.open) dom.rucheDialog.close();
  dom.rucheId.value = "";
  dom.rucheFormTitle.textContent = "Ajouter une ruche";
  setHint(dom.rucheFormHint, "", "");
}

export function openRucheCreator() {
  // Le formulaire sert aussi a l edition: sans remise a zero, il conserve les
  // valeurs de la ruche precedemment ouverte.
  dom.rucheForm.reset();
  dom.rucheId.value = "";
  dom.rucheType.value = "";
  dom.rucheStatus.value = findReferenceIdByLabel(state.references.statuses, "Active") || "";
  dom.rucheFormat.value = "";
  dom.rucheReineRace.value = "";
  dom.rucheReineProvenance.value = "";
  dom.rucheReineAnnee.value = String(new Date().getFullYear());
  dom.rucheReineDate.value = new Date().toISOString().slice(0, 10);
  dom.rucheHasCorps.checked = true;
  dom.rucheHasPartition.checked = false;
  dom.rucheHasToit.checked = true;
  dom.rucheHasPlancher.checked = true;
  dom.rucheFormTitle.textContent = "Ajouter une ruche";
  dom.rucheOrigineMateriel.value = "achat";
  dom.rucheOrigineMaterielWrap.hidden = false;
  setHint(dom.rucheFormHint, "", "");
  dom.rucheSecondaryActions.hidden = false;
  dom.rucheDialog.showModal();
  dom.rucheIdentifiant.focus();
}

// Creation d'une ruche : `achat` (nouveau materiel) ne touche pas au stock range ; `stock`
// retire les elements coches et les cadres du stock du format de la ruche.
export function materialOrigin(select, body) {
  if (select.value !== "stock") return { origine_materiel: "achat" };
  const elements = [
    ["plancher", body.has_plancher],
    ["corps", body.has_corps],
    ["toit", body.has_toit],
    ["partition", body.has_partition],
    ["grille", body.has_grille_a_reine],
    ["nourrisseur", body.has_nourrisseur],
  ].filter(([, present]) => present).map(([element]) => element);
  if (body.nombre_cadres !== 0) elements.push("cadres");
  return { origine_materiel: "stock", elements_stock: elements };
}

export function findReferenceIdByLabel(referenceMap, expectedLabel) {
  const normalized = expectedLabel.toLowerCase();
  return [...referenceMap.entries()].find(([, label]) => label.toLowerCase() === normalized)?.[0] || "";
}

export function editRuche(ruche) {
  dom.rucheId.value = ruche.id;
  dom.rucheIdentifiant.value = ruche.identifiant_personnalise || "";
  dom.rucheType.value = ruche.ref_type_ruche_id || "";
  dom.rucheStatus.value = ruche.ref_statut_ruche_id || "";
  dom.rucheCadres.value = ruche.nombre_cadres ?? "";
  dom.rucheFormat.value = ruche.format_ruche || "";
  dom.rucheReineAnnee.value = ruche.reine_annee_marquage || "";
  dom.rucheReineDate.value = ruche.reine_date_mise_en_place || "";
  dom.rucheReineRace.value = ruche.reine_race || "";
  dom.rucheReineProvenance.value = ruche.reine_provenance || "";
  dom.rucheHasCorps.checked = ruche.has_corps !== false;
  dom.rucheHasHausse.checked = ruche.has_hausse === true;
  dom.rucheHasPartition.checked = ruche.has_partition === true;
  dom.rucheHasGrille.checked = ruche.has_grille_a_reine === true;
  dom.rucheHasNourrisseur.checked = ruche.has_nourrisseur === true;
  dom.rucheHasToit.checked = ruche.has_toit !== false;
  dom.rucheHasPlancher.checked = ruche.has_plancher !== false;
  dom.rucheFormTitle.textContent = `Modifier ${ruche.identifiant_personnalise}`;
  dom.rucheOrigineMaterielWrap.hidden = true;
  setHint(dom.rucheFormHint, "", "");
  dom.rucheDialog.showModal();
  dom.rucheIdentifiant.focus();
}

export async function saveRuche(event) {
  event.preventDefault();
  if (!state.selectedRucher || !state.authenticated) {
    setHint(dom.rucheFormHint, "Selectionne un rucher et connecte-toi d abord.", "error");
    return;
  }
  const rucheId = dom.rucheId.value;
  const body = {
    identifiant_personnalise: dom.rucheIdentifiant.value.trim(),
    ref_type_ruche_id: dom.rucheType.value || null,
    ref_statut_ruche_id: dom.rucheStatus.value || null,
    rucher_id: state.selectedRucher.id,
    is_at_atelier: false,
    nombre_cadres: optionalNumber(dom.rucheCadres.value),
    format_ruche: dom.rucheFormat.value || null,
    reine_annee_marquage: optionalNumber(dom.rucheReineAnnee.value),
    // L'age de la reine se compte depuis ce jour ; l'annee suit la date.
    reine_date_mise_en_place: dom.rucheReineDate.value || null,
    reine_race: dom.rucheReineRace.value.trim() || null,
    reine_provenance: dom.rucheReineProvenance.value.trim() || null
    ,has_corps: dom.rucheHasCorps.checked
    ,has_hausse: dom.rucheHasHausse.checked
    ,has_partition: dom.rucheHasPartition.checked
    ,has_grille_a_reine: dom.rucheHasGrille.checked
    ,has_nourrisseur: dom.rucheHasNourrisseur.checked
    ,has_toit: dom.rucheHasToit.checked
    ,has_plancher: dom.rucheHasPlancher.checked
  };
  if (!rucheId) Object.assign(body, materialOrigin(dom.rucheOrigineMateriel, body));
  try {
  dom.queenDialog.close();
    setStatus("Enregistrement de la ruche...");
    await api(rucheId ? `/ruches/${encodeURIComponent(rucheId)}` : "/ruches", {
      method: rucheId ? "PUT" : "POST",
      body
    });
    setHint(dom.rucheFormHint, rucheId ? "Ruche modifiee." : "Ruche creee.", "ok");
    resetRucheForm();
    await refreshDashboard();
    if (state.onboardingFlowActive) setActiveTab("dashboard");
    setStatus("Ruche enregistree.");
  } catch (error) {
    setHint(dom.rucheFormHint, `Enregistrement impossible: ${error.message}`, "error");
    setStatus("Erreur ruche.");
  }
}

export async function selectRuche(ruche) {
  state.selectedRuche = ruche;
  renderRucheContext(ruche);
  renderDashboardContext();
  renderRuches();
  setStatus("Chargement des visites...");
  try {
    const visites = await api(`/visites?ruche_id=${encodeURIComponent(ruche.id)}`);
    const reines = await api(`/ruches/${encodeURIComponent(ruche.id)}/reines`);
    renderQueenSummary(reines);
    renderVisites(visites);
    await loadRucheHarvests();
    await loadRucheTags();
    setCurrentApiculturePeriod();
    await loadSynthese();
    await loadAdvancedSynthesis();
    setStatus("Visites chargees.");
  } catch (error) {
    setStatus(`Erreur visites: ${error.message}`);
  }
}

export async function refreshSelectedRuche() {
  if (!state.selectedRuche) return;
  const refreshed = await api(`/ruches/${encodeURIComponent(state.selectedRuche.id)}`);
  state.selectedRuche = { ...state.selectedRuche, ...refreshed };
  const update = (ruche) => ruche.id === refreshed.id ? { ...ruche, ...refreshed } : ruche;
  state.ruches = state.ruches.map(update);
  state.allRuches = state.allRuches.map(update);
  state.atelierRuches = state.atelierRuches.map(update);
  renderRucheContext(state.selectedRuche);
  renderRuches();
  await loadMaterialStock();
}
