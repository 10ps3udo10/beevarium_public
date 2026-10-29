// Creation de ruches en nombre : creation rapide (gratuite), modeles de ruche
// et import de tableur (Premium). L'API cree tout ou rien.
import { api } from "./api.js";
import { refreshDashboard } from "./dashboard.js";
import { dom } from "./dom.js";
import { setActiveTab } from "./navigation.js";
import { selectRucher } from "./ruchers.js";
import { FORMAT_LABELS, state } from "./state.js";
import { defaultFrameCount, escapeHtml, setHint, setStatus } from "./utils.js";

const ELEMENT_INPUTS = {
  has_corps: "quickHasCorps",
  has_toit: "quickHasToit",
  has_plancher: "quickHasPlancher",
  has_grille_a_reine: "quickHasGrille",
  has_nourrisseur: "quickHasNourrisseur",
  has_hausse: "quickHasHausse",
};
const MAX_QUICK_HIVES = 200;
const MAX_IMPORT_BYTES = 700 * 1024;

function typeOptions(selected) {
  const options = [...state.references.types.entries()]
    .sort((a, b) => a[1].localeCompare(b[1], "fr"))
    .map(([id, label]) => `<option value="${escapeHtml(id)}"${id === selected ? " selected" : ""}>${escapeHtml(label)}</option>`)
    .join("");
  return `<option value="">Non renseigne</option>${options}`;
}

function defaultTypeId() {
  return [...state.references.types.entries()].find(([, label]) => label.toLowerCase() === "production")?.[0] || "";
}

function formatOptions(selected) {
  return Object.entries(FORMAT_LABELS)
    .map(([value, label]) => `<option value="${value}"${value === selected ? " selected" : ""}>${label}</option>`)
    .join("");
}

// Fonctions Premium visibles mais grisees pour un compte gratuit.
export function renderPremiumLocks() {
  const locked = !state.isPremium;
  dom.quickTemplate.disabled = locked;
  dom.quickTemplateWrap.classList.toggle("is-premium-locked", locked);
  dom.btnQuickSaveTemplate.disabled = locked;
  dom.btnImportOpen.disabled = locked;
  const tip = locked ? "Reserve aux comptes Premium" : "";
  [dom.quickTemplateWrap, dom.btnQuickSaveTemplate, dom.btnImportOpen].forEach((element) => { element.title = tip; });
}

// Numero suivant libre pour un prefixe, d'apres les ruches deja creees.
function nextNumber(prefix) {
  const pattern = new RegExp(`^${prefix.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}(\\d+)$`, "i");
  const numbers = state.allRuches
    .map((ruche) => pattern.exec(ruche.identifiant_personnalise || ""))
    .filter(Boolean)
    .map((match) => Number(match[1]));
  return numbers.length ? Math.max(...numbers) + 1 : 1;
}

function quickParams() {
  return {
    count: Math.min(MAX_QUICK_HIVES, Math.max(1, Number(dom.quickCount.value) || 1)),
    prefix: dom.quickPrefix.value.trim(),
    start: Math.max(0, Number(dom.quickStart.value) || 0),
    format: dom.quickFormat.value,
  };
}

// L'apercu suit les reglages ; une ligne modifiee a la main est conservee.
function buildQuickRows() {
  const { count, prefix, start, format } = quickParams();
  const type = dom.quickType.value;
  const width = Math.max(2, String(start + count - 1).length);
  const rows = [];
  for (let index = 0; index < count; index += 1) {
    const previous = state.quickRows[index];
    const generated = `${prefix}${String(start + index).padStart(width, "0")}`;
    rows.push({
      identifiant: previous?.identifiantEdited ? previous.identifiant : generated,
      identifiantEdited: Boolean(previous?.identifiantEdited),
      type: previous?.typeEdited ? previous.type : type,
      typeEdited: Boolean(previous?.typeEdited),
      format: previous?.formatEdited ? previous.format : format,
      formatEdited: Boolean(previous?.formatEdited),
    });
  }
  state.quickRows = rows;
}

// Mise a jour sur place quand le nombre de lignes ne change pas : reconstruire
// le tableau sous le curseur ferait perdre la saisie en cours.
function renderQuickPreview() {
  buildQuickRows();
  const existing = dom.quickPreviewBody.querySelectorAll("tr");
  if (existing.length === state.quickRows.length) {
    state.quickRows.forEach((row, index) => {
      const identifiant = dom.quickPreviewBody.querySelector(`[data-quick-row="${index}"][data-quick-field="identifiant"]`);
      const format = dom.quickPreviewBody.querySelector(`[data-quick-row="${index}"][data-quick-field="format"]`);
      if (identifiant && identifiant.value !== row.identifiant) identifiant.value = row.identifiant;
      const type = dom.quickPreviewBody.querySelector(`[data-quick-row="${index}"][data-quick-field="type"]`);
      if (type && type.value !== row.type) type.value = row.type;
      if (format && format.value !== row.format) format.value = row.format;
    });
    updateQuickCounts();
    return;
  }
  dom.quickPreviewBody.innerHTML = state.quickRows.map((row, index) => `<tr>
    <td><input data-quick-row="${index}" data-quick-field="identifiant" value="${escapeHtml(row.identifiant)}" maxlength="100" aria-label="Identifiant de la ruche ${index + 1}"></td>
    <td><select data-quick-row="${index}" data-quick-field="type" aria-label="Type de la ruche ${index + 1}">${typeOptions(row.type)}</select></td>
    <td><select data-quick-row="${index}" data-quick-field="format" aria-label="Format de la ruche ${index + 1}">${formatOptions(row.format)}</select></td>
  </tr>`).join("");
  updateQuickCounts();
}

function updateQuickCounts() {
  dom.quickPreviewTitle.textContent = `Apercu : ${state.quickRows.length} ruche(s)`;
  dom.btnQuickSubmit.textContent = `Creer ${state.quickRows.length} ruche(s)`;
}

function applyElements(source) {
  Object.entries(ELEMENT_INPUTS).forEach(([field, key]) => { dom[key].checked = Boolean(source[field]); });
}

function quickElements() {
  return Object.fromEntries(Object.entries(ELEMENT_INPUTS).map(([field, key]) => [field, dom[key].checked]));
}

async function loadModeles() {
  if (!state.isPremium) {
    state.modelesRuche = [];
  } else {
    try {
      state.modelesRuche = await api("/modeles-ruche");
    } catch {
      state.modelesRuche = [];
    }
  }
  dom.quickTemplate.innerHTML = `<option value="">Aucun modele</option>${state.modelesRuche.map((modele) => `<option value="${escapeHtml(modele.id)}">${escapeHtml(modele.nom)}</option>`).join("")}`;
}

// `rucher` absent : nouveau rucher (prise en main, onglet Ruchers) ;
// sinon ajout de ruches a ce rucher.
export async function openQuickCreate(rucher = null) {
  state.quickTargetRucher = rucher;
  state.quickRows = [];
  dom.quickPreviewBody.innerHTML = "";
  dom.quickCreateTitle.textContent = rucher ? `Ajouter plusieurs ruches a ${rucher.nom}` : "Creer un rucher et ses ruches";
  dom.quickRucherFields.hidden = Boolean(rucher);
  dom.quickRucherTarget.hidden = !rucher;
  dom.quickRucherTarget.textContent = rucher ? `Rucher : ${rucher.nom}` : "";
  dom.quickRucherName.value = "";
  dom.quickType.innerHTML = typeOptions(defaultTypeId());
  dom.quickFormat.innerHTML = formatOptions("dadant");
  dom.quickFrames.value = String(defaultFrameCount("dadant"));
  dom.quickCount.value = rucher ? "5" : "10";
  dom.quickPrefix.value = "R";
  dom.quickStart.value = String(nextNumber("R"));
  applyElements({ has_corps: true, has_toit: true, has_plancher: true });
  setHint(dom.quickCreateHint, "", "");
  renderPremiumLocks();
  await loadModeles();
  renderQuickPreview();
  dom.quickCreateDialog.showModal();
  (rucher ? dom.quickCount : dom.quickRucherName).focus();
}

function applyTemplate() {
  const modele = state.modelesRuche.find((item) => item.id === dom.quickTemplate.value);
  if (!modele) return;
  if (modele.format_ruche) dom.quickFormat.value = modele.format_ruche;
  if (modele.ref_type_ruche_id) dom.quickType.value = modele.ref_type_ruche_id;
  dom.quickFrames.value = modele.nombre_cadres ?? defaultFrameCount(dom.quickFormat.value);
  applyElements(modele);
  state.quickRows.forEach((row) => { row.formatEdited = false; row.typeEdited = false; });
  renderQuickPreview();
}

async function saveTemplate() {
  if (!state.isPremium) return;
  const nom = window.prompt("Nom du modele (ex. Dadant production) :");
  if (!nom || !nom.trim()) return;
  try {
    const modele = await api("/modeles-ruche", {
      method: "POST",
      body: { nom: nom.trim(), ref_type_ruche_id: dom.quickType.value || null, format_ruche: dom.quickFormat.value, nombre_cadres: Number(dom.quickFrames.value) || null, ...quickElements() },
    });
    await loadModeles();
    dom.quickTemplate.value = modele.id;
    setHint(dom.quickCreateHint, `Modele "${modele.nom}" enregistre.`, "ok");
  } catch (error) {
    setHint(dom.quickCreateHint, `Modele impossible : ${error.message}`, "error");
  }
}

async function submitQuickCreate(event) {
  event.preventDefault();
  const target = state.quickTargetRucher;
  const name = dom.quickRucherName.value.trim();
  if (!target && !name) {
    setHint(dom.quickCreateHint, "Donne un nom au rucher.", "error");
    dom.quickRucherName.focus();
    return;
  }
  const empty = state.quickRows.findIndex((row) => !row.identifiant.trim());
  if (empty >= 0) {
    setHint(dom.quickCreateHint, `Ligne ${empty + 1} : identifiant vide.`, "error");
    return;
  }
  const frames = dom.quickFrames.value === "" ? null : Number(dom.quickFrames.value);
  const elements = quickElements();
  const ruches = state.quickRows.map((row) => ({
    identifiant_personnalise: row.identifiant.trim(),
    ref_type_ruche_id: row.type || null,
    format_ruche: row.format,
    // Cadres du reglage pour le format choisi ; une ligne d'un autre format
    // prend la capacite par defaut de son format.
    nombre_cadres: row.format === dom.quickFormat.value ? frames : defaultFrameCount(row.format),
    ...elements,
  }));
  const body = target
    ? { rucher_id: target.id, ruches }
    : { rucher: { nom: name, type_terrain: dom.quickRucherType.value, statut_activite: "actif", statut_peuplement: "peuple" }, ruches };
  dom.btnQuickSubmit.disabled = true;
  setHint(dom.quickCreateHint, "Creation en cours...", "");
  try {
    const result = await api("/ruchers/creation-rapide", { method: "POST", body });
    dom.quickCreateDialog.close();
    await refreshDashboard();
    if (state.onboardingFlowActive) {
      setActiveTab("dashboard");
    } else {
      setActiveTab("ruchers");
      const rucher = state.ruchers.find((item) => item.id === result.rucher.id) || result.rucher;
      await selectRucher(rucher);
    }
    setStatus(`${result.ruches_creees} ruche(s) creee(s) dans ${result.rucher.nom}. Completez chaque ruche quand vous le souhaitez.`);
  } catch (error) {
    setHint(dom.quickCreateHint, `Creation impossible : ${error.message}`, "error");
  } finally {
    dom.btnQuickSubmit.disabled = false;
  }
}

// --- Import de tableur (Premium) ------------------------------------------------

export function openImport() {
  if (!state.isPremium) return;
  state.importFile = null;
  state.importLines = [];
  dom.importFile.value = "";
  dom.importMapping.hidden = true;
  dom.importPreview.hidden = true;
  dom.btnImportSubmit.disabled = true;
  dom.btnImportSubmit.textContent = "Importer";
  setHint(dom.importHint, "", "");
  dom.importDialog.showModal();
}

function downloadTemplate() {
  const lines = [
    "Rucher;Ruche;Type de ruche;Format;Cadres",
    "Les Tilleuls;R01;Production;Dadant;10",
    "Les Tilleuls;R02;Production;Dadant;10",
    "Coteau Sud;E01;Essaim;Ruchette;6",
  ];
  // BOM : Excel ouvre alors le fichier en UTF-8 avec les accents.
  const blob = new Blob([`﻿${lines.join("\r\n")}\r\n`], { type: "text/csv;charset=utf-8" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "beevarium-modele-import.csv";
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(link.href), 1000);
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result).split(",", 2)[1] || "");
    reader.onerror = () => reject(new Error("lecture du fichier impossible"));
    reader.readAsDataURL(file);
  });
}

async function analyseImport(correspondance = null) {
  if (!state.importFile) return;
  setHint(dom.importHint, "Analyse du fichier...", "");
  try {
    const result = await api("/import/ruches/analyse", {
      method: "POST",
      body: { nom_fichier: state.importFile.nom, contenu_base64: state.importFile.base64, ...(correspondance ? { correspondance } : {}) },
    });
    renderMapping(result.colonnes, result.correspondance);
    renderImportResult(result);
  } catch (error) {
    dom.importPreview.hidden = true;
    dom.btnImportSubmit.disabled = true;
    setHint(dom.importHint, `Analyse impossible : ${error.message}`, "error");
  }
}

async function onImportFile() {
  const file = dom.importFile.files?.[0];
  if (!file) return;
  if (file.size > MAX_IMPORT_BYTES) {
    setHint(dom.importHint, "Fichier trop lourd (700 Ko au plus) : retirer les colonnes inutiles ou decouper le fichier.", "error");
    return;
  }
  try {
    state.importFile = { nom: file.name, base64: await readFileAsBase64(file) };
  } catch (error) {
    setHint(dom.importHint, `Lecture impossible : ${error.message}`, "error");
    return;
  }
  await analyseImport();
}

function mappingSelects() {
  return [...dom.importMapping.querySelectorAll("select[data-field]")];
}

function renderMapping(columns, mapping) {
  mappingSelects().forEach((select) => {
    const field = select.dataset.field;
    select.innerHTML = `<option value="">(aucune colonne)</option>${columns.filter(Boolean).map((column) => `<option value="${escapeHtml(column)}">${escapeHtml(column)}</option>`).join("")}`;
    select.value = mapping[field] || "";
  });
  dom.importMapping.hidden = false;
}

function renderImportResult(result) {
  state.importLines = result.lignes;
  const nouveaux = result.ruchers_a_creer.length ? ` Ruchers crees : ${result.ruchers_a_creer.join(", ")}.` : "";
  dom.importSummary.textContent = result.nb_erreurs
    ? `${result.lignes.length} ligne(s), ${result.nb_erreurs} en erreur : corrige-les ici ou dans le fichier.`
    : `${result.lignes.length} ruche(s) pretes a importer.${nouveaux}`;
  dom.importPreviewBody.innerHTML = result.lignes.map((line, index) => {
    const cell = (field, value, size) => `<input data-import-row="${index}" data-import-field="${field}" value="${escapeHtml(value ?? "")}" maxlength="${size}" aria-label="${field} ligne ${line.numero}">`;
    const statusCell = line.erreurs.length
      ? `<span class="import-error">${line.erreurs.map(escapeHtml).join(" ; ")}</span>`
      : `<span class="import-ok">OK${line.rucher_existant ? "" : " (nouveau rucher)"}</span>`;
    return `<tr class="${line.erreurs.length ? "has-error" : ""}"><td>${line.numero}</td><td>${cell("rucher", line.rucher, 150)}</td><td>${cell("identifiant", line.identifiant, 100)}</td><td>${cell("type_ruche", line.type_ruche, 100)}</td><td>${cell("format_ruche", line.format_ruche, 30)}</td><td>${cell("nombre_cadres", line.nombre_cadres, 10)}</td><td>${statusCell}</td></tr>`;
  }).join("");
  dom.importPreview.hidden = false;
  dom.btnImportSubmit.disabled = false;
  dom.btnImportSubmit.textContent = result.nb_erreurs ? "Reverifier" : `Importer ${result.lignes.length} ruche(s)`;
  setHint(dom.importHint, "", "");
}

function importPayload() {
  return state.importLines.map((line) => ({
    rucher: line.rucher || "",
    identifiant: line.identifiant || "",
    type_ruche: line.type_ruche || null,
    format_ruche: line.format_ruche || null,
    nombre_cadres: line.nombre_cadres || null,
  }));
}

// Toujours reverifie avant de creer : l'apercu a pu etre corrige.
async function submitImport(event) {
  event.preventDefault();
  if (!state.importLines.length) return;
  dom.btnImportSubmit.disabled = true;
  try {
    const verification = await api("/import/ruches/verifier", { method: "POST", body: { lignes: importPayload() } });
    if (verification.nb_erreurs) {
      renderImportResult(verification);
      return;
    }
    setHint(dom.importHint, "Import en cours...", "");
    const result = await api("/import/ruches", { method: "POST", body: { lignes: importPayload() } });
    dom.importDialog.close();
    await refreshDashboard();
    setActiveTab("ruchers");
    setStatus(`${result.ruches_creees} ruche(s) importee(s)${result.ruchers_crees ? `, ${result.ruchers_crees} rucher(s) cree(s)` : ""}.`);
  } catch (error) {
    setHint(dom.importHint, `Import impossible : ${error.message}`, "error");
  } finally {
    dom.btnImportSubmit.disabled = false;
  }
}

export function bindCreationEvents() {
  dom.btnQuickCreate.addEventListener("click", () => openQuickCreate(null));
  dom.btnQuickAddHives.addEventListener("click", () => { if (state.selectedRucher) openQuickCreate(state.selectedRucher); });
  dom.btnCloseQuickCreate.addEventListener("click", () => dom.quickCreateDialog.close());
  dom.quickCreateForm.addEventListener("submit", submitQuickCreate);
  dom.quickTemplate.addEventListener("change", applyTemplate);
  dom.btnQuickSaveTemplate.addEventListener("click", saveTemplate);
  dom.quickType.addEventListener("change", renderQuickPreview);
  dom.quickFormat.addEventListener("change", () => {
    dom.quickFrames.value = String(defaultFrameCount(dom.quickFormat.value));
    renderQuickPreview();
  });
  dom.quickPrefix.addEventListener("input", () => {
    dom.quickStart.value = String(nextNumber(dom.quickPrefix.value.trim()));
    state.quickRows.forEach((row) => { row.identifiantEdited = false; });
    renderQuickPreview();
  });
  [dom.quickCount, dom.quickStart].forEach((input) => input.addEventListener("input", renderQuickPreview));
  dom.quickPreviewBody.addEventListener("input", (event) => {
    const index = Number(event.target.dataset.quickRow);
    const row = state.quickRows[index];
    if (!row) return;
    if (event.target.dataset.quickField === "identifiant") {
      row.identifiant = event.target.value;
      row.identifiantEdited = true;
    } else if (event.target.dataset.quickField === "type") {
      row.type = event.target.value;
      row.typeEdited = true;
    } else {
      row.format = event.target.value;
      row.formatEdited = true;
    }
  });
  dom.btnImportOpen.addEventListener("click", openImport);
  dom.btnCloseImport.addEventListener("click", () => dom.importDialog.close());
  dom.btnImportTemplate.addEventListener("click", downloadTemplate);
  dom.importFile.addEventListener("change", onImportFile);
  dom.importMapping.addEventListener("change", () => {
    const correspondance = Object.fromEntries(mappingSelects().map((select) => [select.dataset.field, select.value || null]));
    analyseImport(correspondance);
  });
  dom.importPreviewBody.addEventListener("input", (event) => {
    const line = state.importLines[Number(event.target.dataset.importRow)];
    if (!line) return;
    line[event.target.dataset.importField] = event.target.value;
    dom.btnImportSubmit.textContent = "Reverifier et importer";
  });
  dom.importForm.addEventListener("submit", submitImport);
}
