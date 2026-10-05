import { api } from "./api.js";
import { dom } from "./dom.js";
import { renderHoneyBreakdown } from "./recoltes.js";
import { queenTenure } from "./reines.js";
import { applyScopeRuche } from "./scope.js";
import { FORMAT_LABELS, MATERIAL_SHEET_LABELS, QUEEN_ORIGIN_LABELS, state } from "./state.js";
import { escapeHtml, formatFrenchDate, formatRatio, periodLabel, setHint, setStatus } from "./utils.js";

export function renderSyntheseMetrics(data) {
  const totalRuche = Number(data?.total_visites_ruche || 0);
  const totalRucher = Number(data?.total_visites_rucher || 0);
  const ia = Number(data?.visites_ia_vocale || 0);
  const partIa = totalRuche > 0 ? Math.round((ia / totalRuche) * 100) : 0;

  dom.synthTotalVisitesRuche.textContent = String(totalRuche);
  dom.synthTotalVisitesRucher.textContent = String(totalRucher);
  dom.synthTotalRuches.textContent = String(state.ruches.length);
  dom.synthPartIa.textContent = `${partIa}%`;
  dom.synthReineVue.textContent = data?.taux_reine_vue != null ? `${Math.round(Number(data.taux_reine_vue) * 100)}%` : "-";

  const noteRuche = data?.note_ruche_moyenne != null ? Number(data.note_ruche_moyenne).toFixed(2) : "-";
  const noteRucher = data?.note_rucher_moyenne != null ? Number(data.note_rucher_moyenne).toFixed(2) : "-";
  const formatDisplayDate = (value) => value
    ? new Date(`${value}T00:00:00`).toLocaleDateString("fr-FR")
    : null;
  const period = data?.start_date || data?.end_date
    ? `du ${formatDisplayDate(data.start_date) || "debut"} au ${formatDisplayDate(data.end_date) || "aujourd hui"}`
    : "sur toute la periode";
  dom.syntheseLecture.textContent = `Lecture rapide ${period}: notes ${noteRuche}/${noteRucher}, ${data?.brouillons_ia ?? 0} brouillon(s) IA.`;
}

export async function refreshStatistics() {
  if (!state.authenticated) return;
  await Promise.all([loadSynthese(), loadAdvancedSynthesis()]);
}

export function statsSearchLabel(ruche) {
  const rucher = state.ruchers.find((item) => item.id === ruche.rucher_id);
  return `${ruche.identifiant_personnalise} · ${rucher?.nom || "Atelier"}`;
}

export function statsSearchHives() {
  const byId = new Map([...state.allRuches, ...state.atelierRuches].map((ruche) => [ruche.id, ruche]));
  return [...byId.values()].sort((a, b) => a.identifiant_personnalise.localeCompare(b.identifiant_personnalise, "fr", { numeric: true }));
}

export function renderStatsSearchOptions() {
  if (!dom.statsSearchOptions) return;
  dom.statsSearchOptions.replaceChildren(...statsSearchHives().map((ruche) => new Option(statsSearchLabel(ruche))));
}

// Recherche Statistiques : choisir une ruche (autocompletion ou Entree)
// cale le rucher et la ruche, comme les selecteurs de portee.
export async function applyStatsSearch() {
  const query = dom.statsSearch.value.trim().toLowerCase();
  if (!query) return;
  const hives = statsSearchHives();
  const match = hives.find((ruche) => statsSearchLabel(ruche).toLowerCase() === query)
    || hives.find((ruche) => ruche.identifiant_personnalise.toLowerCase() === query && ruche.rucher_id === state.selectedRucher?.id)
    || hives.find((ruche) => ruche.identifiant_personnalise.toLowerCase() === query)
    || hives.find((ruche) => ruche.identifiant_personnalise.toLowerCase().startsWith(query));
  if (!match) {
    setStatus(`Aucune ruche ne correspond a "${dom.statsSearch.value.trim()}".`);
    return;
  }
  dom.statsSearch.value = "";
  await applyScopeRuche(match.id);
}

export function setCurrentApiculturePeriod() {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, "0");
  const day = String(today.getDate()).padStart(2, "0");
  dom.synthStartDate.value = `${year}-01-01`;
  dom.synthEndDate.value = `${year}-${month}-${day}`;
}

export async function applyPeriodSelection() {
  if (dom.periodWindow.value === "today") {
    dom.periodWindow.value = "season";
    setCurrentApiculturePeriod();
  } else if (dom.periodWindow.value === "season") {
    setCurrentApiculturePeriod();
  } else if (dom.periodWindow.value === "last-season") {
    // Saison = annee civile (decision concepteur 2026-10-03).
    const lastYear = new Date().getFullYear() - 1;
    dom.synthStartDate.value = `${lastYear}-01-01`;
    dom.synthEndDate.value = `${lastYear}-12-31`;
  } else if (dom.periodWindow.value === "queen" && state.selectedRuche) {
    const reines = await api(`/ruches/${encodeURIComponent(state.selectedRuche.id)}/reines`);
    const active = reines.find((item) => item.statut === "active");
    if (active) {
      dom.synthStartDate.value = active.date_mise_en_place.slice(0, 10);
      dom.synthEndDate.value = new Date().toISOString().slice(0, 10);
    } else {
      setCurrentApiculturePeriod();
    }
  } else {
    const end = new Date();
    const start = new Date(end);
    start.setDate(end.getDate() - Number(dom.periodWindow.value) + 1);
    dom.synthStartDate.value = start.toISOString().slice(0, 10);
    dom.synthEndDate.value = end.toISOString().slice(0, 10);
  }
  await loadSynthese();
  await loadAdvancedSynthesis();
}

export async function loadSynthese() {
  if (!state.authenticated) {
    setHint(dom.authHint, "Connecte-toi d abord.", "error");
    return;
  }

  const queryParts = [];
  if (state.selectedRucher?.id) {
    queryParts.push(`rucher_id=${encodeURIComponent(state.selectedRucher.id)}`);
  }
  if (state.selectedRuche?.id) {
    queryParts.push(`ruche_id=${encodeURIComponent(state.selectedRuche.id)}`);
  }
  if (dom.synthStartDate.value) {
    queryParts.push(`start_date=${encodeURIComponent(dom.synthStartDate.value)}`);
  }
  if (dom.synthEndDate.value) {
    queryParts.push(`end_date=${encodeURIComponent(dom.synthEndDate.value)}`);
  }

  setStatus("Chargement de la synthese...");
  try {
    const suffix = queryParts.length ? `?${queryParts.join("&")}` : "";
    const data = await api(`/visites/synthese/periode${suffix}`);
    renderSyntheseMetrics(data);
    await loadEnrichedStatistics();
    setStatus("Synthese chargee.");
  } catch (error) {
    setStatus(`Erreur synthese: ${error.message}`);
  }
}

export function renderAdvancedSynthesis(data) {
  const current = data.current || {};
  const previous = data.previous || {};
  dom.trendNote.textContent = current.note_moyenne == null ? "-" : Number(current.note_moyenne).toFixed(2);
  dom.trendQueen.textContent = formatRatio(current.taux_reine_vue);
  dom.trendFrames.textContent = current.cadres_total_moyens == null ? "-" : Number(current.cadres_total_moyens).toFixed(1);
  dom.trendBroodShare.textContent = formatRatio(current.taux_cadres_couvain);
  const noteDelta = data.note_delta == null ? "n/d" : `${data.note_delta >= 0 ? "+" : ""}${Number(data.note_delta).toFixed(2)}`;
  const queenDelta = data.reine_delta == null ? "n/d" : `${data.reine_delta >= 0 ? "+" : ""}${Math.round(data.reine_delta * 100)} pts`;
  const broodDelta = data.couvain_delta == null ? "n/d" : `${data.couvain_delta >= 0 ? "+" : ""}${Math.round(data.couvain_delta * 100)} pts`;
  const broodFrames = current.cadres_couvain_moyens == null ? "-" : Number(current.cadres_couvain_moyens).toFixed(1);
  dom.trendComparison.textContent = `Fenetre ${data.window_days} jours: ${current.total_visites} visite(s), note ${noteDelta}, reine ${queenDelta}, couvain ${broodDelta} vs periode precedente. Couvain: ${broodFrames} cadres moyens.`;
  dom.trendScope.textContent = state.selectedRuche
    ? `Portee: ruche ${state.selectedRuche.identifiant_personnalise}.`
    : state.selectedRucher
      ? `Portee: rucher ${state.selectedRucher.nom}.`
      : "Portee: tous les ruchers.";
  dom.uncoveredHivesList.innerHTML = "";
  if (!data.uncovered_hives?.length) {
    dom.uncoveredHivesList.innerHTML = "<li>Toutes les ruches ont une visite recente.</li>";
    return;
  }
  data.uncovered_hives.forEach((hive) => {
    const li = document.createElement("li");
    li.textContent = `${hive.identifiant_personnalise} - ${hive.jours_depuis_visite == null ? "jamais visitee" : `${hive.jours_depuis_visite} jours`}`;
    dom.uncoveredHivesList.appendChild(li);
  });
}

export async function loadAdvancedSynthesis() {
  if (!state.authenticated) {
    setHint(dom.authHint, "Connecte-toi d abord.", "error");
    return;
  }
  const scopeParts = [];
  if (state.selectedRucher?.id) scopeParts.push(`rucher_id=${encodeURIComponent(state.selectedRucher.id)}`);
  if (state.selectedRuche?.id) scopeParts.push(`ruche_id=${encodeURIComponent(state.selectedRuche.id)}`);
  const suffix = scopeParts.length ? `&${scopeParts.join("&")}` : "";
  setStatus("Analyse des tendances...");
  try {
    const windowDays = dom.periodWindow.value === "180" ? 180 : dom.periodWindow.value === "90" ? 90 : 30;
    const data = await api(`/visites/synthese/avancee?window_days=${windowDays}${suffix}`);
    renderAdvancedSynthesis(data);
    setStatus("Tendances chargees.");
  } catch (error) {
    setStatus(`Erreur tendances: ${error.message}`);
  }
}

export async function loadEnrichedStatistics() {
  if (!state.authenticated) return;
  const params = new URLSearchParams();
  if (state.selectedRucher?.id) params.set("rucher_id", state.selectedRucher.id);
  if (state.selectedRuche?.id) params.set("ruche_id", state.selectedRuche.id);
  // Toutes les metriques suivent la meme fenetre que la synthese.
  const periodParams = new URLSearchParams();
  if (dom.synthStartDate.value) periodParams.set("start_date", dom.synthStartDate.value);
  if (dom.synthEndDate.value) periodParams.set("end_date", dom.synthEndDate.value);
  periodParams.forEach((value, key) => params.set(key, value));
  try {
    const scope = statsScope();
    applyStatsScopeVisibility(scope);
    const data = await api(`/statistiques/tableau-de-bord?${params.toString()}`);
    dom.statsYearLabel.textContent = periodLabel(data.start_date, data.end_date);
    dom.statsHoney.textContent = `${data.miel_total_kg.toFixed(1)} kg`;
    dom.statsHarvests.textContent = String(data.recoltes_count);
    dom.statsVisits.textContent = String(data.visites_count);
    dom.statsMortality.textContent = `${data.mortalite_percent}%`;
    dom.statsQueenAge.textContent = data.age_moyen_reines == null ? "-" : `${data.age_moyen_reines.toFixed(1)} an(s)`;
    dom.statsOldQueens.textContent = String(data.reines_agees_count);
    dom.statsFrameAge.textContent = data.age_moyen_cadres == null ? "A renseigner" : `${data.age_moyen_cadres.toFixed(1)} an(s)`;
    dom.statsOldFrames.textContent = String(data.cadres_anciens_count);
    dom.statsNewColonies.textContent = String(data.potential_new_colonies);
    renderCountBars(dom.statsTypeDistribution, data.type_distribution);
    renderCountBars(dom.statsRucherDistribution, data.rucher_distribution);
    // Chaque portee ne charge que ses propres donnees (une requete par fiche).
    if (scope === "global") {
      const [byRucher, byRuche] = await Promise.all([
        api(`/recoltes/stats/par-rucher?${periodParams.toString()}`),
        api(`/recoltes/stats/par-ruche?${periodParams.toString()}`)
      ]);
      renderHoneyBreakdown(dom.statsHoneyByRucher, byRucher.map((item) => ({ label: item.nom_rucher, value: item.poids_total_kg })), Infinity);
      // Toutes les ruches en rucher, y compris celles qui n'ont rien produit.
      const produced = new Map(byRuche.map((item) => [item.ruche_id, Number(item.poids_total_kg)]));
      const allHives = state.allRuches.filter((ruche) => !ruche.is_at_atelier)
        .map((ruche) => ({ label: ruche.identifiant_personnalise, value: produced.get(ruche.id) || 0 }))
        .sort((a, b) => b.value - a.value || a.label.localeCompare(b.label, "fr", { numeric: true }));
      renderHoneyBreakdown(dom.statsHoneyByRuche, allHives, Infinity, true);
    } else if (scope === "rucher") {
      renderRucherSheet(await api(`/statistiques/fiche-rucher?rucher_id=${encodeURIComponent(state.selectedRucher.id)}&${periodParams.toString()}`));
    } else {
      renderHiveSheet(await api(`/statistiques/fiche-ruche?ruche_id=${encodeURIComponent(state.selectedRuche.id)}&${periodParams.toString()}`));
    }
  } catch (error) {
    dom.statsTypeDistribution.textContent = `Indicateurs indisponibles: ${error.message}`;
  }
}

// --- Statistiques : portee globale, rucher ou ruche -------------------------------

export function statsScope() {
  if (state.selectedRuche) return "ruche";
  if (state.selectedRucher) return "rucher";
  return "global";
}

export function applyStatsScopeVisibility(scope) {
  document.querySelectorAll("[data-stats-scope]").forEach((block) => {
    block.hidden = !block.dataset.statsScope.split(" ").includes(scope);
  });
}

// Repartition : une barre par categorie, effectif et part du total.
export function renderCountBars(target, counts) {
  const entries = Object.entries(counts || {}).sort((a, b) => b[1] - a[1]);
  const total = entries.reduce((sum, [, count]) => sum + count, 0);
  if (!total) {
    target.innerHTML = "<p class=\"hint\">Aucune ruche dans la portee.</p>";
    return;
  }
  const maximum = Math.max(...entries.map(([, count]) => count));
  target.innerHTML = entries.map(([label, count]) => {
    const share = Math.round(count / total * 100);
    return `<div class="bar-row" title="${escapeHtml(label)} : ${count} ruche(s), ${share} %"><span>${escapeHtml(label)}</span><div class="bar-track"><i class="is-count" style="width:${count / maximum * 100}%"></i></div><strong>${count} <small>${share} %</small></strong></div>`;
  }).join("");
}

export function sheetTile(label, value) {
  return `<div class="sheet-tile"><span>${escapeHtml(label)}</span><strong>${escapeHtml(value)}</strong></div>`;
}

export function watchBlock(motifs) {
  if (!motifs.length) return "<p class=\"hint\">Aucun motif de surveillance.</p>";
  return `<ul class="sheet-watch">${motifs.map((motif) => `<li>${escapeHtml(motif)}</li>`).join("")}</ul>`;
}

export function renderRucherSheet(sheet) {
  const target = document.getElementById("stats-rucher-sheet");
  const percent = (value) => value == null ? "-" : `${Math.round(value * 100)} %`;
  target.innerHTML = `
    <div class="section-heading"><div><p class="eyebrow">Fiche rucher</p><h4>${escapeHtml(sheet.nom)}</h4></div><span class="status-chip">${escapeHtml(sheet.type_terrain || "biotope non renseigne")}</span></div>
    <div class="sheet-tiles">
      ${sheetTile("Ruches", String(sheet.ruches_actives))}
      ${sheetTile("Ruches visitees", `${sheet.ruches_visitees_periode}/${sheet.ruches_actives}`)}
      ${sheetTile("Visites", String(sheet.visites_periode))}
      ${sheetTile("Note moyenne", sheet.note_moyenne == null ? "-" : `${sheet.note_moyenne}/5`)}
      ${sheetTile("Couvain moyen", percent(sheet.couvain_moyen))}
      ${sheetTile("Reines actives", String(sheet.reines_actives))}
      ${sheetTile("Age moyen des reines", sheet.age_moyen_reines == null ? "-" : `${sheet.age_moyen_reines} an(s)`)}
      ${sheetTile("Reines de 2 ans ou plus", String(sheet.reines_plus_2_ans))}
      ${sheetTile("Miel recolte", `${sheet.miel_total_kg.toFixed(1)} kg`)}
    </div>
    <div class="sheet-columns">
      <section><h5>Formats</h5><div class="bar-list" data-bars="formats"></div><h5>Types</h5><div class="bar-list" data-bars="types"></div></section>
      <section><h5>Miel par ruche</h5><div class="bar-list sheet-scroll" data-bars="honey"></div></section>
      <section><h5>Ruches a surveiller</h5>${sheet.surveillance.length ? `<ul class="sheet-watch">${sheet.surveillance.map((entry) => `<li><strong>${escapeHtml(entry.identifiant_personnalise)}</strong> ${entry.motifs.map(escapeHtml).join(" · ")}</li>`).join("")}</ul>` : "<p class=\"hint\">Aucune ruche a surveiller.</p>"}</section>
    </div>`;
  const formats = Object.fromEntries(Object.entries(sheet.par_format).map(([key, count]) => [FORMAT_LABELS[key] || key, count]));
  renderCountBars(target.querySelector('[data-bars="formats"]'), formats);
  renderCountBars(target.querySelector('[data-bars="types"]'), sheet.par_type);
  renderHoneyBreakdown(target.querySelector('[data-bars="honey"]'), sheet.miel_par_ruche.map((item) => ({ label: item.identifiant_personnalise, value: item.poids_total_kg })), Infinity, true);
}

export function renderHiveSheet(sheet) {
  const target = document.getElementById("stats-hive-sheet");
  const hive = sheet.ruche;
  const queen = sheet.reine_active;
  const lastVisit = sheet.visites[sheet.visites.length - 1];
  const material = Object.entries(sheet.materiel).map(([key, count]) => `<li>${escapeHtml(MATERIAL_SHEET_LABELS[key] || key)}${count > 1 ? ` x ${count}` : ""}</li>`).join("");
  const movements = sheet.mouvements_cadres.length
    ? `<table class="sheet-table"><thead><tr><th>Date</th><th>Mouvement</th><th>Qte</th><th>Cire</th></tr></thead><tbody>${sheet.mouvements_cadres.map((item) => `<tr><td>${item.date ? formatFrenchDate(item.date) : "-"}</td><td>${escapeHtml(item.action || "-")}</td><td>${item.quantite}</td><td>${item.annee_cire || "-"}</td></tr>`).join("")}</tbody></table>`
    : "<p class=\"hint\">Aucun mouvement de cadres sur la periode.</p>";
  const harvests = sheet.recoltes.length
    ? `<ul class="sheet-list">${sheet.recoltes.map((item) => `<li>${formatFrenchDate(item.date_recolte)} <strong>${item.poids_miel_kg.toFixed(1)} kg</strong></li>`).join("")}</ul>`
    : "<p class=\"hint\">Aucune recolte sur la periode.</p>";
  const moves = sheet.transvasements.map((item) => `<li>${formatFrenchDate(item.date_transvasement)} : ${escapeHtml(FORMAT_LABELS[item.format_avant] || item.format_avant || "?")} vers ${escapeHtml(FORMAT_LABELS[item.format_apres] || item.format_apres || "?")}${item.identifiant_avant !== item.identifiant_apres ? ` (ex ${escapeHtml(item.identifiant_avant || "")})` : ""}</li>`).join("");
  target.innerHTML = `
    <div class="section-heading"><div><p class="eyebrow">Fiche ruche</p><h4>${escapeHtml(hive.identifiant_personnalise)}</h4></div><span class="status-chip">${escapeHtml(sheet.rucher_nom || "-")}</span></div>
    <div class="sheet-tiles">
      ${sheetTile("Format", FORMAT_LABELS[hive.format_ruche] || "Non renseigne")}
      ${sheetTile("Cadres", String(hive.nombre_cadres ?? "-"))}
      ${sheetTile("Visites", String(sheet.visites.length))}
      ${sheetTile("Derniere visite", sheet.derniere_visite ? formatFrenchDate(sheet.derniere_visite) : "Aucune")}
      ${sheetTile("Derniere note", lastVisit?.note_ruche == null ? "-" : `${lastVisit.note_ruche}/5`)}
      ${sheetTile("Miel recolte", `${sheet.miel_total_kg.toFixed(1)} kg`)}
      ${sheetTile("Age moyen des cadres", sheet.age_moyen_cadres == null ? "A renseigner" : `${sheet.age_moyen_cadres} an(s)`)}
    </div>
    <div class="sheet-columns">
      <section><h5>Reine</h5>${queen ? `<dl class="sheet-dl"><dt>Race</dt><dd>${escapeHtml(queen.race || "Non renseignee")}</dd><dt>Provenance</dt><dd>${escapeHtml(queen.provenance || "Non renseignee")}</dd><dt>Origine</dt><dd>${escapeHtml(QUEEN_ORIGIN_LABELS[queen.origine] || queen.origine)}</dd><dt>Mise en place</dt><dd>${formatFrenchDate(queen.date_mise_en_place)}</dd><dt>En place depuis</dt><dd>${queenTenure(queen.date_mise_en_place)}</dd></dl>` : "<p class=\"hint\">Aucune reine active.</p>"}<p class="hint">${sheet.reines.length} reine(s) dans l'historique.</p></section>
      <section><h5>Materiel</h5><ul class="sheet-list">${material || "<li>Non renseigne</li>"}</ul>${moves ? `<h5>Transvasements</h5><ul class="sheet-list">${moves}</ul>` : ""}</section>
      <section><h5>Surveillance</h5>${watchBlock(sheet.surveillance)}<h5>Recoltes</h5>${harvests}</section>
    </div>
    <section class="sheet-chart"><h5>Cadres et couvain par visite</h5><div data-chart="frames"></div></section>
    <section><h5>Mouvements de cadres</h5>${movements}</section>`;
  renderFramesChart(target.querySelector('[data-chart="frames"]'), sheet.visites);
}

// Courbes cadres totaux / cadres de couvain : un seul axe (memes unites),
// couvain en pointilles en plus de la couleur, legende et etiquettes directes.
export function renderFramesChart(target, visits) {
  const points = visits.filter((visit) => visit.nombre_cadres_total != null || visit.nombre_cadres_couvain != null);
  if (points.length < 2) {
    target.innerHTML = "<p class=\"hint\">Au moins deux visites avec des cadres renseignes sont necessaires pour tracer l'evolution.</p>";
    return;
  }
  // Dessin a l'echelle 1 du conteneur : le texte garde sa taille sur mobile.
  const width = Math.max(280, Math.round(target.clientWidth || 640));
  const height = width < 480 ? 200 : 240;
  const pad = { top: 16, right: 78, bottom: 28, left: 30 };
  const times = points.map((visit) => new Date(visit.date_visite).getTime());
  const minTime = Math.min(...times);
  const span = Math.max(Math.max(...times) - minTime, 1);
  const maxValue = Math.max(10, ...points.map((visit) => Math.max(visit.nombre_cadres_total || 0, visit.nombre_cadres_couvain || 0)));
  const x = (time) => pad.left + (time - minTime) / span * (width - pad.left - pad.right);
  const y = (value) => height - pad.bottom - value / maxValue * (height - pad.top - pad.bottom);
  const series = [
    { key: "nombre_cadres_total", label: "Cadres", className: "chart-total" },
    { key: "nombre_cadres_couvain", label: "Couvain", className: "chart-brood" },
  ];
  const ticks = [0, Math.round(maxValue / 2), maxValue];
  const grid = ticks.map((tick) => `<line class="chart-grid" x1="${pad.left}" x2="${width - pad.right}" y1="${y(tick)}" y2="${y(tick)}"></line><text class="chart-axis" x="${pad.left - 6}" y="${y(tick) + 4}" text-anchor="end">${tick}</text>`).join("");
  const dateLabels = [points[0], points[points.length - 1]].map((visit, index) => `<text class="chart-axis" x="${x(new Date(visit.date_visite).getTime())}" y="${height - 8}" text-anchor="${index ? "end" : "start"}">${formatFrenchDate(visit.date_visite)}</text>`).join("");
  const lines = series.map((serie) => {
    const serieePoints = points.filter((visit) => visit[serie.key] != null);
    if (!serieePoints.length) return "";
    const path = serieePoints.map((visit, index) => `${index ? "L" : "M"}${x(new Date(visit.date_visite).getTime()).toFixed(1)},${y(visit[serie.key]).toFixed(1)}`).join(" ");
    const dots = serieePoints.map((visit) => `<circle class="${serie.className}" cx="${x(new Date(visit.date_visite).getTime()).toFixed(1)}" cy="${y(visit[serie.key]).toFixed(1)}" r="4.5"><title>${formatFrenchDate(visit.date_visite)} : ${visit[serie.key]} ${serie.label.toLowerCase()}</title></circle>`).join("");
    const last = serieePoints[serieePoints.length - 1];
    const label = `<text class="chart-label" x="${x(new Date(last.date_visite).getTime()) + 8}" y="${y(last[serie.key]) + 4}">${serie.label} ${last[serie.key]}</text>`;
    return `<path class="${serie.className}" d="${path}"></path>${dots}${label}`;
  }).join("");
  target.innerHTML = `<div class="chart-legend"><span><i class="chart-swatch chart-total"></i>Cadres totaux</span><span><i class="chart-swatch chart-brood"></i>Cadres de couvain</span></div><svg class="frames-chart" viewBox="0 0 ${width} ${height}" role="img" aria-label="Evolution des cadres et du couvain sur ${points.length} visites">${grid}${dateLabels}${lines}</svg>`;
}
