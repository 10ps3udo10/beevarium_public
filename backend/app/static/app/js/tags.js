import { api } from "./api.js";
import { dom } from "./dom.js";
import { refreshSelectedRuche, renderRuches } from "./ruches.js";
import { DEFAULT_TAG_FAVORITES, TAG_CATALOG, state } from "./state.js";
import { escapeHtml, setHint, setStatus } from "./utils.js";

export function allCatalogTags() {
  return TAG_CATALOG.flatMap((group) => group.tags);
}

export function loadTagFavorites() {
  try {
    const parsed = JSON.parse(localStorage.getItem("bee.tagFavorites") || "null");
    const catalog = new Set(allCatalogTags());
    state.tagFavorites = Array.isArray(parsed) && parsed.length
      ? parsed.filter((tag) => catalog.has(tag))
      : [...DEFAULT_TAG_FAVORITES];
  } catch {
    state.tagFavorites = [...DEFAULT_TAG_FAVORITES];
  }
}

export async function saveTagFavorites() {
  localStorage.setItem("bee.tagFavorites", JSON.stringify(state.tagFavorites));
  if (state.token) {
    await api("/users/me", { method: "PATCH", body: { tag_favorites: state.tagFavorites } });
  }
}

export function renderTagSuggestions() {
  dom.tagSuggestions.innerHTML = allCatalogTags()
    .map((tag) => `<option value="${tag}"></option>`)
    .join("");
}

export function renderVisitSelectedTags(tags) {
  if (!dom.visitSelectedTags) return;
  const visible = (tags || []).filter((tag) => tag.source !== "derive");
  const pills = [
    ...visible.map((tag) => `<span class="tag-pill">${escapeHtml(tag.libelle)}</span>`),
    ...state.pendingVisitTags.map((label) => `<span class="tag-pill is-pending" title="Pose a la synchronisation de la visite">${escapeHtml(label)} (hors ligne)</span>`),
  ];
  dom.visitSelectedTags.innerHTML = pills.length ? pills.join("") : "<p class=\"hint\">Aucun tag pose.</p>";
}

export function updateVisitTagSuggestions() {
  const suggestions = [];
  if (dom.visiteReineVue.value === "false") suggestions.push("reine non vue");
  if (dom.visiteCouvain.value === "faible") suggestions.push("couvain faible");
  if (dom.visiteReserves.value === "critique") suggestions.push("reserves faibles", "a nourrir");
  if (dom.visiteCadresCouvain.value === "0") suggestions.push("absence couvain");
  renderVisitTagSuggestions(dom.visitTagSuggestions, [...new Set(suggestions)]);
}

export function renderVisitTagSuggestions(target, suggestions, removalSuggestions = []) {
  target.innerHTML = "";
  target.hidden = !suggestions?.length && !removalSuggestions?.length;
  if (!suggestions?.length && !removalSuggestions?.length) return;
  if (removalSuggestions?.length) {
    const removedTitle = document.createElement("p");
    removedTitle.className = "hint";
    removedTitle.textContent = "Tags retires automatiquement";
    target.appendChild(removedTitle);
    const removedList = document.createElement("div");
    removedList.className = "tag-favorites";
    removalSuggestions.forEach((label) => {
      const item = document.createElement("span");
      item.className = "tag-quick tag-removed";
      item.textContent = label;
      removedList.appendChild(item);
    });
    target.appendChild(removedList);
  }
  if (!suggestions?.length) return;
  const title = document.createElement("p");
  title.className = "hint";
  title.textContent = "Tags suggeres par cette visite";
  target.appendChild(title);
  const list = document.createElement("div");
  list.className = "tag-favorites";
  suggestions.forEach((label) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tag-quick";
    button.textContent = label;
    button.addEventListener("click", async () => {
      await addRucheTagByLabel(label);
      button.disabled = true;
    });
    list.appendChild(button);
  });
  target.appendChild(list);
}

export function renderRucheTags(tags) {
  state.selectedRucheTags = tags;
  renderVisitSelectedTags(tags);
  syncSelectedRucheTags(tags);
  dom.rucheTagsList.innerHTML = "";
  if (!tags.length) {
    dom.rucheTagsList.innerHTML = "<p class=\"hint\">Aucun tag.</p>";
    renderTagFavorites();
    return;
  }
  tags.forEach((tag) => {
    if (tag.source === "derive") {
      const pill = document.createElement("span");
      pill.className = "tag-pill is-derived";
      pill.textContent = tag.libelle;
      dom.rucheTagsList.appendChild(pill);
      return;
    }
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tag-pill";
    button.dataset.tagId = tag.id;
    button.textContent = `${tag.libelle} x`;
    button.title = `Retirer ${tag.libelle}`;
    dom.rucheTagsList.appendChild(button);
  });
  renderTagFavorites();
}

export function syncSelectedRucheTags(tags) {
  if (!state.selectedRuche) return;
  // Le tag derive `a surveiller` reste visible dans le tableau des ruches.
  const visibles = tags.filter((tag) => tag.source !== "derive" || tag.libelle === "a surveiller");
  // Simple consultation : tags inchanges, pas de reconstruction du tableau
  // (elle decalait la liste juste apres avoir coche une ruche).
  const libelles = (list) => (list || []).map((tag) => tag.libelle).join("|");
  if (libelles(visibles) === libelles(state.selectedRuche.tags)) return;
  state.selectedRuche.tags = visibles;
  const update = (ruche) => ruche.id === state.selectedRuche.id ? { ...ruche, tags: state.selectedRuche.tags } : ruche;
  state.ruches = state.ruches.map(update);
  state.allRuches = state.allRuches.map(update);
  state.atelierRuches = state.atelierRuches.map(update);
  renderRuches();
}

export function renderTagFavorites() {
  if (!dom.rucheTagFavorites) return;
  const active = new Set(state.selectedRucheTags.map((tag) => tag.libelle.toLowerCase()));
  if (dom.tagDialogCurrent) {
    dom.tagDialogCurrent.innerHTML = state.selectedRucheTags.length
      ? state.selectedRucheTags.map((tag) => `<button type="button" class="tag-pill${tag.source === "derive" ? " is-derived" : ""}" data-tag-id="${escapeHtml(tag.id)}" title="Retirer ${escapeHtml(tag.libelle)}">${escapeHtml(tag.libelle)}${tag.source === "derive" ? "" : " x"}</button>`).join("")
      : "<p class=\"hint\">Aucun tag pose.</p>";
  }
  dom.rucheTagFavorites.innerHTML = "";
  state.tagFavorites.forEach((label) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "tag-quick";
    button.textContent = label;
    button.disabled = active.has(label.toLowerCase());
    bindStagedTag(button, label);
    dom.rucheTagFavorites.appendChild(button);
  });
  if (dom.tagDialogCatalog) {
    const catalogFragment = document.createDocumentFragment();
    TAG_CATALOG.forEach((group) => {
      const tags = group.tags.map((label) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = "tag-quick";
        button.textContent = label;
        button.disabled = active.has(label.toLowerCase());
        bindStagedTag(button, label);
        return button;
      });
      const section = document.createElement("section");
      section.className = "tag-dialog-category";
      const title = document.createElement("h4");
      title.textContent = group.category;
      const list = document.createElement("div");
      list.className = "tag-favorites";
      tags.forEach((button) => list.appendChild(button));
      section.append(title, list);
      catalogFragment.appendChild(section);
    });
    dom.tagDialogCatalog.replaceChildren(catalogFragment);
  }
}

// Les tags cliques dans la popup sont selectionnes puis poses ensemble par le
// bouton Ajouter, avec ceux saisis a la main (separes par des virgules).
export function bindStagedTag(button, label) {
  const key = label.toLowerCase();
  const sync = () => {
    const selected = state.stagedRucheTags.has(key);
    button.classList.toggle("is-selected", selected);
    button.setAttribute("aria-pressed", String(selected));
  };
  sync();
  button.addEventListener("click", () => {
    if (state.stagedRucheTags.has(key)) state.stagedRucheTags.delete(key);
    else state.stagedRucheTags.set(key, label);
    sync();
    // Le meme tag peut figurer dans les favoris et dans le catalogue.
    renderTagFavorites();
    updateAddTagsButton();
  });
}

export function typedTagLabels() {
  return dom.rucheTagInput.value.split(",").map((label) => label.trim()).filter(Boolean);
}

export function updateAddTagsButton() {
  const keys = new Set([...state.stagedRucheTags.keys(), ...typedTagLabels().map((label) => label.toLowerCase())]);
  dom.btnAddRucheTags.textContent = keys.size > 1 ? `Ajouter ${keys.size} tags` : "Ajouter";
}

export async function openTagDialog() {
  if (!state.selectedRuche) {
    setStatus("Selectionne une ruche avant de modifier les tags.");
    return;
  }
  state.resumeDialogAfterTags = null;
  [dom.visitCreateDialog, dom.visitDialog].forEach((dialog) => {
    if (dialog.open) {
      state.resumeDialogAfterTags = dialog;
      dialog.close();
    }
  });
  await loadRucheTags();
  state.stagedRucheTags.clear();
  renderTagFavorites();
  dom.rucheTagInput.value = "";
  updateAddTagsButton();
  setHint(dom.rucheTagHint, "", "");
  dom.tagDialog.showModal();
  dom.rucheTagInput.focus();
}

export function closeTagDialog() {
  dom.tagDialog.close();
  if (state.resumeDialogAfterTags) {
    state.resumeDialogAfterTags.showModal();
    state.resumeDialogAfterTags = null;
  }
}

export async function loadRucheTags() {
  if (!state.selectedRuche) return;
  try {
    const tags = await api(`/ruches/${encodeURIComponent(state.selectedRuche.id)}/tags`);
    renderRucheTags(tags);
  } catch (error) {
    dom.rucheTagsList.innerHTML = `<p class="hint">Tags indisponibles: ${error.message}</p>`;
  }
}

export async function addRucheTag(event) {
  event.preventDefault();
  await addRucheTagsByLabels([...state.stagedRucheTags.values(), ...typedTagLabels()]);
}

export async function addRucheTagByLabel(label) {
  await addRucheTagsByLabels([label]);
}

export async function addRucheTagsByLabels(rawLabels) {
  if (!state.selectedRuche) {
    setHint(dom.rucheTagHint, "Selectionne une ruche d abord.", "error");
    return;
  }
  const active = new Set(state.selectedRucheTags.map((tag) => tag.libelle.toLowerCase()));
  const labels = [...new Map(rawLabels.map((label) => [label.toLowerCase(), label])).values()]
    .filter((label) => !active.has(label.toLowerCase()));
  if (!labels.length) {
    setHint(dom.rucheTagHint, "Choisis un ou plusieurs tags, ou saisis-les separes par des virgules.", "error");
    return;
  }
  const fromNewVisit = state.resumeDialogAfterTags === dom.visitCreateDialog;
  if (fromNewVisit && !navigator.onLine) {
    addPendingVisitTags(labels);
    return;
  }
  const added = [];
  try {
    for (const label of labels) {
      await api(`/ruches/${encodeURIComponent(state.selectedRuche.id)}/tags`, { method: "POST", body: { libelle: label } });
      added.push(label);
    }
  } catch (error) {
    if (fromNewVisit && (error.message === "Failed to fetch" || error.message === "Echec reseau")) {
      addPendingVisitTags(labels.filter((label) => !added.includes(label)));
      return;
    }
    setHint(dom.rucheTagHint, `Tag impossible: ${error.message}`, "error");
    if (added.length) await loadRucheTags();
    return;
  }
  dom.rucheTagInput.value = "";
  state.stagedRucheTags.clear();
  await refreshSelectedRuche();
  await loadRucheTags();
  closeTagDialog();
  setStatus(labels.length > 1 ? `${labels.length} tags ajoutes : ${labels.join(", ")}.` : `Tag "${labels[0]}" ajoute.`);
}

export function addPendingVisitTags(labels) {
  labels.forEach((label) => {
    if (!state.pendingVisitTags.some((item) => item.toLowerCase() === label.toLowerCase())) {
      state.pendingVisitTags.push(label);
    }
  });
  dom.rucheTagInput.value = "";
  state.stagedRucheTags.clear();
  closeTagDialog();
  renderVisitSelectedTags(state.selectedRucheTags);
  setStatus(`${labels.length > 1 ? `Tags ${labels.join(", ")} ajoutes` : `Tag "${labels[0]}" ajoute`} a la visite : ${labels.length > 1 ? "ils seront poses" : "il sera pose"} a la synchronisation.`);
}

export async function deleteRucheTag(tagId) {
  if (!state.selectedRuche) return;
  try {
    await api(`/ruches/${encodeURIComponent(state.selectedRuche.id)}/tags/${encodeURIComponent(tagId)}`, { method: "DELETE" });
    setHint(dom.rucheTagHint, "Tag retire.", "ok");
    await refreshSelectedRuche();
    await loadRucheTags();
  } catch (error) {
    setHint(dom.rucheTagHint, `Suppression impossible: ${error.message}`, "error");
  }
}

export function renderTagSettings() {
  const favoriteSet = new Set(state.tagFavorites);
  dom.tagFavoritesSettings.innerHTML = "";
  TAG_CATALOG.forEach((group) => {
    const section = document.createElement("section");
    section.className = "tag-settings-section";
    section.innerHTML = `<h4>${group.category}</h4>`;
    group.tags.forEach((label) => {
      const option = document.createElement("label");
      option.className = "tag-setting-option";
      const checkbox = document.createElement("input");
      checkbox.type = "checkbox";
      checkbox.checked = favoriteSet.has(label);
      checkbox.addEventListener("change", () => {
        if (checkbox.checked && !state.tagFavorites.includes(label)) {
          state.tagFavorites.push(label);
        } else if (!checkbox.checked) {
          state.tagFavorites = state.tagFavorites.filter((tag) => tag !== label);
        }
        saveTagFavorites().catch((error) => setStatus(`Favoris non synchronises: ${error.message}`));
        renderTagFavorites();
      });
      option.appendChild(checkbox);
      option.append(label);
      section.appendChild(option);
    });
    dom.tagFavoritesSettings.appendChild(section);
  });
}
