const params = new URLSearchParams(window.location.search);
const token = params.get("token") || "";
const hint = document.getElementById("hint");
const formBlock = document.getElementById("form-block");
const password = document.getElementById("password");
const passwordConfirm = document.getElementById("password-confirm");
const btnSubmit = document.getElementById("btn-submit");

// Oeil des champs mot de passe (meme comportement que l'ecran de connexion).
document.querySelectorAll("[data-password-for]").forEach((button) => {
  const input = document.getElementById(button.dataset.passwordFor);
  button.addEventListener("click", () => {
    const visible = input.type === "password";
    input.type = visible ? "text" : "password";
    button.setAttribute("aria-pressed", String(visible));
    button.setAttribute("aria-label", visible ? "Masquer le mot de passe" : "Afficher le mot de passe");
  });
});
function setHint(message, kind) {
  hint.textContent = message;
  hint.classList.remove("ok", "error");
  if (kind) hint.classList.add(kind);
}

if (!token) {
  formBlock.hidden = true;
  setHint("Lien invalide : aucun jeton fourni. Refaites une demande depuis l ecran de connexion.", "error");
}

async function submit() {
  if (password.value.length < 12) {
    setHint("Le mot de passe doit contenir au moins 12 caracteres.", "error");
    return;
  }
  if (password.value !== passwordConfirm.value) {
    setHint("Les deux mots de passe ne correspondent pas.", "error");
    return;
  }
  btnSubmit.disabled = true;
  setHint("Enregistrement en cours...");
  try {
    const response = await fetch(`${window.location.origin}/auth/reset-password`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token, password: password.value })
    });
    const payload = await response.json().catch(() => null);
    if (!response.ok) throw new Error(payload?.error?.message || payload?.detail || "Echec de la reinitialisation");
    formBlock.hidden = true;
    setHint(`${payload.message} Redirection en cours...`, "ok");
    setTimeout(() => { window.location.href = "./index.html"; }, 2500);
  } catch (error) {
    setHint(error.message, "error");
    btnSubmit.disabled = false;
  }
}

btnSubmit.addEventListener("click", submit);
passwordConfirm.addEventListener("keydown", (event) => {
  if (event.key === "Enter") submit();
});
