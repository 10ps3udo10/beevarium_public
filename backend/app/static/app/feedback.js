const form = document.querySelector("#feedback-form");
const status = document.querySelector("#feedback-status");
const loginCard = document.querySelector("#feedback-login");
const loginEmail = document.querySelector("#feedback-login-email");
const loginPassword = document.querySelector("#feedback-login-password");
const loginButton = document.querySelector("#feedback-login-button");
const loginStatus = document.querySelector("#feedback-login-status");

let authenticated = false;

async function readResponse(response, fallback) {
  const payload = await response.json().catch(() => null);
  if (!response.ok) throw new Error(payload?.error?.message || payload?.detail || fallback);
  return payload;
}

try {
  await readResponse(await fetch("/auth/me"), "Session absente.");
  authenticated = true;
  loginCard.hidden = true;
} catch {
  status.textContent = "Connectez-vous pour envoyer ce retour.";
}

loginButton.addEventListener("click", async () => {
  loginButton.disabled = true;
  loginStatus.textContent = "Connexion en cours...";
  try {
    await readResponse(await fetch("/auth/login", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: loginEmail.value.trim(), password: loginPassword.value }),
    }), "Connexion impossible.");
    authenticated = true;
    loginCard.hidden = true;
    status.textContent = "Connexion reussie. Vous pouvez envoyer votre retour.";
  } catch (error) {
    loginStatus.textContent = error.message;
  } finally {
    loginButton.disabled = false;
  }
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!authenticated) {
    status.textContent = "Connectez-vous avant d'envoyer votre retour.";
    loginCard.hidden = false;
    return;
  }
  const button = form.querySelector("button");
  button.disabled = true;
  status.textContent = "Envoi en cours...";
  try {
    await readResponse(await fetch("/feedback", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        category: document.querySelector("#feedback-category").value,
        message: document.querySelector("#feedback-message").value.trim(),
        context: document.querySelector("#feedback-context").value.trim() || null,
      }),
    }), "Le retour n'a pas pu etre envoye.");
    form.reset();
    status.textContent = "Merci, votre retour a bien ete envoye.";
  } catch (error) {
    status.textContent = error.message;
  } finally {
    button.disabled = false;
  }
});
