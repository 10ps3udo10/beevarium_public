import { api } from "./api.js";
import { refreshDashboard } from "./dashboard.js";
import { dom } from "./dom.js";
import { keepInPlace, materialOrigin, renderBulkActions, toggleRucheSelection } from "./ruches.js";
import { FORMAT_LABELS, state } from "./state.js";
import { escapeHtml, optionalNumber, setHint, setStatus } from "./utils.js";

export function renderAtelier(ruches, atelier) {
  dom.atelierRuchesList.innerHTML = ruches.length ? "" : "<li>Aucune ruche a l atelier.</li>";
  if (!ruches.length) {
    renderBulkActions();
    return;
  }
  ruches.forEach((ruche) => {
    const item = document.createElement("li");
    item.dataset.rucheId = ruche.id;
    const checkbox = document.createElement("input");
    checkbox.type = "checkbox";
    checkbox.checked = state.selectedRucheIds.has(ruche.id);
    item.classList.toggle("is-selected", checkbox.checked);
    checkbox.setAttribute("aria-label", `Selectionner ${ruche.identifiant_personnalise}`);
    checkbox.addEventListener("click", (event) => event.stopPropagation());
    checkbox.addEventListener("change", () => keepInPlace(item, () => {
      item.classList.toggle("is-selected", checkbox.checked);
      toggleRucheSelection(ruche.id, checkbox.checked);
    }));
    item.appendChild(checkbox);
    const button = document.createElement("button");
    button.textContent = ruche.identifiant_personnalise;
    button.addEventListener("click", () => keepInPlace(item, () => {
      checkbox.checked = !state.selectedRucheIds.has(ruche.id);
      item.classList.toggle("is-selected", checkbox.checked);
      toggleRucheSelection(ruche.id, checkbox.checked);
    }));
    item.appendChild(button);
    dom.atelierRuchesList.appendChild(item);
  });
  renderBulkActions();
}

export async function loadAtelier() {
  const atelier = await api("/atelier");
  const ruches = await api("/ruches?atelier_only=true");
  state.atelierRuches = ruches;
  renderAtelier(ruches, atelier);
  await loadMaterialStock();
}

export async function loadMaterialStock() {
  try {
    const materialRows = await api("/materiel-atelier");
    const stock = await api("/materiel-atelier/stats/stock-synthetique-par-type");
    const materialTypes = await api("/references/type-materiel");
    dom.stockTypeSelect.innerHTML = materialTypes
      .filter((item) => item.libelle.toLowerCase() !== "ruchette")
      .map((item) => `<option value="${escapeHtml(item.id)}">${escapeHtml(item.libelle)}</option>`)
      .join("");
    const displayStock = stock.filter((item) => item.libelle_type_materiel.toLowerCase() !== "ruchette");
    if (dom.dashboardMaterialStatus) {
      // Une reference = un couple type + format reellement possede (atelier ou en service).
      const references = displayStock.filter((item) => Number(item.quantite_stock_totale) > 0).length;
      dom.dashboardMaterialStatus.textContent = references ? String(references) : "Aucune";
    }
    dom.atelierStockList.innerHTML = displayStock.length ? "" : "<p class=\"hint\">Aucun type de materiel configure.</p>";
    displayStock.forEach((item) => {
      const card = document.createElement("article");
      card.className = "stock-card";
      const row = materialRows.find((material) => material.ref_type_materiel_id === item.ref_type_materiel_id && (material.format_materiel || null) === (item.format_materiel || null));
      const formatLabel = item.format_materiel ? FORMAT_LABELS[item.format_materiel] || item.format_materiel : "Non renseigne";
      card.innerHTML = `<strong class="stock-card-title"><span>${escapeHtml(item.libelle_type_materiel)}<span class="stock-title-separator"> · </span></span><small>${escapeHtml(formatLabel)}</small></strong><div class="stock-quantities"><span><b>${Number(item.quantite_en_service_totale)}</b> en service</span><span><b>${Number(item.quantite_atelier_totale)}</b> range</span>${Number(item.quantite_ruches_atelier_calculee) ? `<span><b>${Number(item.quantite_ruches_atelier_calculee)}</b> ruches atelier</span>` : ""}<span><b>${Number(item.quantite_stock_totale)}</b> total</span></div><button class="btn btn-ghost stock-edit" type="button">Modifier</button>`;
      card.querySelector(".stock-edit").addEventListener("click", () => openStockDialog(item, row));
      dom.atelierStockList.appendChild(card);
    });
  } catch (error) {
    dom.atelierStockList.innerHTML = `<p class="hint error">Stocks indisponibles: ${error.message}</p>`;
  }
}

export function openStockDialog(stock, material) {
  dom.stockDialogTitle.textContent = `Modifier ${stock.libelle_type_materiel}`;
  dom.stockMaterialId.value = material?.id || "";
  dom.stockTypeId.value = stock.ref_type_materiel_id;
  dom.stockTypeSelect.value = stock.ref_type_materiel_id;
  dom.stockTypeSelect.disabled = true;
  syncStockFormatOptions();
  dom.stockFormat.value = stock.format_materiel || "";
  // Changer le format ecraserait la ligne existante et creerait des doublons.
  dom.stockFormat.disabled = true;
  // Une seule ligne par type et format : la quantite affichee est le total range.
  dom.stockAtelierQuantity.value = stock.quantite_atelier_totale ?? material?.quantite_atelier ?? 0;
  dom.stockQuantityNote.textContent = "Nouvelle quantite totale rangee : utilise - et + pour retirer ou ajouter.";
  // Affiche le total reellement en service, celui que voit l utilisateur dans la liste.
  dom.stockServiceQuantity.value = stock.quantite_en_service_totale ?? 0;
  setHint(dom.stockFormHint, "Seule la quantite a l atelier est modifiable.", "");
  dom.stockDialog.showModal();
}

export function openNewMaterialDialog() {
  dom.stockMaterialId.value = "";
  dom.stockTypeId.value = "";
  dom.stockTypeSelect.disabled = false;
  dom.stockFormat.disabled = false;
  dom.stockFormat.value = "";
  dom.stockAtelierQuantity.value = "";
  dom.stockServiceQuantity.value = "0";
  dom.stockDialogTitle.textContent = "Ajouter du materiel";
  dom.stockQuantityNote.textContent = "Quantite a ajouter : si ce type et ce format existent deja, elle s ajoute au stock range.";
  syncStockFormatOptions();
  setHint(dom.stockFormHint, "", "");
  dom.stockDialog.showModal();
}

// Cadres et partitions suivent le format du cadre : une ruchette Dadant porte
// des cadres Dadant, le format Ruchette n'existe donc pas pour eux.
const FRAME_FORMAT_TYPES = new Set(["cadre", "partition"]);

export function syncStockFormatOptions() {
  const label = dom.stockTypeSelect.selectedOptions[0]?.textContent.trim().toLowerCase() || "";
  const ruchetteOption = dom.stockFormat.querySelector('option[value="ruchette"]');
  if (!ruchetteOption) return;
  ruchetteOption.disabled = FRAME_FORMAT_TYPES.has(label);
  if (ruchetteOption.disabled && dom.stockFormat.value === "ruchette") dom.stockFormat.value = "dadant";
}

export function stepStockQuantity(delta) {
  const current = Number(dom.stockAtelierQuantity.value) || 0;
  dom.stockAtelierQuantity.value = String(Math.max(0, current + delta));
}

export async function saveStock(event) {
  event.preventDefault();
  const atelierQuantity = Number(dom.stockAtelierQuantity.value);
  if (!Number.isInteger(atelierQuantity) || atelierQuantity < 0) {
    setHint(dom.stockFormHint, "Renseigne une quantite entiere positive ou nulle.", "error");
    return;
  }
  // La quantite en service est derivee des ruches: on ne l envoie plus.
  const body = { ref_type_materiel_id: dom.stockTypeSelect.value || dom.stockTypeId.value, modele: null, format_materiel: dom.stockFormat.value || null, quantite_atelier: atelierQuantity, quantite_en_service: 0 };
  try {
    const materialId = dom.stockMaterialId.value;
    await api(materialId ? `/materiel-atelier/${encodeURIComponent(materialId)}` : "/materiel-atelier", { method: materialId ? "PUT" : "POST", body });
    dom.stockDialog.close();
    await loadMaterialStock();
    setStatus("Stock mis a jour.");
  } catch (error) {
    setHint(dom.stockFormHint, `Mise a jour impossible: ${error.message}`, "error");
  }
}

export function openAtelierRucheCreator() {
  dom.atelierRucheForm.reset();
  dom.atelierRucheId.value = "";
  dom.atelierRucheDialogTitle.textContent = "Ajouter une ruche";
  dom.atelierRucheSubmit.textContent = "Ajouter a l'atelier";
  dom.atelierRucheOrigineMateriel.value = "achat";
  dom.atelierRucheOrigineMaterielWrap.hidden = false;
  setHint(dom.atelierRucheHint, "", "");
  dom.atelierRucheDialog.showModal();
  dom.atelierRucheIdentifiant.focus();
}

export function openAtelierRucheEditor() {
  const selected = [...state.selectedRucheIds]
    .map((id) => state.atelierRuches.find((ruche) => ruche.id === id))
    .filter(Boolean);
  if (selected.length !== 1) return;
  const ruche = selected[0];
  dom.atelierRucheId.value = ruche.id;
  dom.atelierRucheDialogTitle.textContent = `Modifier ${ruche.identifiant_personnalise}`;
  dom.atelierRucheSubmit.textContent = "Enregistrer la ruche";
  dom.atelierRucheIdentifiant.value = ruche.identifiant_personnalise || "";
  dom.atelierRucheFormat.value = ruche.format_ruche || "";
  dom.atelierRucheCadres.value = ruche.nombre_cadres ?? "";
  dom.atelierRucheHasCorps.checked = ruche.has_corps !== false;
  dom.atelierRucheHasPartition.checked = ruche.has_partition === true;
  dom.atelierRucheHasGrille.checked = ruche.has_grille_a_reine === true;
  dom.atelierRucheHasNourrisseur.checked = ruche.has_nourrisseur === true;
  dom.atelierRucheHasToit.checked = ruche.has_toit !== false;
  dom.atelierRucheHasPlancher.checked = ruche.has_plancher !== false;
  dom.atelierRucheOrigineMaterielWrap.hidden = true;
  setHint(dom.atelierRucheHint, "", "");
  dom.atelierRucheDialog.showModal();
  dom.atelierRucheIdentifiant.focus();
}

export async function saveAtelierRuche(event) {
  event.preventDefault();
  try {
    const rucheId = dom.atelierRucheId.value;
    const current = state.atelierRuches.find((ruche) => ruche.id === rucheId);
    const body = {
      identifiant_personnalise: dom.atelierRucheIdentifiant.value.trim(),
      rucher_id: null,
      atelier_id: current?.atelier_id || null,
      is_at_atelier: true,
      ref_type_ruche_id: current?.ref_type_ruche_id || null,
      ref_statut_ruche_id: current?.ref_statut_ruche_id || null,
      format_ruche: dom.atelierRucheFormat.value || null,
      nombre_cadres: optionalNumber(dom.atelierRucheCadres.value),
      reine_annee_marquage: current?.reine_annee_marquage || null,
      reine_race: current?.reine_race || null,
      reine_provenance: current?.reine_provenance || null,
      has_corps: dom.atelierRucheHasCorps.checked,
      has_hausse: current?.has_hausse === true,
      has_grille_a_reine: dom.atelierRucheHasGrille.checked,
      has_nourrisseur: dom.atelierRucheHasNourrisseur.checked,
      has_partition: dom.atelierRucheHasPartition.checked,
      has_toit: dom.atelierRucheHasToit.checked,
      has_plancher: dom.atelierRucheHasPlancher.checked,
    };
    if (!rucheId) Object.assign(body, materialOrigin(dom.atelierRucheOrigineMateriel, body));
    await api(rucheId ? `/ruches/${encodeURIComponent(rucheId)}` : "/ruches", { method: rucheId ? "PUT" : "POST", body });
    dom.atelierRucheDialog.close();
    state.selectedRucheIds.clear();
    await refreshDashboard();
    setStatus(rucheId ? "Ruche Atelier modifiee." : "Ruche ajoutee a l atelier.");
  } catch (error) {
    setHint(dom.atelierRucheHint, `Enregistrement impossible: ${error.message}`, "error");
  }
}
