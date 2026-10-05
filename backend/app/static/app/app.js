import { api, applyApiBaseUrl, loadConfig, renderEnvironmentPill } from "./js/api.js";
import { openAtelierRucheCreator, openAtelierRucheEditor, openNewMaterialDialog, saveAtelierRuche, saveStock, stepStockQuantity, syncStockFormatOptions } from "./js/atelier.js";
import { continueOnboarding, loadDemoCredentials, login, logout, openProfileEditor, renderProfile, register, requestPasswordReset, saveProfile, setSessionView, showForgotPassword, showRegister } from "./js/auth.js";
import { bindCreationEvents } from "./js/creation.js";
import { refreshDashboard } from "./js/dashboard.js";
import { dom } from "./js/dom.js";
import { rejectDraft, saveDraft } from "./js/ia.js";
import { bindCompactMenu, closeNavigationDrawer, restorePendingTab, setActiveTab, tabFromLocation, toggleNavigationDrawer } from "./js/navigation.js";
import { keepLocalConflict, keepServerConflict, mergeConflictManually, showFirstSyncConflict, syncOfflineVisits, updateSyncStatus } from "./js/offline.js";
import { deleteHarvest, openHarvestDialog, populateHarvestHives, saveHarvest } from "./js/recoltes.js";
import { saveQueen } from "./js/reines.js";
import { confirmRucherDelete, createRucherFromDialog, moveHivesBeforeRucherDelete, openRucherCreator, openRucherDelete, openRucherEditor, renderRuchers, saveRucherEdit } from "./js/ruchers.js";
import { editRuche, openBulkMoveDialog, openRucheCreator, renderRuches, resetRucheForm, saveRuche, submitBulkMove } from "./js/ruches.js";
import { applyScopeRuche, applyScopeRucher, fillVisitCreateScope } from "./js/scope.js";
import { state } from "./js/state.js";
import { applyPeriodSelection, applyStatsSearch, refreshStatistics, renderStatsSearchOptions, setCurrentApiculturePeriod } from "./js/statistiques.js";
import { addRucheTag, closeTagDialog, deleteRucheTag, loadTagFavorites, openTagDialog, renderTagSettings, renderTagSuggestions, renderVisitSelectedTags, updateAddTagsButton, updateVisitTagSuggestions } from "./js/tags.js";
import { openTransvasementDialog, submitTransvasement, updateTransvasementProvenance } from "./js/transvasement.js";
import { bindPasswordToggles, setHint, setStatus } from "./js/utils.js";
import { applyFrameMovementToTotal, hydrateVisitEquipmentFromRuche, loadVisitHistory, openNewVisitDialog, prefillVisitFramesFromRuche, saveVisitEdit, saveVisite } from "./js/visites.js";

function bindEvents() {
  // La connexion est liee en premier: elle doit survivre a l echec d une autre liaison.
  dom.btnLogin.addEventListener("click", login);
  dom.password.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      login();
    }
  });

  dom.envSelect.addEventListener("change", () => {
    state.profile = dom.envSelect.value;
    applyApiBaseUrl();
    renderEnvironmentPill();
    setHint(dom.configHint, `Profil actif: ${state.profile}`, "ok");
  });

  dom.saveConfig.addEventListener("click", () => {
    localStorage.setItem("bee.profile", dom.envSelect.value);
    localStorage.setItem("bee.apiOverride", dom.overrideUrl.value.trim());
    state.profile = dom.envSelect.value;
    applyApiBaseUrl();
    renderEnvironmentPill();
    setHint(dom.configHint, `Configuration enregistree. API: ${state.apiBaseUrl}`, "ok");
    setStatus("Configuration enregistree.");
  });

  dom.btnLogout.addEventListener("click", () => { void logout(); });
  dom.btnTagSettings.addEventListener("click", () => {
    renderTagSettings();
    dom.profileMenu.open = false;
    dom.tagSettingsDialog.showModal();
  });
  dom.btnCloseTagSettings.addEventListener("click", () => dom.tagSettingsDialog.close());
  dom.btnLoadDemo.addEventListener("click", loadDemoCredentials);
  dom.btnForgotOpen.addEventListener("click", () => showForgotPassword(true));
  dom.btnForgotCancel.addEventListener("click", () => showForgotPassword(false));
  dom.btnForgotSubmit.addEventListener("click", requestPasswordReset);
  bindPasswordToggles();
  bindCreationEvents();
  dom.btnRegisterOpen.addEventListener("click", () => showRegister(true));
  dom.btnRegisterCancel.addEventListener("click", () => showRegister(false));
  dom.btnRegisterSubmit.addEventListener("click", register);
  dom.registerPassword.addEventListener("keydown", (event) => {
    if (event.key === "Enter") register();
  });
  dom.btnOnboardingNext.addEventListener("click", continueOnboarding);
  dom.btnOpenNav.addEventListener("click", toggleNavigationDrawer);
  dom.btnCloseNav.addEventListener("click", closeNavigationDrawer);
  dom.navBackdrop.addEventListener("click", closeNavigationDrawer);
  dom.mainNav.addEventListener("mouseleave", () => {
    if (!dom.mainNav.contains(document.activeElement)) closeNavigationDrawer();
  });

  [dom.visiteScopeRucher, dom.statsScopeRucher].forEach((select) => {
    select?.addEventListener("change", (event) => applyScopeRucher(event.target.value));
  });
  [dom.visiteScopeRuche, dom.statsScopeRuche].forEach((select) => {
    select?.addEventListener("change", (event) => applyScopeRuche(event.target.value));
  });  document.querySelectorAll(".tab-button").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tab));
  });
  document.querySelectorAll("[data-tab-shortcut]").forEach((button) => {
    button.addEventListener("click", () => setActiveTab(button.dataset.tabShortcut));
  });
  dom.btnShowRucherForm.addEventListener("click", () => {
    openRucherCreator();
  });
  dom.btnShowRucheForm.addEventListener("click", openRucheCreator);
  dom.btnShowAtelierRucheForm.addEventListener("click", openAtelierRucheCreator);
  dom.btnEditAtelierSelected.addEventListener("click", openAtelierRucheEditor);
  const helpDialog = document.getElementById("help-dialog");
  document.getElementById("btn-open-help").addEventListener("click", () => {
    dom.profileMenu?.removeAttribute("open");
    helpDialog.showModal();
  });
  document.getElementById("btn-close-help").addEventListener("click", () => helpDialog.close());
  // Infobulles : survol ou focus sur ordinateur, toucher sur mobile.
  document.addEventListener("click", (event) => {
    const tipButton = event.target.closest(".info-tip");
    document.querySelectorAll(".info-tip.is-open").forEach((item) => { if (item !== tipButton) item.classList.remove("is-open"); });
    if (tipButton) {
      event.preventDefault();
      event.stopPropagation();
      tipButton.classList.toggle("is-open");
    }
  }, true);
  document.getElementById("brand-home").addEventListener("click", (event) => {
    event.preventDefault();
    if (state.authenticated) setActiveTab("dashboard");
  });
  dom.btnEditRucher.addEventListener("click", openRucherEditor);
  dom.btnVisitTransvasement.addEventListener("click", () => openTransvasementDialog(true));
  dom.btnRucheTransvasement.addEventListener("click", () => openTransvasementDialog(false));
  dom.btnCloseTransvasement.addEventListener("click", () => dom.transvasementDialog.close());
  dom.transvasementProvenance.addEventListener("change", updateTransvasementProvenance);
  dom.transvasementForm.addEventListener("submit", submitTransvasement);
  dom.btnDeleteRucher.addEventListener("click", openRucherDelete);
  dom.btnCloseRucherDelete.addEventListener("click", () => dom.rucherDeleteDialog.close());
  dom.btnRucherDeleteMove.addEventListener("click", moveHivesBeforeRucherDelete);
  dom.btnRucherDeleteConfirm.addEventListener("click", confirmRucherDelete);
  dom.btnCloseRucher.addEventListener("click", () => dom.rucherDialog.close());
  dom.rucherEditForm.addEventListener("submit", saveRucherEdit);
  dom.btnCloseCreateRucher.addEventListener("click", () => dom.rucherCreateDialog.close());
  dom.rucherCreateForm.addEventListener("submit", createRucherFromDialog);
  dom.btnMoveRucherSelected.addEventListener("click", () => openBulkMoveDialog(state.selectedRucher?.nom || "le rucher", "terrain"));
  dom.btnMoveAtelierSelected.addEventListener("click", () => openBulkMoveDialog("l atelier", "atelier"));
  dom.btnCloseBulkMove.addEventListener("click", () => {
    state.pendingBulkMoveIds = [];
    dom.bulkMoveDialog.close();
  });
  dom.bulkMoveForm.addEventListener("submit", submitBulkMove);
  dom.btnCloseStock.addEventListener("click", () => dom.stockDialog.close());
  dom.btnAddMaterial.addEventListener("click", openNewMaterialDialog);
  dom.btnCloseAtelierRuche.addEventListener("click", () => dom.atelierRucheDialog.close());
  dom.btnCloseQueen.addEventListener("click", () => dom.queenDialog.close());
  dom.atelierRucheForm.addEventListener("submit", saveAtelierRuche);
  dom.stockForm.addEventListener("submit", saveStock);
  dom.stockQuantityMinus.addEventListener("click", () => stepStockQuantity(-1));
  dom.stockQuantityPlus.addEventListener("click", () => stepStockQuantity(1));
  dom.stockTypeSelect.addEventListener("change", syncStockFormatOptions);
  dom.btnCloseVisit.addEventListener("click", () => dom.visitDialog.close());
  dom.visitEditForm.addEventListener("submit", saveVisitEdit);
  dom.synthStartDate.addEventListener("change", refreshStatistics);
  dom.synthEndDate.addEventListener("change", refreshStatistics);
  dom.rucherSearch.addEventListener("input", renderRuchers);
  dom.rucheSearch.addEventListener("input", renderRuches);
  dom.periodWindow.addEventListener("change", () => applyPeriodSelection());
  dom.statsSearch.addEventListener("focus", renderStatsSearchOptions);
  dom.statsSearch.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      applyStatsSearch();
    }
  });
  dom.statsSearch.addEventListener("change", applyStatsSearch);
  dom.rucheForm.addEventListener("submit", saveRuche);
  dom.rucheReineDate.addEventListener("change", () => {
    if (dom.rucheReineDate.value) dom.rucheReineAnnee.value = dom.rucheReineDate.value.slice(0, 4);
  });
  dom.rucheTagForm.addEventListener("submit", addRucheTag);
  dom.rucheTagInput.addEventListener("input", updateAddTagsButton);
  dom.btnOpenRucheTags.addEventListener("click", openTagDialog);
  dom.btnCloseTagDialog.addEventListener("click", closeTagDialog);
  dom.rucheTagsList.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-tag-id]");
    if (button) deleteRucheTag(button.dataset.tagId);
  });
  dom.tagDialogCurrent.addEventListener("click", (event) => {
    const button = event.target.closest("button[data-tag-id]");
    if (button) deleteRucheTag(button.dataset.tagId);
  });
  dom.btnCancelRuche.addEventListener("click", resetRucheForm);
  dom.visiteForm.addEventListener("submit", saveVisite);
  [dom.visiteReineVue, dom.visiteCouvain, dom.visiteReserves, dom.visiteCadresCouvain].forEach((field) => field?.addEventListener("input", updateVisitTagSuggestions));
  dom.visitCreateRucher.addEventListener("change", async () => {
    await applyScopeRucher(dom.visitCreateRucher.value);
    fillVisitCreateScope();
  });
  dom.visitCreateRuche.addEventListener("change", async () => {
    await applyScopeRuche(dom.visitCreateRuche.value);
    hydrateVisitEquipmentFromRuche();
    dom.visiteCadresTotal.value = "";
    dom.visiteCadresCouvain.value = "";
    await prefillVisitFramesFromRuche();
    renderVisitSelectedTags(state.selectedRucheTags);
    fillVisitCreateScope();
  });
  dom.btnNewVisit.addEventListener("click", openNewVisitDialog);
  dom.btnCloseCreateVisit.addEventListener("click", () => dom.visitCreateDialog.close());
  dom.btnVisitTags.addEventListener("click", openTagDialog);
  dom.btnEditVisitTags.addEventListener("click", openTagDialog);
  [dom.visiteCadresAction, dom.visiteCadresQuantite].forEach((input) => input.addEventListener("change", () => applyFrameMovementToTotal(dom.visiteCadresAction, dom.visiteCadresQuantite, dom.visiteCadresAnnee, dom.visiteCadresTotal)));
  [dom.editVisitCadresAction, dom.editVisitCadresQuantite].forEach((input) => input.addEventListener("change", () => applyFrameMovementToTotal(dom.editVisitCadresAction, dom.editVisitCadresQuantite, dom.editVisitCadresAnnee, dom.editVisitTotalFrames)));
  dom.visiteHausse.addEventListener("change", () => { dom.visiteHausseQuantite.disabled = !dom.visiteHausse.checked; if (!dom.visiteHausse.checked) dom.visiteHausseQuantite.value = ""; });
  dom.editVisitHausse.addEventListener("change", () => { dom.editVisitHausseQuantite.disabled = !dom.editVisitHausse.checked; if (!dom.editVisitHausse.checked) dom.editVisitHausseQuantite.value = ""; });
  dom.btnShowIaReview.addEventListener("click", () => {
    dom.iaWipDialog.showModal();
  });
  dom.btnCloseIaWip.addEventListener("click", () => dom.iaWipDialog.close());
  dom.btnEditProfile.addEventListener("click", openProfileEditor);
  dom.btnCloseProfile.addEventListener("click", () => dom.profileDialog.close());
  dom.profileForm.addEventListener("submit", saveProfile);
  dom.btnNewHarvest.addEventListener("click", () => openHarvestDialog());
  dom.harvestRucher.addEventListener("change", () => populateHarvestHives(dom.harvestRucher.value));
  dom.btnCloseHarvest.addEventListener("click", () => dom.harvestDialog.close());
  dom.harvestForm.addEventListener("submit", saveHarvest);
  dom.btnDeleteHarvest.addEventListener("click", deleteHarvest);
  dom.visitesSearch.addEventListener("input", loadVisitHistory);
  dom.visitesTypeFilter.addEventListener("change", loadVisitHistory);
  dom.visitesStatusFilter.addEventListener("change", loadVisitHistory);
  dom.visitesSourceFilter.addEventListener("change", loadVisitHistory);
  bindCompactMenu(dom.visitesTypeMenu, dom.visitesTypeFilter);
  bindCompactMenu(dom.visitesStatusMenu, dom.visitesStatusFilter);
  bindCompactMenu(dom.visitesSourceMenu, dom.visitesSourceFilter);
  dom.visitesStartDate.addEventListener("change", loadVisitHistory);
  dom.visitesEndDate.addEventListener("change", loadVisitHistory);
  dom.queenForm.addEventListener("submit", saveQueen);
  dom.iaReviewForm.addEventListener("submit", (event) => { event.preventDefault(); saveDraft("brouillon"); });
  dom.btnCloseIaReview.addEventListener("click", () => dom.iaReviewDialog.close());
  dom.iaValidate.addEventListener("click", () => saveDraft("valide"));
  dom.iaReject.addEventListener("click", rejectDraft);
  dom.btnRucheStats.addEventListener("click", () => {
    setActiveTab("stats");
    dom.statsScopeRucherMenu.querySelector("summary")?.focus();
  });
  dom.btnRucheVisit.addEventListener("click", () => {
    setActiveTab("visites");
    openNewVisitDialog();
  });
  dom.btnRucheHarvest.addEventListener("click", () => openHarvestDialog());
  dom.btnRucheMove.addEventListener("click", () => {
    openBulkMoveDialog("la ruche", "terrain");
  });
  dom.btnRucheQueen.addEventListener("click", () => {
    dom.rucheSecondaryActions.hidden = false;
    dom.queenDate.value = new Date().toISOString().slice(0, 10);
    setHint(dom.queenFormHint, "", "");
    dom.queenDialog.showModal();
    dom.queenDate.focus();
  });
  dom.btnRucheEdit.addEventListener("click", () => { if (state.selectedRuche) editRuche(state.selectedRuche); });
  dom.syncKeepServer.addEventListener("click", keepServerConflict);
  dom.syncKeepLocal.addEventListener("click", keepLocalConflict);
  dom.syncMerge.addEventListener("click", mergeConflictManually);
}

async function bootstrap() {
  loadTagFavorites();
  renderTagSuggestions();
  // Lie les evenements en premier: meme si la suite echoue, la connexion reste possible.
  try {
    bindEvents();
  } catch (error) {
    console.error("Echec de liaison des evenements", error);
  }

  try {
    await loadConfig();
    renderEnvironmentPill();
    state.pendingTab = tabFromLocation();
    setActiveTab("dashboard");
    let isAuthenticated = false;
    try {
      renderProfile(await api("/auth/me"));
      isAuthenticated = true;
    } catch (error) {
      if (![401, 403].includes(error.status)) throw error;
    } finally {
      state.authenticated = true;
      localStorage.removeItem("bee.token");
    }
    state.authenticated = isAuthenticated;
    setSessionView(isAuthenticated);
    if (isAuthenticated) {
      await refreshDashboard();
      restorePendingTab();
    }
    dom.periodWindow.value = "season";
    setCurrentApiculturePeriod();
    // Lien ou historique du navigateur vers un autre onglet (#visites...).
    window.addEventListener("hashchange", () => {
      const tabName = tabFromLocation();
      if (state.authenticated && document.getElementById("dashboard-card").dataset.activeTab !== tabName) setActiveTab(tabName);
    });
    window.addEventListener("offline", () => updateSyncStatus("offline"));
    window.addEventListener("online", syncOfflineVisits);
    await updateSyncStatus(navigator.onLine ? "online" : "offline");
    await showFirstSyncConflict();
    setStatus(`Client pret. API cible: ${state.apiBaseUrl}`);
  } catch (error) {
    console.error("Erreur de demarrage", error);
    setStatus(`Erreur de demarrage: ${error.message}`);
    setHint(dom.authHint, "Verifie la configuration client.", "error");
  }
}

bootstrap();

