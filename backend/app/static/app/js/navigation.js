import { dom } from "./dom.js";
import { loadDrafts } from "./ia.js";
import { updateRucherPanelVisibility } from "./ruchers.js";
import { state } from "./state.js";
import { refreshStatistics } from "./statistiques.js";
import { loadVisitHistory } from "./visites.js";

export function bindCompactMenu(menu, select) {
  if (!menu || !select) return;
  const summary = menu.querySelector("summary");
  const options = menu.querySelector(".scope-menu-options");
  const render = () => {
    summary.textContent = select.options[select.selectedIndex]?.textContent || "Choisir";
    options.innerHTML = "";
    [...select.options].forEach((option) => {
      const button = document.createElement("button");
      button.type = "button";
      button.textContent = option.textContent;
      button.classList.toggle("is-selected", option.value === select.value);
      button.addEventListener("click", () => {
        menu.open = false;
        select.value = option.value;
        select.dispatchEvent(new Event("change", { bubbles: true }));
      });
      options.appendChild(button);
    });
  };
  select.addEventListener("change", render);
  render();
}

// L'onglet actif est garde dans l'URL (#visites...) pour survivre a une
// actualisation ; les filtres, eux, repartent de zero au chargement.
export function tabFromLocation() {
  const tabName = window.location.hash.replace(/^#/, "");
  return document.querySelector(`.tab-button[data-tab="${CSS.escape(tabName)}"]`) ? tabName : "dashboard";
}

export function setActiveTab(tabName) {
  const dashboardCard = document.getElementById("dashboard-card");
  dashboardCard.dataset.activeTab = tabName;
  const hash = tabName === "dashboard" ? "" : `#${tabName}`;
  if (window.location.hash !== hash) {
    window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}${hash}`);
  }
  closeNavigationDrawer();
  document.querySelectorAll(".tab-button").forEach((button) => {
    const active = button.dataset.tab === tabName;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-selected", String(active));
  });
  dashboardCard.querySelectorAll("[data-panel]").forEach((panel) => {
    const panels = panel.dataset.panel.split(" ");
    panel.hidden = !panels.includes(tabName);
  });
  updateRucherPanelVisibility();
  if (tabName === "visites") {
    loadDrafts();
    loadVisitHistory();
  }
  // Les statistiques n'etaient chargees qu'au premier changement de filtre.
  if (tabName === "stats" && state.authenticated) {
    refreshStatistics();
  }
}

export function restorePendingTab() {
  const tabName = state.pendingTab;
  state.pendingTab = null;
  if (tabName && tabName !== "dashboard") setActiveTab(tabName);
}

export function openNavigationDrawer() {
  dom.mainNav?.classList.add("is-open");
  if (dom.navBackdrop) dom.navBackdrop.hidden = false;
  dom.btnOpenNav?.setAttribute("aria-expanded", "true");
}

export function toggleNavigationDrawer() {
  if (dom.mainNav?.classList.contains("is-open")) {
    closeNavigationDrawer();
    return;
  }
  openNavigationDrawer();
}

export function closeNavigationDrawer() {
  dom.mainNav?.classList.remove("is-open");
  // Le menu desktop reste ouvert tant qu'il contient le focus (:focus-within) :
  // sans cela, il masquait le logo apres chaque changement d'onglet.
  if (dom.mainNav?.contains(document.activeElement)) document.activeElement.blur();
  if (dom.navBackdrop) dom.navBackdrop.hidden = true;
  dom.btnOpenNav?.setAttribute("aria-expanded", "false");
}

export async function refreshVisitsIfActive() {
  if (!state.authenticated) return;
  const dashboardCard = document.getElementById("dashboard-card");
  if (dashboardCard?.dataset.activeTab === "visites") {
    await loadVisitHistory();
  }
}
