import { api, applyApiBaseUrl } from "./api.js";
import { refreshDashboard, renderDashboardContext } from "./dashboard.js";
import { dom } from "./dom.js";
import { restorePendingTab, setActiveTab } from "./navigation.js";
import { openQuickCreate, renderPremiumLocks } from "./creation.js";
import { clearOfflineData } from "./offline.js";
import { renderRuchers, selectRucher } from "./ruchers.js";
import { openRucheCreator, renderRuches } from "./ruches.js";
import { applyScopeRuche } from "./scope.js";
import { state } from "./state.js";
import { allCatalogTags } from "./tags.js";
import { setHint, setStatus } from "./utils.js";
import { openNewVisitDialog, renderVisites } from "./visites.js";

export function renderProfile(user) {
  const email = user?.email || "Profil";
  const plan = user?.is_premium ? "Compte Premium" : "Compte Free";
  state.isPremium = Boolean(user?.is_premium);
  renderPremiumLocks();
  dom.profileEmail.textContent = email;
  dom.profilePlan.textContent = plan;
  dom.profilePill.textContent = email.split("@")[0].slice(0, 18) || "Profil";
  dom.profileFirstName.value = user?.prenom || "";
  dom.profileEmailReadonly.value = email;
  if (Array.isArray(user?.tag_favorites) && user.tag_favorites.length) {
    state.tagFavorites = user.tag_favorites.filter((tag) => allCatalogTags().includes(tag));
    localStorage.setItem("bee.tagFavorites", JSON.stringify(state.tagFavorites));
  }
}

export function openProfileEditor() {
  dom.profileDialog.showModal();
}

export async function saveProfile(event) {
  event.preventDefault();
  try {
    const user = await api("/users/me", { method: "PATCH", body: { prenom: dom.profileFirstName.value.trim() || null } });
    renderProfile(user);
    dom.profileDialog.close();
    setStatus("Profil mis a jour.");
  } catch (error) {
    setHint(dom.profileFormHint, `Mise a jour impossible: ${error.message}`, "error");
  }
}

export function setSessionView(isAuthenticated) {
  dom.authCard.hidden = isAuthenticated;
  if (dom.forgotCard) {
    dom.forgotCard.hidden = true;
  }
  if (dom.registerCard) {
    dom.registerCard.hidden = true;
  }
  dom.dashboardCard.hidden = !isAuthenticated;
  dom.configCard.hidden = true;
  dom.btnLogout.hidden = !isAuthenticated;
  dom.profileMenu.hidden = !isAuthenticated;
  dom.environmentPill.hidden = !isAuthenticated;
}

export function showForgotPassword(show) {
  if (!dom.forgotCard) {
    return;
  }
  dom.authCard.hidden = show;
  dom.forgotCard.hidden = !show;
  if (dom.registerCard) dom.registerCard.hidden = true;
  if (show) {
    dom.forgotEmail.value = dom.email.value.trim();
    setHint(dom.forgotHint, "");
    dom.forgotEmail.focus();
  }
}

export function showRegister(show) {
  dom.authCard.hidden = show;
  dom.forgotCard.hidden = true;
  dom.registerCard.hidden = !show;
  if (show) {
    dom.registerEmail.value = dom.email.value.trim();
    setHint(dom.registerHint, "");
    dom.registerPrenom.focus();
  }
}

// Inscription : le compte cree ouvre directement la session, comme une
// connexion ; la prise en main guidee prend ensuite le relais.
export async function register() {
  const email = dom.registerEmail.value.trim();
  const password = dom.registerPassword.value;
  if (!email || !email.includes("@")) {
    setHint(dom.registerHint, "Saisis une adresse e-mail valide.", "error");
    return;
  }
  if (password.length < 12) {
    setHint(dom.registerHint, "Le mot de passe doit faire au moins 12 caracteres.", "error");
    return;
  }
  if (!dom.registerTerms.checked) {
    setHint(dom.registerHint, "Accepte les conditions de la beta pour continuer.", "error");
    return;
  }
  applyApiBaseUrl();
  dom.btnRegisterSubmit.disabled = true;
  setStatus("Creation du compte...");
  try {
    const data = await api("/auth/register", {
      method: "POST",
      body: {
        email,
        password,
        prenom: dom.registerPrenom.value.trim() || null,
      },
    });
    state.authenticated = true;
    renderProfile(data.user);
    localStorage.removeItem("bee.token");
    dom.registerPassword.value = "";
    dom.registerPassword.type = "password";
    dom.registerCard.hidden = true;
    setStatus("Compte cree. Bienvenue !");
    setSessionView(true);
    await refreshDashboard();
  } catch (error) {
    const message = error.message === "Email deja utilise"
      ? "Un compte existe deja avec cette adresse : connecte-toi ou utilise Mot de passe oublie."
      : error.message;
    setHint(dom.registerHint, `Creation impossible : ${message}`, "error");
    setStatus("Echec de creation du compte.");
  } finally {
    dom.btnRegisterSubmit.disabled = false;
  }
}

export async function requestPasswordReset() {
  const email = dom.forgotEmail.value.trim();
  if (!email) {
    setHint(dom.forgotHint, "Indiquez votre adresse e-mail.", "error");
    return;
  }

  dom.btnForgotSubmit.disabled = true;
  setHint(dom.forgotHint, "Envoi en cours...");
  try {
    const result = await api("/auth/forgot-password", { method: "POST", body: { email } });
    setHint(dom.forgotHint, result.message, "ok");
  } catch (error) {
    setHint(dom.forgotHint, error.message, "error");
  } finally {
    dom.btnForgotSubmit.disabled = false;
  }
}

export function renderOnboarding() {
  if (!dom.onboardingCard) return;
  const { ruchers, ruches, hasVisit } = state.onboarding;
  dom.onboardingCard.hidden = hasVisit;
  if (hasVisit) {
    state.onboardingFlowActive = false;
    return;
  }

  dom.onboardingStepRucher.classList.toggle("is-complete", ruchers > 0);
  dom.onboardingStepRuche.classList.toggle("is-complete", ruches > 0);
  dom.onboardingStepVisite.classList.remove("is-complete");
  if (!ruchers) {
    dom.btnOnboardingNext.textContent = "Creer mon premier rucher";
  } else if (!ruches) {
    dom.btnOnboardingNext.textContent = "Ajouter ma premiere ruche";
  } else {
    dom.btnOnboardingNext.textContent = "Enregistrer ma premiere visite";
  }
}

export async function continueOnboarding() {
  state.onboardingFlowActive = true;
  const { ruchers, ruches } = state.onboarding;
  if (!ruchers) {
    // Prise en main : le rucher et toutes ses ruches en une fois.
    setActiveTab("ruchers");
    await openQuickCreate(null);
    return;
  }
  if (!ruches) {
    const rucher = state.ruchers[0];
    if (!rucher) return;
    setActiveTab("ruchers");
    await selectRucher(rucher);
    openRucheCreator();
    return;
  }
  const ruche = state.allRuches[0] || state.ruches[0];
  if (!ruche) return;
  setActiveTab("visites");
  await applyScopeRuche(ruche.id);
  openNewVisitDialog();
}

export async function login() {
  applyApiBaseUrl();
  setStatus("Connexion en cours...");
  dom.btnLogin.disabled = true;
  try {
    const data = await api("/auth/login", {
      method: "POST",
      body: {
        email: dom.email.value.trim(),
        password: dom.password.value
      }
    });
    state.authenticated = true;
    renderProfile(data.user);
    localStorage.removeItem("bee.token");
    // Le mot de passe affiche en clair ne doit pas le rester apres connexion.
    dom.password.type = "password";
    setHint(dom.authHint, `Connecte: ${data.user.email}`, "ok");
    setStatus("Connexion reussie.");
    setSessionView(true);
    await refreshDashboard();
    restorePendingTab();
  } catch (error) {
    setHint(dom.authHint, `Connexion impossible: ${error.message}`, "error");
    setStatus("Echec de connexion.");
  } finally {
    dom.btnLogin.disabled = false;
  }
}

export async function logout({ revokeServerSession = true } = {}) {
  if (revokeServerSession) {
    try {
      await api("/auth/logout", { method: "POST" });
    } catch (error) {
      console.warn("Revocation serveur impossible", error);
    }
  }
  state.token = "";
  state.authenticated = false;
  state.selectedRucher = null;
  state.selectedRuche = null;
  state.ruchers = [];
  state.ruches = [];
  renderDashboardContext();
  localStorage.removeItem("bee.token");
  try {
    await clearOfflineData();
  } catch (error) {
    console.warn("Effacement offline incomplet", error);
  }
  setSessionView(false);
  renderRuchers();
  renderRuches();
  renderVisites([]);
  dom.rucherDetail.textContent = "Selectionne un rucher.";
  dom.synthTotalVisitesRuche.textContent = "-";
  dom.synthTotalVisitesRucher.textContent = "-";
  dom.synthTotalRuches.textContent = "-";
  dom.synthPartIa.textContent = "-";
  dom.synthReineVue.textContent = "-";
  dom.syntheseLecture.textContent = "Charge une synthese pour voir les indicateurs terrain.";
  setHint(dom.authHint, "Session locale supprimee.", "ok");
  setStatus("Deconnecte.");
}

export async function loadDemoCredentials() {
  setStatus("Chargement demo local...");
  try {
    const demo = await fetch("./demo-access.json", { cache: "no-store" }).then((res) => res.json());
    if (!demo.email || !demo.password) {
      throw new Error("Fichier demo-access.json non pret. Lance bootstrap avec publication client.");
    }
    dom.email.value = demo.email;
    dom.password.value = demo.password;
    setHint(dom.authHint, "Identifiants demo charges. Clique sur Se connecter.", "ok");
    setStatus("Identifiants demo prets.");
  } catch (error) {
    setHint(dom.authHint, `Chargement demo impossible: ${error.message}`, "error");
    setStatus("Demo non disponible.");
  }
}
