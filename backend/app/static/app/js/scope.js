import { renderDashboardContext } from "./dashboard.js";
import { dom } from "./dom.js";
import { refreshVisitsIfActive } from "./navigation.js";
import { selectRucher } from "./ruchers.js";
import { selectRuche } from "./ruches.js";
import { state } from "./state.js";
import { refreshStatistics } from "./statistiques.js";

// La popup de visite permet de choisir rucher puis ruche, quel que soit
// l'onglet ou le contexte d'ouverture ; elle reprend la portee courante.
export function fillVisitCreateScope() {
  const rucherId = state.selectedRuche?.rucher_id || state.selectedRucher?.id || "";
  dom.visitCreateRucher.replaceChildren(
    new Option("Choisir un rucher", ""),
    ...state.ruchers.map((rucher) => new Option(rucher.nom, rucher.id)),
  );
  dom.visitCreateRucher.value = rucherId;
  const hives = state.allRuches
    .filter((ruche) => !ruche.is_at_atelier && ruche.rucher_id === rucherId)
    .sort((a, b) => a.identifiant_personnalise.localeCompare(b.identifiant_personnalise, "fr", { numeric: true }));
  dom.visitCreateRuche.replaceChildren(
    new Option(rucherId ? "Choisir une ruche" : "Choisir d'abord un rucher", ""),
    ...hives.map((ruche) => new Option(ruche.identifiant_personnalise, ruche.id)),
  );
  dom.visitCreateRuche.value = state.selectedRuche?.id || "";
  dom.visitCreateRuche.disabled = !rucherId;
}

// Selecteurs de portee partages par la saisie de visite et les statistiques:
// ils evitent de devoir passer par l onglet Ruchers pour choisir une ruche.
export function renderScopeSelectors() {
  const hivesFor = (rucherId) => {
    // state.ruches contient les ruches du rucher courant, y compris celles qui
    // viennent d etre creees et ne sont pas encore dans allRuches.
    const all = [...state.allRuches, ...state.ruches, ...state.atelierRuches];
    const unique = [...new Map(all.map((ruche) => [ruche.id, ruche])).values()];
    return unique
      .filter((ruche) => !rucherId || ruche.rucher_id === rucherId)
      .sort((left, right) => left.identifiant_personnalise.localeCompare(right.identifiant_personnalise, "fr", { numeric: true }));
  };

  const fill = (select, placeholder, entries, selectedId, labelOf) => {
    if (!select) {
      return;
    }
    select.innerHTML = `<option value="">${placeholder}</option>`;
    entries.forEach((entry) => {
      const option = document.createElement("option");
      option.value = entry.id;
      option.textContent = labelOf(entry);
      select.appendChild(option);
    });
    select.value = selectedId || "";
  };

  const renderMenu = (menu, select, placeholder, entries, selectedId, labelOf, onSelect) => {
    if (!menu) return;
    const selected = entries.find((entry) => entry.id === selectedId);
    const summary = menu.querySelector("summary");
    const options = menu.querySelector(".scope-menu-options");
    summary.textContent = selected ? labelOf(selected) : placeholder;
    options.innerHTML = "";
    [{ id: "", label: placeholder }, ...entries.map((entry) => ({ id: entry.id, label: labelOf(entry) }))]
      .forEach((entry) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = entry.label;
        button.classList.toggle("is-selected", entry.id === selectedId);
        button.addEventListener("click", async () => {
          menu.open = false;
          select.value = entry.id;
          await onSelect(entry.id);
        });
        options.appendChild(button);
      });
  };

  const rucherId = state.selectedRucher?.id || "";
  const rucheId = state.selectedRuche?.id || "";
  const hives = hivesFor(rucherId);

  fill(dom.visiteScopeRucher, "Choisir un rucher", state.ruchers, rucherId, (r) => r.nom);
  fill(dom.visiteScopeRuche, "Choisir une ruche", hives, rucheId, (r) => r.identifiant_personnalise);
  fill(dom.statsScopeRucher, "Tous les ruchers", state.ruchers, rucherId, (r) => r.nom);
  fill(dom.statsScopeRuche, "Toutes les ruches", hives, rucheId, (r) => r.identifiant_personnalise);
  renderMenu(dom.visiteScopeRucherMenu, dom.visiteScopeRucher, "Choisir un rucher", state.ruchers, rucherId, (r) => r.nom, applyScopeRucher);
  renderMenu(dom.visiteScopeRucheMenu, dom.visiteScopeRuche, "Choisir une ruche", hives, rucheId, (r) => r.identifiant_personnalise, applyScopeRuche);
  renderMenu(dom.statsScopeRucherMenu, dom.statsScopeRucher, "Tous les ruchers", state.ruchers, rucherId, (r) => r.nom, applyScopeRucher);
  renderMenu(dom.statsScopeRucheMenu, dom.statsScopeRuche, "Toutes les ruches", hives, rucheId, (r) => r.identifiant_personnalise, applyScopeRuche);

  if (dom.visiteScopeReminder) {
    dom.visiteScopeReminder.textContent = state.selectedRuche
      ? `Saisie pour ${state.selectedRuche.identifiant_personnalise}.`
      : "Choisis le rucher et la ruche en haut de l onglet avant de saisir.";
  }
}

export async function applyScopeRucher(rucherId) {
  if (!rucherId) {
    state.selectedRucher = null;
    state.selectedRuche = null;
    renderDashboardContext();
    await refreshVisitsIfActive();
    await refreshStatistics();
    return;
  }
  const rucher = state.ruchers.find((item) => item.id === rucherId);
  if (rucher) {
    await selectRucher(rucher);
    await refreshVisitsIfActive();
    await refreshStatistics();
  }
}

export async function applyScopeRuche(rucheId) {
  if (!rucheId) {
    state.selectedRuche = null;
    renderDashboardContext();
    await refreshVisitsIfActive();
    await refreshStatistics();
    return;
  }
  const all = [...state.allRuches, ...state.ruches, ...state.atelierRuches];
  const ruche = all.find((item) => item.id === rucheId);
  if (!ruche) {
    return;
  }
  // Choisir une ruche depuis un autre onglet doit aussi caler le rucher.
  if (ruche.rucher_id && ruche.rucher_id !== state.selectedRucher?.id) {
    const rucher = state.ruchers.find((item) => item.id === ruche.rucher_id);
    if (rucher) {
      await selectRucher(rucher);
    }
  }
  await selectRuche(ruche);
  await refreshVisitsIfActive();
}
