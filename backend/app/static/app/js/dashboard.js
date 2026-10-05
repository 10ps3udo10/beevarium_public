import { api } from "./api.js";
import { loadAtelier } from "./atelier.js";
import { logout, renderOnboarding } from "./auth.js";
import { dom } from "./dom.js";
import { renderRuchers, selectRucher } from "./ruchers.js";
import { renderRucheReferenceOptions } from "./ruches.js";
import { renderScopeSelectors } from "./scope.js";
import { WATCHLIST_TIP, state } from "./state.js";
import { escapeHtml, formatFrenchDate, setHint, setStatus } from "./utils.js";
import { renderFrameActionOptions } from "./visites.js";

export function renderDashboardOverview() {
  const totalRuches = state.ruches.length;
  const atelierCount = state.atelierRuches.length;
  dom.dashboardRuchersCount.textContent = String(state.ruchers.length);
  dom.dashboardRuchesCount.textContent = String(totalRuches || "-");
  dom.dashboardAtelierCount.textContent = String(atelierCount || "-");
  dom.dashboardLastVisit.textContent = "-";
  dom.dashboardUnvisitedCount.textContent = "-";
  dom.dashboardQueensCount.textContent = "-";
  dom.dashboardQueenAge.textContent = "-";
  dom.dashboardQueenAlerts.textContent = "-";
  dom.dashboardFramesAverage.textContent = "-";
  updateDashboardMeter(dom.dashboardVisitMeter, dom.dashboardVisitMeterLabel, 0, "-");
  updateDashboardMeter(dom.dashboardBroodMeter, dom.dashboardBroodMeterLabel, 0, "-");
  updateDashboardMeter(dom.dashboardQueenMeter, dom.dashboardQueenMeterLabel, 0, "-");
  dom.dashboardSummaryHint.textContent = "";
}

export function updateDashboardMeter(element, label, ratio, text) {
  const safeRatio = Math.max(0, Math.min(1, Number.isFinite(ratio) ? ratio : 0));
  element?.style.setProperty("--value", `${Math.round(safeRatio * 100)}%`);
  if (label) label.textContent = text;
}

export async function loadDashboardIndicators() {
  const data = await api("/statistiques/cheptel");

  state.onboarding = {
    ruchers: state.ruchers.length,
    ruches: state.allRuches.length + state.atelierRuches.length,
    hasVisit: Boolean(data.derniere_visite),
  };

  dom.dashboardRuchersCount.textContent = String(data.ruchers_actifs);
  dom.dashboardRuchesCount.textContent = String(data.ruches_suivies);
  dom.dashboardAtelierCount.textContent = String(data.ruches_atelier);
  dom.dashboardLastVisit.textContent = data.derniere_visite ? formatFrenchDate(data.derniere_visite) : "Aucune";
  dom.dashboardUnvisitedCount.textContent = String(data.ruches_sans_visite_recente);
  if (dom.dashboardDraftsCount) {
    dom.dashboardDraftsCount.textContent = String(data.visites_a_valider ?? 0);
  }
  dom.dashboardQueensCount.textContent = String(data.reines_actives);
  if (dom.dashboardOldQueens) dom.dashboardOldQueens.textContent = String(data.reines_plus_2_ans ?? 0);
  dom.dashboardQueenAge.textContent = data.age_moyen_reines == null ? "-" : `${data.age_moyen_reines.toFixed(1)} an(s)`;
  dom.dashboardQueenAlerts.textContent = String(data.ruches_a_surveiller.length);
  // Taux d occupation plutot que moyenne brute : une ruchette de 6 cadres
  // pleine ne doit pas tirer la moyenne vers le bas face aux Dadant 10.
  dom.dashboardFramesAverage.textContent = data.taux_occupation_cadres == null ? "-" : `${Math.round(data.taux_occupation_cadres * 100)} %`;

  const totalHives = Number(data.ruches_suivies || 0);
  const visitedThisYear = Math.min(Number(data.ruches_visitees_annee || 0), totalHives);
  const visitCoverage = totalHives > 0 ? visitedThisYear / totalHives : 0;
  const queenCoverage = totalHives > 0 ? Number(data.reines_actives || 0) / totalHives : 0;
  updateDashboardMeter(dom.dashboardVisitMeter, dom.dashboardVisitMeterLabel, visitCoverage, totalHives ? `${Math.round(visitCoverage * 100)}%` : "-");
  updateDashboardMeter(dom.dashboardBroodMeter, dom.dashboardBroodMeterLabel, Number(data.taux_couvain_moyen || 0), data.taux_couvain_moyen == null ? "-" : `${Math.round(data.taux_couvain_moyen * 100)}%`);
  updateDashboardMeter(dom.dashboardQueenMeter, dom.dashboardQueenMeterLabel, queenCoverage, totalHives ? `${data.reines_actives}/${totalHives}` : "-");
  if (dom.dashboardVisitMeterCaption) {
    dom.dashboardVisitMeterCaption.textContent = `${visitedThisYear}/${totalHives} ruches visitees`;
  }
  renderWatchlist(data.ruches_a_surveiller);
  renderOnboarding();
  await loadDashboardVisitChart();
}

export async function loadDashboardVisitChart() {
  if (!dom.dashboardMonthlyVisits) return;
  try {
    const data = await api("/statistiques/visites-par-mois");
    const maximum = Math.max(...data.months.map((item) => item.count), 1);
    dom.dashboardMonthlyVisits.innerHTML = "";
    data.months.forEach((item) => {
      const column = document.createElement("div");
      column.className = "monthly-visit-column";
      const bar = document.createElement("i");
      bar.style.height = `${Math.round((item.count / maximum) * 100)}%`;
      const label = document.createElement("span");
      label.textContent = new Date(`${item.month}-01T00:00:00`).toLocaleDateString("fr-FR", { month: "short" }).replace(".", "");
      if (item.count > 0) {
        const count = document.createElement("strong");
        count.textContent = String(item.count);
        column.append(count);
      }
      column.append(bar, label);
      dom.dashboardMonthlyVisits.appendChild(column);
    });
  } catch (error) {
    dom.dashboardMonthlyVisits.innerHTML = `<p class="hint">Graphique indisponible: ${error.message}</p>`;
  }
}

export function renderWatchlist(entries) {
  if (!dom.dashboardWatchlist) {
    return;
  }
  if (!entries.length) {
    dom.dashboardWatchlist.hidden = true;
    dom.dashboardWatchlist.innerHTML = "";
    return;
  }

  dom.dashboardWatchlist.hidden = false;
  const items = entries
    .map((entry) => {
      const lieu = entry.rucher_nom ? ` · ${escapeHtml(entry.rucher_nom)}` : "";
      return `<li><strong>${escapeHtml(entry.identifiant_personnalise)}</strong>${lieu}<span>${entry.motifs.map(escapeHtml).join(" · ")}</span></li>`;
    })
    .join("");
  dom.dashboardWatchlist.innerHTML = `<p class="category-label">Ruches a surveiller <button type="button" class="info-tip" aria-label="Explication" data-tip="${escapeHtml(WATCHLIST_TIP)}">i</button></p><ul class="watchlist-items">${items}</ul>`;
}

export function renderDashboardContext() {
  if (state.selectedRuche) {
    dom.dashboardContextLabel.textContent = `${state.selectedRucher?.nom || "Atelier"} / ${state.selectedRuche.identifiant_personnalise}`;
  } else if (state.selectedRucher) {
    dom.dashboardContextLabel.textContent = state.selectedRucher.nom;
  } else {
    dom.dashboardContextLabel.textContent = "Tous les ruchers";
  }
  renderScopeSelectors();
}

export async function refreshDashboard() {
  if (!state.authenticated) {
    setHint(dom.authHint, "Connecte-toi d abord.", "error");
    return;
  }

  setStatus("Chargement des ruchers...");
  try {
    const [typeRefs, statusRefs, cadreRefs] = await Promise.all([api("/references/type-ruche"), api("/references/statut-ruche"), api("/references/action-cadre")]);
    state.references.types = new Map(typeRefs.map((item) => [item.id, item.libelle]));
    state.references.statuses = new Map(statusRefs.map((item) => [item.id, item.libelle]));
    state.references.cadreActions = new Map(cadreRefs.map((item) => [item.id, item.libelle]));
    renderRucheReferenceOptions();
    renderFrameActionOptions();
    state.ruchers = await api("/ruchers");
    const ruchesParRucher = await Promise.all(
      state.ruchers.map((rucher) => api(`/ruches?rucher_id=${encodeURIComponent(rucher.id)}`))
    );
    state.ruches = ruchesParRucher.flat();
    state.allRuches = [...state.ruches];
    await loadAtelier();
    renderRuchers();
    renderDashboardOverview();
    renderScopeSelectors();
    await loadDashboardIndicators();

    if (state.selectedRucher) {
      const next = state.ruchers.find((item) => item.id === state.selectedRucher.id);
      if (next) {
        await selectRucher(next);
      }
    }

    setStatus("Tableau de bord charge.");
  } catch (error) {
    if (error.status === 401) {
      logout();
      setHint(dom.authHint, "Session expiree. Reconnecte-toi.", "error");
      return;
    }
    setStatus(`Erreur ruchers: ${error.message}`);
  }
}
