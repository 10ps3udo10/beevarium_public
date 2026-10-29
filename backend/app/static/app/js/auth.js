import { api, applyApiBaseUrl } from "./api.js";
import { refreshDashboard, renderDashboardContext } from "./dashboard.js";
import { dom } from "./dom.js";
import { restorePendingTab, setActiveTab } from "./navigation.js";
import { openQuickCreate, renderPremiumLocks } from "./creation.js";
import qrcode from "./vendor/qrcode.js";
import { clearOfflineData } from "./offline.js";
import { renderRuchers, selectRucher } from "./ruchers.js";
import { openRucheCreator, renderRuches } from "./ruches.js";
import { applyScopeRuche } from "./scope.js";
import { state } from "./state.js";
import { allCatalogTags } from "./tags.js";
import { setHint, setStatus } from "./utils.js";
import { openNewVisitDialog, renderVisites } from "./visites.js";

let pendingMfaToken = "";

export function renderProfile(user) {
  renderMfaState(user);
  dom.btnOpenAdmin.hidden = !user?.is_admin;
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
  dom.accountDeleteForm.reset();
  setHint(dom.accountDeleteHint, "", "");
  setHint(dom.mfaHint, "", "");
  dom.mfaRecoveryBox.hidden = true;
  dom.mfaEnableForm.hidden = true;
  dom.profileDialog.showModal();
}

// Droit d'acces et portabilite (RGPD) : tout le compte dans un fichier JSON.
export async function exportAccount() {
  dom.btnExportAccount.disabled = true;
  try {
    const data = await api("/users/me/export");
    const url = URL.createObjectURL(new Blob([JSON.stringify(data, null, 2)], { type: "application/json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `beevarium-export-${new Date().toISOString().slice(0, 10)}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setStatus("Export des donnees telecharge.");
  } catch (error) {
    setHint(dom.accountDeleteHint, `Export impossible: ${error.message}`, "error");
  } finally {
    dom.btnExportAccount.disabled = false;
  }
}

export async function deleteAccount(event) {
  event.preventDefault();
  if (!window.confirm("Supprimer definitivement le compte et toutes ses donnees ? Cette action est irreversible.")) return;
  try {
    await api("/users/me", { method: "DELETE", body: { password: dom.accountDeletePassword.value } });
  } catch (error) {
    setHint(dom.accountDeleteHint, error.status === 403 ? "Mot de passe incorrect." : `Suppression impossible: ${error.message}`, "error");
    return;
  }
  dom.profileDialog.close();
  await logout({ revokeServerSession: false });
  setHint(dom.authHint, "Compte supprime. Toutes ses donnees ont ete effacees.", "ok");
  setStatus("Compte supprime.");
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
    const data = pendingMfaToken
      ? await api("/auth/login/mfa", { method: "POST", body: { mfa_token: pendingMfaToken, code: dom.mfaCode.value.trim() } })
      : await api("/auth/login", {
          method: "POST",
          body: {
            email: dom.email.value.trim(),
            password: dom.password.value
          }
        });
    if (data.mfa_required) {
      // Deuxieme etape : pas de session tant que le code n'est pas valide.
      pendingMfaToken = data.mfa_token;
      dom.mfaRow.hidden = false;
      dom.mfaCode.focus();
      setHint(dom.authHint, "Saisis le code de ton application d'authentification (ou un code de secours).", "ok");
      setStatus("Code de verification requis.");
      return;
    }
    pendingMfaToken = "";
    dom.mfaRow.hidden = true;
    dom.mfaCode.value = "";
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
    if (pendingMfaToken && error.status === 401 && error.message.startsWith("Jeton")) {
      pendingMfaToken = "";
      dom.mfaRow.hidden = true;
    }
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

// --- Double authentification (profil) et administration ---
function renderMfaState(user) {
  const enabled = Boolean(user?.mfa_enabled);
  dom.mfaState.textContent = enabled ? "Double authentification active." : "Double authentification inactive.";
  dom.mfaSetupForm.hidden = enabled;
  dom.mfaDisableForm.hidden = !enabled;
  if (enabled) dom.mfaEnableForm.hidden = true;
}

// QR code genere dans le navigateur : la cle ne part chez aucun service tiers.
function renderMfaQr(otpauthUri) {
  const qr = qrcode(0, "M");
  qr.addData(otpauthUri);
  qr.make();
  dom.mfaQr.innerHTML = qr.createSvgTag({ cellSize: 4, margin: 4, scalable: true });
}

export async function setupMfa(event) {
  event.preventDefault();
  try {
    const data = await api("/users/me/mfa/setup", { method: "POST", body: { password: dom.mfaSetupPassword.value } });
    dom.mfaSetupPassword.value = "";
    dom.mfaSecret.textContent = data.secret;
    dom.mfaOtpauth.href = data.otpauth_uri;
    dom.mfaAccount.textContent = dom.profileEmailReadonly.value;
    renderMfaQr(data.otpauth_uri);
    dom.mfaSetupForm.hidden = true;
    dom.mfaEnableForm.hidden = false;
    dom.mfaEnableCode.focus();
    setHint(dom.mfaHint, "", "");
  } catch (error) {
    setHint(dom.mfaHint, error.status === 403 ? "Mot de passe incorrect." : `Activation impossible: ${error.message}`, "error");
  }
}

export async function enableMfa(event) {
  event.preventDefault();
  try {
    const data = await api("/users/me/mfa/enable", { method: "POST", body: { code: dom.mfaEnableCode.value.trim() } });
    dom.mfaEnableCode.value = "";
    dom.mfaSecret.textContent = "";
    dom.mfaQr.replaceChildren();
    dom.mfaRecoveryList.textContent = data.recovery_codes.join("\n");
    dom.mfaRecoveryBox.hidden = false;
    renderProfile(data.user);
    setHint(dom.mfaHint, "Double authentification activee.", "ok");
  } catch (error) {
    setHint(dom.mfaHint, error.status === 403 ? "Code invalide." : `Activation impossible: ${error.message}`, "error");
  }
}

export async function disableMfa(event) {
  event.preventDefault();
  try {
    const data = await api("/users/me/mfa/disable", {
      method: "POST",
      body: { password: dom.mfaDisablePassword.value, code: dom.mfaDisableCode.value.trim() },
    });
    dom.mfaDisablePassword.value = "";
    dom.mfaDisableCode.value = "";
    dom.mfaRecoveryBox.hidden = true;
    renderProfile(data.user);
    setHint(dom.mfaHint, "Double authentification desactivee.", "ok");
  } catch (error) {
    setHint(dom.mfaHint, error.status === 403 ? "Mot de passe ou code incorrect." : `Desactivation impossible: ${error.message}`, "error");
  }
}

export function openAdmin() {
  dom.profileMenu.open = false;
  dom.adminDialog.showModal();
  loadAdmin();
}

async function loadAdmin() {
  setHint(dom.adminHint, "", "");
  dom.adminFeedbackList.replaceChildren();
  try {
    const [stats, feedback] = await Promise.all([api("/admin/stats"), api("/admin/feedback")]);
    dom.adminStats.textContent = `${stats.comptes} comptes, ${stats.comptes_actifs_30j} actifs sur 30 jours, ${stats.visites_30j} visites sur 30 jours.`;
    if (!feedback.length) setHint(dom.adminHint, "Aucun retour a traiter.", "ok");
    feedback.forEach((item) => dom.adminFeedbackList.appendChild(adminFeedbackItem(item)));
  } catch (error) {
    dom.adminStats.textContent = "";
    setHint(dom.adminHint, error.message, "error");
  }
}

function adminFeedbackItem(item) {
  const box = document.createElement("div");
  box.className = "admin-feedback stack";
  const text = document.createElement("p");
  text.textContent = `[${item.category}] ${item.email} (${item.created_at.slice(0, 10)}) : ${item.message}`;
  const note = document.createElement("input");
  note.maxLength = 255;
  note.placeholder = "Note (facultative)";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "btn btn-secondary";
  button.textContent = "Marquer traite";
  button.addEventListener("click", async () => {
    button.disabled = true;
    try {
      await api(`/admin/feedback/${item.id}/traiter`, { method: "POST", body: { note: note.value.trim() || null } });
      box.remove();
    } catch (error) {
      button.disabled = false;
      setHint(dom.adminHint, error.message, "error");
    }
  });
  box.append(text, note, button);
  return box;
}
